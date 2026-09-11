"""Modelos de datos compartidos del núcleo de JARVIS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ResponseType = Literal["conversation", "action", "remember"]


@dataclass
class BrainResponse:
    """Respuesta estructurada del cerebro de JARVIS."""

    type: ResponseType
    message: str
    steps: list[dict[str, Any]] | None = None
    reasoning: str = ""
    remember_fact: str | None = None
    raw_json: str | None = None
    basic_mode: bool = False
