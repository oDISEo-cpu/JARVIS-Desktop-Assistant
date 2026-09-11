"""
Entrada por texto/consola con interfaz de chat estilo Rich.
Modo principal de comunicación sin dependencias de voz.
"""

from __future__ import annotations

from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text


class TextReader:
    """Lee entrada de texto desde la consola (modo simple)."""

    def __init__(self, prompt: str = "Usted: ", console: Console | None = None) -> None:
        self._prompt = prompt
        self._console = console or Console()

    def read(self, prompt: str | None = None) -> str | None:
        try:
            return Prompt.ask(f"[bold white]{prompt or self._prompt}[/bold white]", console=self._console).strip()
        except (EOFError, KeyboardInterrupt):
            return None


class ChatReader:
    """
    Interfaz de chat interactiva en terminal con Rich.
    Muestra historial de mensajes del usuario y JARVIS en paneles estilizados.
    """

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()
        self._history: list[tuple[str, str]] = []  # (role, text)

    def add_user_message(self, text: str) -> None:
        """Registra y muestra un mensaje del usuario."""
        self._history.append(("user", text))
        self._console.print(
            Panel(text, title="[bold yellow]Usted[/bold yellow]", border_style="yellow", padding=(0, 1))
        )

    def add_jarvis_message(self, text: str, subtitle: str = "JARVIS") -> None:
        """Registra y muestra una respuesta de JARVIS."""
        self._history.append(("jarvis", text))
        self._console.print(
            Panel(text, title=f"[bold green]{subtitle}[/bold green]", border_style="green", padding=(0, 1))
        )

    def add_system_message(self, text: str) -> None:
        """Muestra un mensaje del sistema (info, degradación, etc.)."""
        self._history.append(("system", text))
        self._console.print(
            Panel(text, title="[dim]Sistema[/dim]", border_style="dim", padding=(0, 1))
        )

    def add_thinking(self) -> None:
        """Indica que JARVIS está procesando."""
        self._console.print("[magenta]🧠 Procesando solicitud...[/magenta]")

    def read(self, prompt: str = "Escriba su mensaje") -> str | None:
        """
        Lee entrada del usuario con prompt estilizado.

        Args:
            prompt: Texto del prompt.

        Returns:
            Texto ingresado o None.
        """
        try:
            self._console.print()
            text = Prompt.ask(f"[bold cyan]{prompt}[/bold cyan]", console=self._console).strip()
            if text:
                self.add_user_message(text)
            return text or None
        except (EOFError, KeyboardInterrupt):
            return None

    def read_with_callback(self, on_input: Callable[[str], None]) -> str | None:
        text = self.read()
        if text:
            on_input(text)
        return text

    def show_help_hint(self) -> None:
        """Muestra atajos disponibles."""
        hint = Text()
        hint.append("Comandos: ", style="dim")
        hint.append("/rutinas", style="cyan")
        hint.append(" · ", style="dim")
        hint.append("ayuda", style="cyan")
        hint.append(" · ", style="dim")
        hint.append("salir", style="cyan")
        self._console.print(hint)
