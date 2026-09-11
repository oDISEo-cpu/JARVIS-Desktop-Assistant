"""
Modo básico de JARVIS: comandos por palabras clave sin LLM.
Activo cuando no hay API key, internet o cuota agotada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from config import USUARIO_TRATO
from core.models import BrainResponse


@dataclass
class KeywordRule:
    """Regla de coincidencia por palabras clave."""

    patterns: list[str]
    tool: str | None
    params_builder: Any  # Callable[[re.Match], dict] | None
    response: str | None = None
    response_type: str = "action"


def _extract_after(pattern: str, text: str) -> str | None:
    """Extrae texto tras un patrón regex."""
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def process_basic_command(user_message: str) -> BrainResponse | None:
    """
    Intenta interpretar un comando sin LLM por coincidencia de palabras clave.

    Args:
        user_message: Texto del usuario.

    Returns:
        BrainResponse si hay coincidencia, None si no se reconoce.
    """
    text = user_message.strip()
    lower = text.lower()
    t = USUARIO_TRATO

    # ── Recuerda ──
    remember_match = re.match(r"(?:recuerda\s+que|recuerda)\s+(.+)", text, re.IGNORECASE)
    if remember_match:
        fact = remember_match.group(1).strip()
        return BrainResponse(
            type="remember",
            message=f"Queda registrado, {t}. He memorizado: {fact}",
            remember_fact=fact,
            reasoning="Modo básico: detección local de 'recuerda'",
        )

    # ── Abrir app ──
    app_name = _extract_after(r"(?:abre|abrir|lanza|inicia)\s+(?:la\s+app\s+|el\s+|la\s+)?(.+)", text)
    if app_name and not any(kw in lower for kw in ("http", "www", "google", "página", "pagina", "url")):
        return BrainResponse(
            type="action",
            message=f"Enseguida, {t}. Abriré {app_name}.",
            steps=[{"tool": "open_app", "params": {"name": app_name}, "description": f"Abrir {app_name}"}],
            reasoning="Modo básico: abrir aplicación",
        )

    # ── Buscar archivo ──
    file_query = _extract_after(r"(?:busca|buscar|encuentra)\s+(?:el\s+archivo\s+|archivo\s+)?(.+\.(?:pdf|docx?|xlsx?|txt|png|jpg|zip))", text)
    if not file_query:
        file_query = _extract_after(r"(?:busca|buscar|encuentra)\s+(?:el\s+archivo\s+)?(.+)", text)
    if file_query and "google" not in lower and "internet" not in lower:
        return BrainResponse(
            type="action",
            message=f"Buscaré '{file_query}' en sus documentos, {t}.",
            steps=[{"tool": "search_file", "params": {"query": file_query, "path": "~"}, "description": "Buscar archivo"}],
            reasoning="Modo básico: búsqueda de archivo",
        )

    # ── Búsqueda web ──
    web_query = _extract_after(r"(?:busca\s+en\s+google|google|buscar\s+en\s+internet)\s+(.+)", text)
    if web_query:
        return BrainResponse(
            type="action",
            message=f"Buscaré en Google: '{web_query}', {t}.",
            steps=[{"tool": "web_search", "params": {"query": web_query}, "description": "Búsqueda en Google"}],
            reasoning="Modo básico: búsqueda web",
        )

    # ── Abrir URL ──
    url_match = re.search(r"(https?://\S+|www\.\S+)", text, re.IGNORECASE)
    if url_match or any(kw in lower for kw in ("abre http", "visita http", "abre www")):
        url = url_match.group(1) if url_match else _extract_after(r"(?:abre|visita)\s+(.+)", text) or ""
        if url:
            return BrainResponse(
                type="action",
                message=f"Abriré esa página, {t}.",
                steps=[{"tool": "open_url", "params": {"url": url}, "description": "Abrir URL"}],
                reasoning="Modo básico: abrir URL",
            )

    # ── Listar ventanas ──
    if any(kw in lower for kw in ("ventanas abiertas", "lista ventanas", "qué ventanas", "que ventanas")):
        return BrainResponse(
            type="action",
            message=f"Permítame listar sus ventanas, {t}.",
            steps=[{"tool": "list_windows", "params": {}, "description": "Listar ventanas"}],
            reasoning="Modo básico: listar ventanas",
        )

    # ── Apagar PC (requiere confirmación en executor) ──
    if any(kw in lower for kw in ("apaga el pc", "apaga la computadora", "shutdown", "apagar pc")):
        return BrainResponse(
            type="action",
            message=f"Procederé a apagar el sistema, {t}. Se requerirá su confirmación.",
            steps=[{"tool": "shutdown_pc", "params": {}, "description": "Apagar PC"}],
            reasoning="Modo básico: apagado con confirmación",
        )

    # ── Bloquear pantalla ──
    if any(kw in lower for kw in ("bloquea", "bloquear pantalla", "lock screen")):
        return BrainResponse(
            type="action",
            message=f"Bloqueando la pantalla, {t}.",
            steps=[{"tool": "lock_screen", "params": {}, "description": "Bloquear pantalla"}],
            reasoning="Modo básico: bloqueo de pantalla",
        )

    # ── Volumen ──
    vol_match = re.search(r"(?:volumen|volume)\s+(?:al?\s+)?(\d+)", lower)
    if vol_match:
        level = int(vol_match.group(1))
        return BrainResponse(
            type="action",
            message=f"Ajustaré el volumen al {level}%, {t}.",
            steps=[{"tool": "set_volume", "params": {"level": level}, "description": "Ajustar volumen"}],
            reasoning="Modo básico: volumen",
        )

    # ── Ayuda ──
    if lower in ("ayuda", "help", "qué puedes hacer", "que puedes hacer", "/help"):
        return BrainResponse(
            type="conversation",
            message=(
                f"Modo básico activo, {t}. Puedo: abrir apps, buscar archivos, "
                "buscar en Google, abrir URLs, listar ventanas, ajustar volumen, "
                "bloquear pantalla y apagar (con confirmación). "
                "Configure un LLM en .env para capacidades completas."
            ),
            reasoning="Modo básico: ayuda",
        )

    return None
