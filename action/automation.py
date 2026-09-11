"""
Automatización con PyAutoGUI y portapapeles.
Clicks, teclado, capturas de pantalla y clipboard.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config import BASE_DIR


def click(x: int, y: int, button: str = "left") -> str:
    """
    Hace click en coordenadas de pantalla.

    Args:
        x: Coordenada horizontal.
        y: Coordenada vertical.
        button: Botón del mouse ('left', 'right', 'middle').

    Returns:
        Mensaje de confirmación.
    """
    try:
        import pyautogui

        pyautogui.FAILSAFE = True
        pyautogui.click(int(x), int(y), button=button)
        return f"Click en ({x}, {y}) con botón '{button}'"
    except Exception as exc:
        return f"Error en click: {exc}"


def type_text(text: str, interval: float = 0.02) -> str:
    """
    Escribe texto simulando el teclado.

    Args:
        text: Texto a escribir.
        interval: Pausa entre teclas.

    Returns:
        Mensaje de confirmación.
    """
    try:
        import pyautogui

        pyautogui.write(text, interval=interval)
        return f"Texto escrito: '{text[:50]}{'...' if len(text) > 50 else ''}'"
    except Exception as exc:
        return f"Error al escribir texto: {exc}"


def screenshot(save_path: str | None = None) -> str:
    """
    Toma una captura de pantalla.

    Args:
        save_path: Ruta opcional para guardar. Si no se indica, usa data/screenshots/.

    Returns:
        Ruta del archivo guardado.
    """
    try:
        import pyautogui

        if save_path is None:
            screenshots_dir = BASE_DIR / "data" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = str(screenshots_dir / f"screenshot_{timestamp}.png")

        img = pyautogui.screenshot()
        img.save(save_path)
        return f"Captura guardada en: {save_path}"
    except Exception as exc:
        return f"Error en captura de pantalla: {exc}"


def clipboard_read() -> str:
    """Lee el contenido del portapapeles."""
    try:
        import pyperclip

        content = pyperclip.paste()
        if not content:
            return "Portapapeles vacío"
        preview = content[:500] + ("..." if len(content) > 500 else "")
        return f"Portapapeles: {preview}"
    except Exception as exc:
        return f"Error al leer portapapeles: {exc}"


def clipboard_write(text: str) -> str:
    """Escribe texto en el portapapeles."""
    try:
        import pyperclip

        pyperclip.copy(text)
        return f"Portapapeles actualizado con: '{text[:50]}{'...' if len(text) > 50 else ''}'"
    except Exception as exc:
        return f"Error al escribir en portapapeles: {exc}"
