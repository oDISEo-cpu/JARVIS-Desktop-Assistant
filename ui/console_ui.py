"""
Interfaz de consola con Rich.
Muestra escucha, razonamiento, ejecución y respuestas con colores distintos.
Incluye panel web opcional con FastAPI + WebSocket.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config import WEB_CHAT_HOST, WEB_CHAT_PORT


class ConsoleUI:
    """Interfaz visual en terminal con Rich."""

    def __init__(self) -> None:
        self.console = Console()

    def show_banner(self) -> None:
        """Muestra el banner de inicio de JARVIS."""
        banner = Text()
        banner.append("J.A.R.V.I.S.", style="bold cyan")
        banner.append("\nJust A Rather Very Intelligent System", style="dim italic")
        banner.append("\n\nAsistente Virtual — Control Total de PC", style="green")
        self.console.print(Panel(banner, border_style="cyan", padding=(1, 4)))

    def show_status(self, modules: dict[str, bool]) -> None:
        """Muestra el estado de los módulos cargados."""
        table = Table(title="Estado del Sistema", border_style="blue")
        table.add_column("Módulo", style="cyan")
        table.add_column("Estado", justify="center")

        for name, active in modules.items():
            status = Text("● ONLINE", style="green") if active else Text("○ OFFLINE", style="red")
            table.add_row(name, status)

        self.console.print(table)

    def show_listening(self) -> None:
        """Indica que JARVIS está escuchando."""
        self.console.print("[yellow]🎤 Escuchando...[/yellow]")

    def show_heard(self, text: str) -> None:
        """Muestra lo que se escuchó/transcribió."""
        self.console.print(Panel(text, title="[yellow]Escuchado[/yellow]", border_style="yellow"))

    def show_thinking(self, text: str = "Procesando solicitud...") -> None:
        """Muestra que JARVIS está razonando."""
        self.console.print(f"[magenta]🧠 {text}[/magenta]")

    def show_reasoning(self, reasoning: str) -> None:
        """Muestra el razonamiento interno del LLM."""
        if reasoning:
            self.console.print(Panel(reasoning, title="[magenta]Razonamiento[/magenta]", border_style="magenta"))

    def show_executing(self, tool: str, params: dict[str, Any] | None = None) -> None:
        """Muestra una acción en ejecución."""
        params_str = f" {params}" if params else ""
        self.console.print(f"[blue]⚡ Ejecutando:[/blue] [bold]{tool}[/bold]{params_str}")

    def show_execution_result(self, result: str) -> None:
        """Muestra el resultado de la ejecución."""
        self.console.print(Panel(result, title="[blue]Resultado[/blue]", border_style="blue"))

    def show_response(self, text: str) -> None:
        """Muestra la respuesta final de JARVIS."""
        self.console.print(Panel(text, title="[green]JARVIS[/green]", border_style="green"))

    def show_error(self, error: str) -> None:
        """Muestra un error."""
        self.console.print(Panel(error, title="[red]Error[/red]", border_style="red"))

    def show_info(self, message: str) -> None:
        """Muestra información general."""
        self.console.print(f"[dim]{message}[/dim]")

    def prompt(self, message: str = "Usted: ") -> str:
        """Prompt de entrada de texto."""
        return self.console.input(f"[bold white]{message}[/bold white]")
