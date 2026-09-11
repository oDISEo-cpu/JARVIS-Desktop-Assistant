"""
Reconocimiento de voz con speech_recognition.
Soporta Google Web Speech API y degrada a solo-texto si no hay micrófono.
"""

from __future__ import annotations

from typing import Callable

from config import LANGUAGE, MIC_PHRASE_LIMIT, MIC_TIMEOUT, SPEECH_ENGINE, VOSK_MODEL_PATH, WAKE_WORD


class VoiceListener:
    """Escucha y transcribe voz del usuario."""

    def __init__(
        self,
        language: str = LANGUAGE,
        engine: str = SPEECH_ENGINE,
        wake_word: str = WAKE_WORD,
        on_partial: Callable[[str], None] | None = None,
    ) -> None:
        self._language = language
        self._engine = engine.lower()
        self._wake_word = wake_word.lower()
        self._on_partial = on_partial
        self._recognizer = None
        self._microphone = None
        self._available = False
        self._init_engine()

    def _init_engine(self) -> None:
        """Inicializa el motor de reconocimiento de voz."""
        if self._engine == "none":
            return

        try:
            import speech_recognition as sr

            self._recognizer = sr.Recognizer()
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.energy_threshold = 300

            # Intentar acceder al micrófono
            self._microphone = sr.Microphone()
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self._available = True
        except Exception as exc:
            print(f"[Listener] Voz no disponible: {exc}. Modo solo-texto activado.")
            self._available = False

    @property
    def is_available(self) -> bool:
        """Indica si el reconocimiento de voz está operativo."""
        return self._available

    def listen(self, timeout: float | None = None, phrase_limit: float | None = None) -> str | None:
        """
        Escucha del micrófono y transcribe a texto.

        Args:
            timeout: Segundos máximos esperando que el usuario hable.
            phrase_limit: Duración máxima de la frase.

        Returns:
            Texto transcrito o None si falla/timeout.
        """
        if not self._available or self._recognizer is None or self._microphone is None:
            return None

        timeout = timeout or MIC_TIMEOUT
        phrase_limit = phrase_limit or MIC_PHRASE_LIMIT

        import speech_recognition as sr

        try:
            with self._microphone as source:
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit,
                )
            return self._transcribe(audio)
        except sr.WaitTimeoutError:
            return None
        except Exception as exc:
            print(f"[Listener] Error al escuchar: {exc}")
            return None

    def _transcribe(self, audio: object) -> str | None:
        """Transcribe audio usando el motor configurado."""
        import speech_recognition as sr

        try:
            if self._engine == "vosk" and VOSK_MODEL_PATH:
                # Vosk offline (requiere modelo descargado)
                return self._recognizer.recognize_vosk(audio)  # type: ignore[union-attr]
            # Google Web Speech API (gratuito, requiere internet)
            return self._recognizer.recognize_google(audio, language=self._language)  # type: ignore[union-attr]
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            print(f"[Listener] Error del servicio de voz: {exc}")
            return None

    def contains_wake_word(self, text: str) -> bool:
        """Comprueba si el texto contiene la palabra de activación."""
        return self._wake_word in text.lower()

    def strip_wake_word(self, text: str) -> str:
        """Elimina la palabra de activación del texto."""
        import re

        pattern = re.compile(re.escape(self._wake_word), re.IGNORECASE)
        return pattern.sub("", text).strip()

    def listen_for_wake_word(self) -> str | None:
        """
        Escucha continuamente hasta detectar la palabra de activación.

        Returns:
            Comando del usuario tras la palabra de activación, o None.
        """
        while True:
            text = self.listen(timeout=3, phrase_limit=5)
            if text and self.contains_wake_word(text):
                command = self.strip_wake_word(text)
                if command:
                    return command
                # Si solo dijo "Jarvis", escuchar el comando
                return self.listen()
