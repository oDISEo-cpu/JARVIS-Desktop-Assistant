"""
Control de aplicaciones y ventanas.
Abrir/cerrar apps, listar y manipular ventanas con pygetwindow y psutil.
"""

from __future__ import annotations

import os
import subprocess
import platform
from typing import Any


def _is_windows() -> bool:
    return platform.system() == "Windows"


def open_app(name: str) -> str:
    """
    Abre una aplicación por nombre o ruta.

    Args:
        name: Nombre del ejecutable, ruta o comando (ej. 'notepad', 'chrome').

    Returns:
        Mensaje de resultado.
    """
    try:
        if _is_windows():
            # Intentar abrir con 'start' de Windows
            os.startfile(name)  # type: ignore[attr-defined]
            return f"Aplicación '{name}' abierta"
        else:
            subprocess.Popen([name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Aplicación '{name}' iniciada"
    except FileNotFoundError:
        # Intentar como comando del sistema
        try:
            subprocess.Popen(name, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Comando '{name}' ejecutado"
        except Exception as exc:
            return f"No pude abrir '{name}': {exc}"
    except Exception as exc:
        return f"Error al abrir '{name}': {exc}"


def close_app(name: str) -> str:
    """
    Cierra procesos cuyo nombre coincida.

    Args:
        name: Nombre del proceso o aplicación.

    Returns:
        Mensaje con procesos cerrados.
    """
    try:
        import psutil

        closed = 0
        name_lower = name.lower().replace(".exe", "")
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = (proc.info["name"] or "").lower().replace(".exe", "")
                if name_lower in proc_name:
                    proc.terminate()
                    closed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if closed:
            return f"Cerrados {closed} proceso(s) relacionados con '{name}'"
        return f"No encontré procesos activos para '{name}'"
    except ImportError:
        return "psutil no disponible para cerrar aplicaciones"
    except Exception as exc:
        return f"Error al cerrar '{name}': {exc}"


def list_windows() -> str:
    """Lista las ventanas abiertas visibles."""
    try:
        import pygetwindow as gw

        windows = gw.getAllWindows()
        visible = [w for w in windows if w.title.strip()]
        if not visible:
            return "No hay ventanas visibles"

        lines = [f"- {w.title}" for w in visible[:20]]
        extra = f"\n... y {len(visible) - 20} más" if len(visible) > 20 else ""
        return f"Ventanas abiertas ({len(visible)}):\n" + "\n".join(lines) + extra
    except Exception as exc:
        return f"No pude listar ventanas: {exc}"


def _find_window(title: str) -> Any:
    """Busca una ventana por título parcial."""
    import pygetwindow as gw

    matches = gw.getWindowsWithTitle(title)
    if matches:
        return matches[0]
    # Búsqueda parcial
    for w in gw.getAllWindows():
        if title.lower() in w.title.lower():
            return w
    return None


def focus_window(title: str) -> str:
    """Enfoca una ventana por título."""
    try:
        win = _find_window(title)
        if win:
            win.activate()
            return f"Ventana '{win.title}' enfocada"
        return f"No encontré ventana con título '{title}'"
    except Exception as exc:
        return f"Error al enfocar ventana: {exc}"


def minimize_window(title: str) -> str:
    """Minimiza una ventana por título."""
    try:
        win = _find_window(title)
        if win:
            win.minimize()
            return f"Ventana '{win.title}' minimizada"
        return f"No encontré ventana '{title}'"
    except Exception as exc:
        return f"Error al minimizar: {exc}"


def maximize_window(title: str) -> str:
    """Maximiza una ventana por título."""
    try:
        win = _find_window(title)
        if win:
            win.maximize()
            return f"Ventana '{win.title}' maximizada"
        return f"No encontré ventana '{title}'"
    except Exception as exc:
        return f"Error al maximizar: {exc}"
