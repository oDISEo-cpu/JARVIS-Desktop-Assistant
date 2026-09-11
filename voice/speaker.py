"""
Síntesis de voz con pyttsx3.
Voz masculina en español, estilo JARVIS.
"""

from __future__ import annotations

import threading

from config import TTS_RATE, TTS_VOICE_INDEX, TTS_VOLUME


class Speaker:
    """Convierte texto a voz usando pyttsx3."""

    def __init__(
        self,
        rate: int = TTS_RATE,
        volume: float = TTS_VOLUME,
        voice_index: int = TTS_VOICE_INDEX,
    ) -> None:
        self._rate = rate
        self._volume = volume
        self._voice_index = voice_index
        self._engine = None
        self._lock = threading.Lock()
        self._available = False
        self._init_engine()

    def _init_engine(self) -> None:
        """Inicializa el motor TTS."""
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate)
            self._engine.setProperty("volume", self._volume)
            self._select_voice()
            self._available = True
        except Exception as exc:
            print(f"[Speaker] TTS no disponible: {exc}")
            self._available = False

    def _select_voice(self) -> None:
        """Selecciona voz masculina en español si está disponible."""
        if self._engine is None:
            return

        voices = self._engine.getProperty("voices")
        if not voices:
            return

        # Prioridad: voz española masculina
        preferred_keywords = ["spanish", "español", "helena", "pablo", "male", "david"]
        selected = None

        for voice in voices:
            name_lower = (voice.name or "").lower()
            id_lower = (voice.id or "").lower()
            if any(kw in name_lower or kw in id_lower for kw in preferred_keywords):
                selected = voice
                break

        if selected:
            self._engine.setProperty("voice", selected.id)
        elif 0 <= self._voice_index < len(voices):
            self._engine.setProperty("voice", voices[self._voice_index].id)

    @property
    def is_available(self) -> bool:
        """Indica si TTS está operativo."""
        return self._available

    def speak(self, text: str, block: bool = True) -> None:
        """
        Reproduce texto como voz.

        Args:
            text: Texto a pronunciar.
            block: Si True, espera a que termine de hablar.
        """
        if not self._available or self._engine is None or not text.strip():
            return

        with self._lock:
            try:
                self._engine.say(text)
                if block:
                    self._engine.runAndWait()
                else:
                    self._engine.startLoop(False)
                    self._engine.iterate()
                    self._engine.endLoop()
            except Exception as exc:
                print(f"[Speaker] Error al hablar: {exc}")

    def speak_async(self, text: str) -> threading.Thread:
        """
        Habla en un hilo separado para no bloquear el bucle principal.

        Args:
            text: Texto a pronunciar.

        Returns:
            Hilo de ejecución.
        """
        thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        thread.start()
        return thread

    def list_voices(self) -> list[str]:
        """Lista las voces disponibles en el sistema."""
        if not self._available or self._engine is None:
            return []
        return [f"{v.name} ({v.id})" for v in self._engine.getProperty("voices")]
