"""
JARVIS — Punto de entrada principal.
Bucle: escuchar/leer → pensar → ejecutar → responder.
Nunca crashea por fallo de un subsistema individual.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from typing import Any, Optional

from config import (
    EXIT_PHRASES,
    FAREWELL,
    GREETING,
    INPUT_MODE,
    USUARIO_TRATO,
    config,
)
from core.brain import Brain, ensure_message_str
from core.memory import Memory
from core.planner import Planner
from core.subsystems import run_subsystem_checks
from action.executor import Executor
from perception.reader import ChatReader
from security.guard import SecurityGuard
from ui.console_ui import ConsoleUI

# Importación opcional del módulo GUI
try:
    from gui.tray import JarvisTray
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


class JarvisAssistant:
    """Orquestador principal del asistente JARVIS."""

    def __init__(
        self,
        input_mode: str | None = None,
        dry_run: bool = False,
        gui_mode: bool = False,
    ) -> None:
        self.input_mode = input_mode or INPUT_MODE
        self.dry_run = dry_run
        self.gui_mode = gui_mode and GUI_AVAILABLE

        self.ui = ConsoleUI()
        self.chat = ChatReader(console=self.ui.console)
        self.memory = Memory(max_history=config.max_history)
        self.planner = Planner()
        self.guard = SecurityGuard(
            whitelist=config.shell_whitelist,
            destructive_keywords=config.destructive_keywords,
            confirm_callback=self._confirm_action,
        )

        # Cerebro: puede degradar a modo básico automáticamente
        self.brain = Brain(memory=self.memory, planner=self.planner)
        self.executor = Executor(
            guard=self.guard,
            planner=self.planner,
            memory=self.memory,
            dry_run=dry_run,
        )

        # Subsistemas opcionales — carga perezosa, nunca crashea
        self._speaker: Any = None
        self._listener: Any = None
        self._running = False
        self._tray: Optional[JarvisTray] = None

    def _load_voice_modules(self) -> None:
        """Carga módulos de voz solo si el modo lo requiere."""
        if self.input_mode == "text":
            return
        try:
            from voice.speaker import Speaker
            self._speaker = Speaker()
        except Exception:
            self._speaker = None
        try:
            from perception.listener import VoiceListener
            from config import WAKE_WORD
            self._listener = VoiceListener(wake_word=WAKE_WORD)
        except Exception:
            self._listener = None

    def _handle_web_message(self, user_text: str) -> dict[str, Any]:
        """
        Procesa un mensaje del chat web y devuelve respuesta estructurada.
        Usado por POST /api/chat y WebSocket /ws.
        DEPRECATED: Interfaz web eliminada según reglas del proyecto.
        """
        raise NotImplementedError("Interfaz web eliminada. JARVIS es solo terminal.")

    @property
    def speaker_available(self) -> bool:
        return self._speaker is not None and getattr(self._speaker, "is_available", False)

    @property
    def listener_available(self) -> bool:
        return self._listener is not None and getattr(self._listener, "is_available", False)

    def _run_llm_diag(self) -> None:
        """Re-ejecuta diagnóstico del LLM (comando /diag)."""
        self.chat.add_system_message("Ejecutando diagnóstico del LLM...")
        report = self.brain.run_diagnostics()
        for line in report.lines:
            self.chat.add_system_message(line)
        if report.ok:
            self.chat.add_system_message("Diagnóstico: LLM operativo.")
        else:
            self.chat.add_system_message(
                f"Diagnóstico: LLM OFFLINE — {report.error or 'error desconocido'}"
            )

    def _confirm_action(self, message: str) -> bool:
        self.ui.show_info(f"⚠️  Confirmación requerida: {message}")
        answer = self.ui.prompt("¿Confirmar? (s/n): ").strip().lower()
        return answer in ("s", "si", "sí", "y", "yes")

    def initialize(self) -> None:
        """Inicializa módulos y muestra estado estilo JARVIS."""
        self.ui.show_banner()

        if self.dry_run:
            self.ui.show_info("[bold yellow]MODO DRY-RUN[/bold yellow] — ninguna acción se ejecutará.")

        # Chequeo de subsistemas (tabla base)
        report = run_subsystem_checks(self.input_mode)
        modules = {s.name: s.available for s in report.subsystems}

        # Chequeo honesto del LLM: chat real con el modelo configurado
        llm_ok, llm_msg = self.brain.llm_status
        modules["Cerebro (LLM)"] = llm_ok
        self.ui.show_status(modules)

        if self.brain.model_notice:
            self.chat.add_system_message(self.brain.model_notice)

        if llm_ok:
            self.chat.add_system_message(f"Cerebro (LLM): {llm_msg}")
        else:
            self.chat.add_system_message(f"Cerebro (LLM): OFFLINE — {llm_msg}")

        for s in report.subsystems:
            if s.name == "Cerebro (LLM)":
                continue
            if not s.available and s.degraded_to:
                self.chat.add_system_message(f"Módulo {s.name}: no disponible → degradando a {s.degraded_to}")
            elif not s.available:
                self.chat.add_system_message(f"Módulo {s.name}: no disponible ({s.message})")

        if self.brain.is_basic_mode and not llm_ok:
            self.chat.add_system_message(
                "Modo básico activo (comandos por palabras clave). "
                "Escriba /diag para volver a probar el LLM."
            )

        self._load_voice_modules()

        # Inicializar GUI si está habilitado
        if self.gui_mode:
            self._init_gui()

        # Mostrar resumen de contexto del usuario (nuevo)
        context_summary = self.memory.get_context_summary()
        if "(Sin contexto guardado)" not in context_summary:
            self.chat.add_system_message(context_summary)

        suggestion = self.memory.get_startup_suggestion()
        greeting = GREETING
        if suggestion:
            greeting = f"{GREETING}\n\n{suggestion}"
        self.chat.add_jarvis_message(greeting)
        if self.speaker_available and self.input_mode != "text":
            self._speaker.speak_async(greeting.split("\n")[0])

    def _init_gui(self) -> None:
        """Inicializa el widget de la bandeja del sistema con la esfera reactiva."""
        try:
            self._tray = JarvisTray(self)
            self.chat.add_system_message("🖥️ Widget de escritorio activado. Revisa la bandeja del sistema.")
        except Exception as e:
            self.chat.add_system_message(f"⚠️ No se pudo iniciar el widget GUI: {e}")
            self.gui_mode = False

    def _should_exit(self, text: str) -> bool:
        text_lower = text.lower().strip()
        return text_lower in ("salir", "exit", "quit") or any(p in text_lower for p in EXIT_PHRASES)

    def _get_input_text(self) -> str | None:
        """Obtiene entrada según el modo configurado."""
        use_voice = self.input_mode in ("voice", "hybrid") and self.listener_available

        if use_voice and self.input_mode == "voice":
            self.ui.show_listening()
            text = self._listener.listen()
            if text:
                self.chat.add_user_message(text)
                return text
            self.chat.add_system_message("No se detectó voz. Escriba su comando:")
            return self.chat.read()

        if use_voice and self.input_mode == "hybrid":
            # Hybrid: intentar voz con timeout corto, siempre aceptar texto
            self.ui.show_listening()
            text = self._listener.listen(timeout=2)
            if text:
                self.chat.add_user_message(text)
                return text

        return self.chat.read()

    def _process_input(self, user_text: str) -> bool:
        """Procesa una entrada. Retorna False para salir."""
        if not user_text:
            return True

        if self._should_exit(user_text):
            farewell = f"{FAREWELL} Hasta pronto, {USUARIO_TRATO}."
            self.chat.add_jarvis_message(farewell)
            if self.speaker_available:
                self._speaker.speak(farewell)
            return False

        if user_text.strip().lower() in ("/diag", "diag"):
            self._run_llm_diag()
            return True

        self.chat.add_thinking()
        try:
            response = self.brain.process(user_text)
        except Exception as exc:
            self.ui.show_error(f"Error en el cerebro: {exc}")
            traceback.print_exc()
            return True

        if response.basic_mode and self.brain.last_llm_error:
            self.chat.add_system_message(f"Error LLM: {self.brain.last_llm_error}")
        elif response.basic_mode:
            self.chat.add_system_message("(Modo básico activo)")

        if response.reasoning:
            self.ui.show_reasoning(response.reasoning)

        # Dry-run: mostrar JSON crudo del LLM
        if self.dry_run and response.raw_json:
            self.ui.console.print("[dim]JSON del LLM:[/dim]")
            try:
                formatted = json.dumps(json.loads(response.raw_json), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                formatted = response.raw_json
            self.ui.console.print(formatted)

        execution_result = ""
        if response.type == "action" and response.steps:
            for step in response.steps:
                self.ui.show_executing(step["tool"], step.get("params"))
            execution_result = self.executor.execute_plan(response.steps, response.reasoning or "")
            self.ui.show_execution_result(execution_result)
            # Guardar plan solo si todos los pasos tuvieron éxito
            if execution_result and "✗" not in execution_result:
                self.memory.set_last_plan(response.steps, response.reasoning or "")

        # Defensa doble: message siempre str antes de UI/TTS
        safe_message = ensure_message_str(response.message, response.steps)
        final_message = safe_message
        if execution_result:
            final_message = f"{safe_message}\n\n{execution_result}"

        self.chat.add_jarvis_message(final_message)

        # Actualizar estado de la esfera GUI si está disponible
        if self.gui_mode and self._tray:
            self._tray.update_state('speaking')

        if self.speaker_available and self.input_mode != "text":
            short = safe_message.split("\n")[0]
            self._speaker.speak_async(short)

        # Resetear estado de la esfera después de responder
        if self.gui_mode and self._tray:
            # Pequeño delay para volver a idle (en producción usar QTimer.singleShot)
            import time
            time.sleep(0.5)
            self._tray.update_state('idle')

        return True

    def run(self) -> None:
        """Bucle principal de terminal."""
        try:
            self.initialize()
        except Exception as exc:
            self.ui.show_error(f"Error en inicialización (continuando): {exc}")

        self._run_terminal_loop()

    def _run_terminal_loop(self) -> None:
        """Bucle interactivo por terminal."""
        self._running = True
        mode_label = {"text": "texto", "voice": "voz", "hybrid": "híbrido"}.get(self.input_mode, self.input_mode)
        self.chat.show_help_hint()
        self.chat.add_system_message(
            f"Modo {mode_label} activo. Escriba 'salir' o 'hasta luego' para cerrar."
        )

        while self._running:
            try:
                user_text = self._get_input_text()
                if user_text is None:
                    break
                if not self._process_input(user_text):
                    break
            except KeyboardInterrupt:
                self.chat.add_system_message("Interrupción detectada.")
                break
            except Exception as exc:
                self.ui.show_error(f"Error inesperado (continuando): {exc}")
                traceback.print_exc()
                continue

        self.chat.add_system_message("JARVIS finalizado.")


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="JARVIS — Asistente Virtual")
    parser.add_argument(
        "--input-mode", choices=["text", "voice", "hybrid"],
        default=None, help="Modo de entrada (default: text)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Genera planes sin ejecutar acciones",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Activa el widget de escritorio con esfera reactiva (requiere PyQt6)",
    )
    return parser.parse_args()


def main() -> None:
    """Punto de entrada."""
    args = parse_args()
    assistant = JarvisAssistant(
        input_mode=args.input_mode,
        dry_run=args.dry_run,
        gui_mode=args.gui,
    )
    assistant.run()
    
    # Si el GUI está activo, ejecutar su loop al final
    if assistant.gui_mode and assistant._tray:
        assistant._tray.run()


if __name__ == "__main__":
    main()
