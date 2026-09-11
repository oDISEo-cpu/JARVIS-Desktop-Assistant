"""
Chequeo de estado de subsistemas de JARVIS.
Permite degradación elegante sin crashear al iniciar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class SubsystemStatus:
    """Estado de un subsistema individual."""

    name: str
    available: bool
    message: str
    degraded_to: str | None = None


@dataclass
class SystemReport:
    """Informe completo del estado del sistema."""

    subsystems: list[SubsystemStatus] = field(default_factory=list)

    def add(self, name: str, available: bool, message: str, degraded_to: str | None = None) -> None:
        self.subsystems.append(SubsystemStatus(name, available, message, degraded_to))

    def as_dict(self) -> dict[str, bool]:
        return {s.name: s.available for s in self.subsystems}


def _safe_check(name: str, checker: Callable[[], tuple[bool, str]], degraded: str | None = None) -> SubsystemStatus:
    """Ejecuta un chequeo capturando cualquier excepción."""
    try:
        ok, msg = checker()
        return SubsystemStatus(name, ok, msg, degraded if not ok else None)
    except Exception as exc:
        return SubsystemStatus(name, False, str(exc), degraded)


def check_llm() -> tuple[bool, str]:
    """Verifica disponibilidad del LLM configurado."""
    from core.brain import create_llm_provider
    from config import LLM_PROVIDER, OPENAI_API_KEY, ANTHROPIC_API_KEY

    if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        return False, "OPENAI_API_KEY no configurada"
    if LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        return False, "ANTHROPIC_API_KEY no configurada"

    provider = create_llm_provider()
    return provider.test_connection()


def check_stt() -> tuple[bool, str]:
    """Verifica reconocimiento de voz (STT)."""
    from perception.listener import VoiceListener
    listener = VoiceListener(engine="google")
    if listener.is_available:
        return True, "Micrófono operativo"
    return False, "Micrófono o PyAudio no disponible"


def check_tts() -> tuple[bool, str]:
    """Verifica síntesis de voz (TTS)."""
    from voice.speaker import Speaker
    speaker = Speaker()
    if speaker.is_available:
        return True, "TTS operativo"
    return False, "pyttsx3 no disponible"


def check_automation() -> tuple[bool, str]:
    """Verifica módulos de automatización."""
    import pyautogui  # noqa: F401
    import pygetwindow  # noqa: F401
    return True, "PyAutoGUI y pygetwindow OK"


def check_memory() -> tuple[bool, str]:
    from core.memory import Memory
    m = Memory()
    return True, f"Memoria OK ({len(m.get_all_memories())} recuerdos)"


def run_subsystem_checks(input_mode: str = "text") -> SystemReport:
    """
    Ejecuta chequeo de todos los subsistemas.

    Args:
        input_mode: Modo de entrada activo para mensajes de degradación.

    Returns:
        Informe completo.
    """
    report = SystemReport()

    report.subsystems.append(_safe_check("Memoria", check_memory))
    report.subsystems.append(_safe_check(
        "Cerebro (LLM)", check_llm, "modo básico (palabras clave)",
    ))
    report.subsystems.append(_safe_check("Automatización", check_automation))

    if input_mode in ("voice", "hybrid"):
        stt = _safe_check("Reconocimiento de voz (STT)", check_stt, "modo texto")
        report.subsystems.append(stt)
        tts = _safe_check("Síntesis de voz (TTS)", check_tts, "solo texto")
        report.subsystems.append(tts)
    else:
        report.add("Reconocimiento de voz (STT)", False, "Modo texto — voz no requerida", "modo texto")
        report.add("Síntesis de voz (TTS)", False, "Modo texto — TTS no requerido", "solo texto")

    report.add("Entrada texto", True, "Operativo")
    return report
