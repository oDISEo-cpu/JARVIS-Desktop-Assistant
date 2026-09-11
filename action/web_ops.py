"""
Operaciones web: abrir URLs y búsquedas en Google.
"""

from __future__ import annotations

import urllib.parse
import webbrowser


def open_url(url: str) -> str:
    """
    Abre una URL en el navegador predeterminado.

    Args:
        url: URL completa o parcial (se añade https:// si falta).

    Returns:
        Mensaje de confirmación.
    """
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    try:
        webbrowser.open(url)
        return f"Abriendo {url}"
    except Exception as exc:
        return f"Error al abrir URL: {exc}"


def web_search(query: str) -> str:
    """
    Realiza una búsqueda en Google.

    Args:
        query: Términos de búsqueda.

    Returns:
        Mensaje de confirmación.
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"
    try:
        webbrowser.open(url)
        return f"Buscando en Google: '{query}'"
    except Exception as exc:
        return f"Error en búsqueda web: {exc}"
