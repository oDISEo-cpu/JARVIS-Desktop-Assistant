"""
Configuración global de JARVIS.
Centraliza API keys, proveedor LLM, voz, idioma y rutas.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

# ── Rutas base ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MEMORY_FILE = DATA_DIR / "memory.json"
ROUTINES_DB = DATA_DIR / "routines.db"
ACTION_LOG_FILE = LOGS_DIR / "actions.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── Modo de entrada ─────────────────────────────────────────────────────────
InputMode = Literal["text", "voice", "hybrid"]
INPUT_MODE: InputMode = os.getenv("JARVIS_INPUT_MODE", "text")  # type: ignore[assignment]

# ── Personalidad ────────────────────────────────────────────────────────────
UserAddress = Literal["señor", "señorita"]
USUARIO_TRATO: UserAddress = os.getenv("USUARIO_TRATO", "señor")  # type: ignore[assignment]

# ── Proveedor LLM ───────────────────────────────────────────────────────────
LLMProvider = Literal["openai", "anthropic", "ollama"]
LLM_PROVIDER: LLMProvider = os.getenv("LLM_PROVIDER", "openai")  # type: ignore[assignment]

# Modelo unificado (override por proveedor si está vacío)
LLM_MODEL: str = os.getenv("LLM_MODEL", "")

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "ollama")  # Ollama no requiere clave real

# Timeout para llamadas al LLM (segundos). Mínimo 120 para modelos grandes en CPU.
LLM_TIMEOUT: int = max(120, int(os.getenv("LLM_TIMEOUT", "120")))


def get_llm_model() -> str:
    """Devuelve el modelo activo según proveedor y LLM_MODEL."""
    if LLM_MODEL:
        return LLM_MODEL
    mapping = {"openai": OPENAI_MODEL, "anthropic": ANTHROPIC_MODEL, "ollama": OLLAMA_MODEL}
    return mapping.get(LLM_PROVIDER, OPENAI_MODEL)


# ── Idioma y voz ────────────────────────────────────────────────────────────
LANGUAGE: str = os.getenv("JARVIS_LANGUAGE", "es-ES")
WAKE_WORD: str = os.getenv("JARVIS_WAKE_WORD", "jarvis")

TTS_RATE: int = int(os.getenv("JARVIS_TTS_RATE", "165"))
TTS_VOLUME: float = float(os.getenv("JARVIS_TTS_VOLUME", "1.0"))
TTS_VOICE_INDEX: int = int(os.getenv("JARVIS_TTS_VOICE_INDEX", "-1"))

SPEECH_ENGINE: str = os.getenv("JARVIS_SPEECH_ENGINE", "google")
VOSK_MODEL_PATH: str = os.getenv("VOSK_MODEL_PATH", "")
MIC_TIMEOUT: float = float(os.getenv("JARVIS_MIC_TIMEOUT", "5"))
MIC_PHRASE_LIMIT: float = float(os.getenv("JARVIS_MIC_PHRASE_LIMIT", "15"))

# ── Memoria ─────────────────────────────────────────────────────────────────
MAX_CONVERSATION_HISTORY: int = int(os.getenv("JARVIS_MAX_HISTORY", "20"))
ROUTINE_MIN_OCCURRENCES: int = int(os.getenv("JARVIS_ROUTINE_MIN", "3"))
ROUTINE_HOUR_TOLERANCE: int = int(os.getenv("JARVIS_ROUTINE_HOUR_TOL", "1"))

# ── Seguridad ───────────────────────────────────────────────────────────────
SHELL_WHITELIST: list[str] = [
    "dir", "ls", "echo", "type", "cat", "pwd", "cd", "where", "whoami",
    "hostname", "ipconfig", "ping", "tasklist", "systeminfo", "date", "time",
    "python", "pip", "git", "node", "npm",
]

DESTRUCTIVE_KEYWORDS: list[str] = [
    "rm", "del", "rmdir", "format", "shutdown", "restart", "reboot",
    "kill", "taskkill", "remove-item", "erase", "wipe",
]

# ── UI ────────────────────────────────────────────────────────────────────────
# Voz desactivada por defecto; modo texto prioritario
ENABLE_VOICE: bool = os.getenv("JARVIS_ENABLE_VOICE", "false").lower() == "true"
WEB_CHAT_HOST: str = os.getenv("JARVIS_WEB_HOST", "127.0.0.1")
WEB_CHAT_PORT: int = int(os.getenv("JARVIS_WEB_PORT", "8000"))

# ── Mensajes ──────────────────────────────────────────────────────────────────
GREETING: str = "Sistemas en línea. ¿En qué puedo ayudarle?"
FAREWELL: str = "Hasta luego. Apagando sistemas."
EXIT_PHRASES: list[str] = ["apagar jarvis", "hasta luego", "salir", "cerrar jarvis", "adiós"]


@dataclass
class JarvisConfig:
    """Contenedor de configuración para inyección de dependencias."""

    input_mode: InputMode = INPUT_MODE
    llm_provider: LLMProvider = LLM_PROVIDER
    language: str = LANGUAGE
    wake_word: str = WAKE_WORD
    user_address: UserAddress = USUARIO_TRATO
    enable_voice: bool = ENABLE_VOICE
    max_history: int = MAX_CONVERSATION_HISTORY
    shell_whitelist: list[str] = field(default_factory=lambda: SHELL_WHITELIST.copy())
    destructive_keywords: list[str] = field(default_factory=lambda: DESTRUCTIVE_KEYWORDS.copy())


config = JarvisConfig()
