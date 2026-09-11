"""
Módulo GUI: Widget de Escritorio (System Tray) con Esfera Reactiva.
Autor: Diego Molina
Descripción: Crea un icono en la bandeja del sistema con una ventana emergente
             que muestra una esfera 3D animada que reacciona al estado de JARVIS.
"""

import sys
import math
from typing import Optional

GUI_AVAILABLE = False

try:
    from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, 
                                 QMainWindow, QWidget, QVBoxLayout)
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtGui import QAction, QPainter, QColor, QRadialGradient, QBrush, QPen
    GUI_AVAILABLE = True
except ImportError:
    # PyQt6 no disponible - crear clases dummy para evitar errores de import
    class QWidget:
        pass
    class QMainWindow:
        pass
    class QTimer:
        pass
    class QColor:
        pass
    class QRadialGradient:
        pass
    class QBrush:
        pass
    class QPen:
        pass
    class QPainter:
        pass
    class Qt:
        class WindowType:
            FramelessWindowHint = 0
            WindowStaysOnTopHint = 0
        class WidgetAttribute:
            WA_TranslucentBackground = 0
        class WindowState:
            WindowMinimized = 0
        class PenStyle:
            NoPen = 0
        class BrushStyle:
            NoBrush = 0
    class QSystemTrayIcon:
        class ActivationReason:
            DoubleClick = 0
        class MessageIcon:
            Information = 0
            Warning = 0
    class QAction:
        def __init__(self, *args, **kwargs):
            pass
        def triggered(self, callback):
            pass

if not GUI_AVAILABLE:
    # No exportamos nada si PyQt6 no está disponible
    __all__ = []
else:
    __all__ = ['JarvisTray', 'ReactiveSphere']

