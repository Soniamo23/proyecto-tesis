from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import cv2

from .pose_extraction.face_landmarks.face_landmark_detector import FaceMeshProcessor
from .pose_extraction.hand_landmarks.hand_landmark_detector import HandMeshProcessor

from .data_reporting.blink_report.total_blink_report import force_show_report_summary as show_blink_summary
from .data_reporting.yawns_report.total_yawn_report import force_show_report_summary as show_yawn_summary
from .data_reporting.nods_report.nods_reporting import force_show_report_summary as show_nods_summary
from .data_reporting.eye_rub_report.eye_rub_reporting import force_show_report_summary as show_eye_rub_summary

from .data_reporting.blink_report.blink_reporting import (
    start_blink_reporting,
    stop_blink_reporting
)
from .data_reporting.yawns_report.yawns_reporting import (
    start_reporting as start_yawn_reporting,
    stop_reporting as stop_yawn_reporting
)
from .data_reporting.blink_report.total_blink_report import register_blink_listener  # Importar el listener de blink
from .data_reporting.eye_rub_report.eye_rub_reporting import register_eye_rub_listener
from .data_reporting.nods_report.nods_reporting import register_nod_listener
from .data_reporting.yawns_report.total_yawn_report import register_yawn_listener  # Importar el listener de bostezos

# Funciones de impresión actualizadas
def imprimir_frotamiento_en_consola(screen, mensaje):
    # Actualiza el label de reporte de ojos con el mensaje
    screen.ids.eyes_message_label.text = mensaje

def imprimir_en_consola(screen, mensaje):
    # Actualiza el label de reporte de parpadeo con el mensaje
    screen.ids.blink_message_label.text = mensaje

def imprimir_nods_en_consola(screen, mensaje):
    # Actualiza el label de reporte de cabeceo con el mensaje
    screen.ids.nod_message_label.text = mensaje

def imprimir_bostezo_en_consola(screen, mensaje):
    # Actualiza el label de reporte de bostezo con el mensaje
    screen.ids.yawn_message_label.text = mensaje


class DriverMonitoringScreen(Screen):
    def on_enter(self):
        print("[INFO] Entrando a DriverMonitoringScreen: iniciando detectores y cámara.")
        self.face_mesh_processor = FaceMeshProcessor()
        self.hand_mesh_processor = HandMeshProcessor()
        self.rotate_frame = True
        self.cap = cv2.VideoCapture(1)

        if not self.cap.isOpened():
            self.ids.footer_label.text = "❌ No se pudo abrir la cámara."
            print("[ERROR] No se pudo abrir la cámara.")
            return

        # Iniciar los hilos de reporte aquí para evitar inicio prematuro
        print("[INFO] Iniciando hilos de reporte de parpadeos y bostezos.")
        start_blink_reporting()
        start_yawn_reporting()

        # Registrar callback para imprimir reportes en consola, pasando la referencia de la pantalla
        register_blink_listener(lambda mensaje: imprimir_en_consola(self, mensaje), report_type="detailed")  # Detallado para parpadeos
        register_eye_rub_listener(lambda mensaje: imprimir_frotamiento_en_consola(self, mensaje), report_type="detailed")  # Reporte detallado para Eye Rub
        register_nod_listener(lambda mensaje: imprimir_nods_en_consola(self, mensaje), report_type="detailed")  # SOLO resumen para nodos
        register_yawn_listener(lambda mensaje: imprimir_bostezo_en_consola(self, mensaje), report_type="detailed")  # Detallado para yawns

        self.event = Clock.schedule_interval(self.update, 1.0 / 30.0)

    def update(self, dt):
        ret, frame = self.cap.read()
        if not ret:
            self.ids.footer_label.text = "❌ Error al leer el frame."
            print("[ERROR] No se pudo leer el frame de la cámara.")
            return

        _, face_success, face_frame = self.face_mesh_processor.process(frame.copy(), draw=True)
        _, hand_success, hand_frame = self.hand_mesh_processor.process(frame.copy(), draw=True)

        if face_frame.shape == frame.shape and hand_frame.shape == frame.shape:
            frame_with_both = frame.copy()
            frame_with_both = cv2.addWeighted(frame_with_both, 1.0, face_frame, 1.0, 0)
            frame_with_both = cv2.addWeighted(frame_with_both, 1.0, hand_frame, 1.0, 0)
        else:
            self.ids.footer_label.text = "❌ Tamaño inconsistente en las mallas."
            print("[ERROR] Tamaño inconsistente entre las mallas detectadas y el frame original.")
            return

        if self.rotate_frame:
            frame_with_both = cv2.flip(frame_with_both, -1)

        rgb_frame = cv2.cvtColor(frame_with_both, cv2.COLOR_BGR2RGB)
        buf = rgb_frame.tobytes()

        texture = Texture.create(size=(rgb_frame.shape[1], rgb_frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
        self.ids.img_widget.texture = texture

        status_msg = "✅ Detección activa" if face_success or hand_success else "🔍 Buscando rostro o manos..."
        self.ids.footer_label.text = status_msg

    def on_leave(self):
        print("[INFO] Saliendo de DriverMonitoringScreen: deteniendo captura y reportes.")
        self.stop_monitoring()
        stop_blink_reporting()
        stop_yawn_reporting()

    def stop_monitoring(self):
        if hasattr(self, 'event'):
            self.event.cancel()
            print("[INFO] Evento Clock cancelado.")
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
            print("[INFO] Cámara liberada.")

    def end_trip(self):
        print("[INFO] Finalizando viaje: mostrando resúmenes y deteniendo reportes.")
        self.stop_monitoring()

        show_blink_summary()  # Mostrar el resumen de parpadeos
        show_yawn_summary()   # Mostrar el resumen de bostezos
        show_nods_summary()   # Mostrar el resumen de nodos
        show_eye_rub_summary() # Mostrar el resumen de frotamientos de ojos

        stop_blink_reporting()
        stop_yawn_reporting()

        self.manager.current = "end_report"
