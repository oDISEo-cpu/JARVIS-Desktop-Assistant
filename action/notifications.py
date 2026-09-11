"""
Notificaciones del sistema.
Usa plyer con fallback a consola.
"""

from __future__ import annotations


def notify(title: str, message: str, timeout: int = 5) -> str:
    """
    Muestra una notificación del sistema.

    Args:
        title: Título de la notificación.
        message: Cuerpo del mensaje.
        timeout: Duración en segundos.

    Returns:
        Mensaje de confirmación.
    """
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            timeout=timeout,
            app_name="JARVIS",
        )
        return f"Notificación enviada: {title}"
    except Exception:
        # Fallback: imprimir en consola
        print(f"\n🔔 [{title}] {message}")
        return f"Notificación (consola): {title} — {message}"
