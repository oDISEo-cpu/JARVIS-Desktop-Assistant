"""
Módulo GUI de JARVIS.
Proporciona interfaz gráfica opcional con widget de esfera reactiva.
"""

from .tray import JarvisTray, ReactiveSphere

__all__ = ['JarvisTray', 'ReactiveSphere']

# Verificar disponibilidad
try:
    from .tray import GUI_AVAILABLE
except ImportError:
    GUI_AVAILABLE = False
