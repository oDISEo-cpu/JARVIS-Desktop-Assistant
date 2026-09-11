"""
Control del sistema: volumen, brillo, energía y bloqueo de pantalla.
Degrada elegantemente si las librerías específicas del OS no están disponibles.
"""

from __future__ import annotations

import ctypes
import platform
import subprocess
from typing import Any


def _is_windows() -> bool:
    return platform.system() == "Windows"


def set_volume(level: int) -> str:
    """
    Establece el volumen del sistema (0-100).

    Args:
        level: Nivel de volumen entre 0 y 100.

    Returns:
        Mensaje de resultado.
    """
    level = max(0, min(100, int(level)))
    if not _is_windows():
        return f"Volumen ajustado a {level}% (simulado en {platform.system()})"

    # Intentar pycaw primero
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Volumen establecido al {level}%"
    except Exception:
        pass

    # Fallback: PowerShell con AudioDeviceCmdlets o nircmd
    try:
        ps_cmd = (
            f"(New-Object -ComObject WScript.Shell).SendKeys([char]173); "
            f"$obj = New-Object -ComObject WScript.Shell; "
            f"1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}; "
            f"1..{level // 2} | ForEach-Object {{ $obj.SendKeys([char]175) }}"
        )
        subprocess.run(["powershell", "-Command", ps_cmd], check=False, capture_output=True)
        return f"Volumen ajustado aproximadamente al {level}%"
    except Exception as exc:
        return f"No pude ajustar el volumen: {exc}"


def get_volume() -> str:
    """Obtiene el volumen actual del sistema."""
    if not _is_windows():
        return "Volumen: no disponible en este sistema operativo"

    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current = int(volume.GetMasterVolumeLevelScalar() * 100)
        return f"Volumen actual: {current}%"
    except Exception:
        return "No pude leer el volumen exacto (pycaw no disponible en este equipo)"


def set_brightness(level: int) -> str:
    """
    Establece el brillo de la pantalla (0-100).

    Args:
        level: Nivel de brillo.

    Returns:
        Mensaje de resultado.
    """
    level = max(0, min(100, int(level)))
    if not _is_windows():
        return f"Brillo ajustado a {level}% (simulado)"

    try:
        import screen_brightness_control as sbc

        sbc.set_brightness(level)
        return f"Brillo establecido al {level}%"
    except Exception as exc:
        return f"No pude ajustar el brillo: {exc}"


def suspend_pc() -> str:
    """Suspende el equipo."""
    if _is_windows():
        try:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
            return "Suspendiendo el sistema..."
        except Exception as exc:
            return f"Error al suspender: {exc}"
    return "Suspensión no implementada para este SO"


def shutdown_pc() -> str:
    """Apaga el equipo (requiere confirmación previa del guard)."""
    if _is_windows():
        subprocess.run(["shutdown", "/s", "/t", "5"], check=False)
        return "Apagando el sistema en 5 segundos..."
    return "Apagado no implementado para este SO"


def restart_pc() -> str:
    """Reinicia el equipo."""
    if _is_windows():
        subprocess.run(["shutdown", "/r", "/t", "5"], check=False)
        return "Reiniciando el sistema en 5 segundos..."
    return "Reinicio no implementado para este SO"


def lock_screen() -> str:
    """Bloquea la pantalla del equipo."""
    if _is_windows():
        ctypes.windll.user32.LockWorkStation()
        return "Pantalla bloqueada"
    return "Bloqueo de pantalla no implementado para este SO"