class ReactiveSphere(QWidget):
    """Widget que dibuja una esfera 3D estilo 'Arc Reactor' que cambia según el estado."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.setMaximumSize(300, 300)
        
        # Estados: 'idle', 'listening', 'thinking', 'speaking'
        self.state = 'idle'
        self.angle = 0
        self.pulse = 0
        
        # Timer para la animación
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)  # ~33 FPS

    def set_state(self, new_state: str):
        """Cambia el estado visual de la esfera."""
        if new_state != self.state:
            self.state = new_state
            self.pulse = 0  # Resetear pulso al cambiar

    def update_animation(self):
        """Actualiza los parámetros de animación y fuerza el repaint."""
        self.angle += 0.05 if self.state in ['thinking', 'speaking'] else 0.01
        
        # Lógica de pulso
        speed = 0.2 if self.state == 'listening' else 0.05
        self.pulse = (self.pulse + speed) % (2 * math.pi)
        
        self.update()

    def paintEvent(self, event):
        if not GUI_AVAILABLE:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 2 - 20

        # Determinar colores según estado
        if self.state == 'listening':
            base_color = QColor(0, 255, 255)  # Cyan brillante
            glow_color = QColor(0, 255, 255, 100)
        elif self.state in ['thinking', 'speaking']:
            base_color = QColor(255, 180, 0)  # Dorado/Iron Man
            glow_color = QColor(255, 140, 0, 100)
        else:
            base_color = QColor(0, 100, 255)  # Azul tranquilo
            glow_color = QColor(0, 100, 255, 50)

        # Fondo oscuro transparente
        painter.fillRect(self.rect(), QColor(10, 10, 15, 200))

        # Efecto de brillo (Glow)
        pulse_factor = 1 + 0.2 * math.sin(self.pulse) if self.state == 'listening' else 1
        gradient = QRadialGradient(center_x, center_y, radius * 1.5 * pulse_factor)
        gradient.setColorAt(0, glow_color)
        gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center_x - int(radius*1.5), center_y - int(radius*1.5), 
                            int(radius*3), int(radius*3))

        # Dibujar la "esfera" (círculos concéntricos rotando)
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(math.degrees(self.angle))
        
        # Anillo exterior
        pen = QPen(base_color, 3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(-radius, -radius, radius*2, radius*2)
        
        # Anillo interior giratorio opuesto
        painter.rotate(-math.degrees(self.angle) * 2)
        pen.setColor(QColor(255, 255, 255, 150))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(-int(radius*0.7), -int(radius*0.7), int(radius*1.4), int(radius*1.4))
        
        # Núcleo central brillante
        painter.resetTransform()
        core_radius = int(radius * 0.3 * pulse_factor)
        core_grad = QRadialGradient(center_x, center_y, core_radius)
        core_grad.setColorAt(0, QColor(255, 255, 255))
        core_grad.setColorAt(0.5, base_color)
        core_grad.setColorAt(1, QColor(0, 0, 0))
        
        painter.setBrush(QBrush(core_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center_x - core_radius, center_y - core_radius, 
                            core_radius*2, core_radius*2)
        
        painter.restore()

class JarvisTray(QMainWindow):
    """Ventana principal que gestiona la bandeja del sistema y la vista de la esfera."""
    
    def __init__(self, jarvis_core):
        if not GUI_AVAILABLE:
            raise ImportError("PyQt6 no está instalado. Ejecuta: pip install PyQt6")
            
        super().__init__()
        self.jarvis = jarvis_core
        self.app = QApplication.instance() or QApplication(sys.argv)
        
        # Configurar ventana oculta (solo usamos el tray)
        self.setWindowState(Qt.WindowState.WindowMinimized)
        self.hide()

        # Configurar Icono de Bandeja
        self.tray_icon = QSystemTrayIcon(self)
        # Icono genérico de robot/círculo (se podría cargar uno .ico real)
        self.tray_icon.setIcon(self.app.style().standardIcon(QSystemTrayIcon.StandardIcon.ComputerIcon))
        self.tray_icon.setToolTip("JARVIS Assistant")

        # Menú Contextual
        tray_menu = QMenu()
        
        self.action_status = QAction("Estado: Esperando", self)
        self.action_status.setEnabled(False)
        tray_menu.addAction(self.action_status)
        
        tray_menu.addSeparator()
        
        action_activate = QAction("🎤 Activar Voz/Texto", self)
        action_activate.triggered.connect(self.activate_interaction)
        tray_menu.addAction(action_activate)
        
        action_show_last = QAction("📄 Leer última respuesta", self)
        action_show_last.triggered.connect(self.show_last_response)
        tray_menu.addAction(action_show_last)
        
        tray_menu.addSeparator()
        
        action_quit = QAction("🚫 Apagar JARVIS", self)
        action_quit.triggered.connect(self.shutdown_jarvis)
        tray_menu.addAction(action_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_click)
        self.tray_icon.show()

        # Ventana emergente de la Esfera
        self.sphere_window = QWidget()
        self.sphere_window.setWindowTitle("JARVIS Core")
        self.sphere_window.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.sphere_window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout()
        self.sphere_widget = ReactiveSphere()
        layout.addWidget(self.sphere_widget)
        self.sphere_window.setLayout(layout)
        self.sphere_window.resize(300, 300)
        
        # Mostrar la esfera inicialmente centrada en la pantalla
        screen_geo = self.app.primaryScreen().geometry()
        self.sphere_window.move(
            screen_geo.center().x() - 150,
            screen_geo.center().y() - 150
        )
        self.sphere_window.show()

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.activate_interaction()

    def update_state(self, state: str):
        """Actualiza el estado visual de la esfera desde el núcleo de JARVIS."""
        if hasattr(self, 'sphere_widget'):
            self.sphere_widget.set_state(state)
            if state == 'idle':
                self.action_status.setText("Estado: Esperando")
            elif state == 'listening':
                self.action_status.setText("Estado: Escuchando...")
            elif state == 'thinking':
                self.action_status.setText("Estado: Procesando...")
            elif state == 'speaking':
                self.action_status.setText("Estado: Respondiendo...")

    def activate_interaction(self):
        """Simula la activación desde el menú."""
        print("\n[GUI] Usuario solicitó interacción...")
        # Aquí podrías disparar un evento en el core para forzar input
        # Por simplicidad, mostramos la ventana si estaba oculta
        self.sphere_window.show()
        self.sphere_window.activateWindow()
        self.sphere_widget.set_state('listening')

    def show_last_response(self):
        """Muestra la última respuesta en consola o notificación."""
        last = self.jarvis.memory.get_last_response()
        if last:
            self.tray_icon.showMessage("Última respuesta de JARVIS", last[:100] + "...", 
                                       QSystemTrayIcon.MessageIcon.Information, 3000)
        else:
            self.tray_icon.showMessage("Sin historial", "Aún no hay respuestas.", 
                                       QSystemTrayIcon.MessageIcon.Warning, 2000)

    def shutdown_jarvis(self):
        """Cierra JARVIS limpiamente."""
        print("\n[GUI] Apagando sistema...")
        self.sphere_window.close()
        self.tray_icon.hide()
        self.app.quit()
        # Forzar salida del bucle principal si existe
        import os
        os._exit(0)

    def run(self):
        """Ejecuta el loop de eventos de Qt."""
        return self.app.exec()
