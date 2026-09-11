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


class WebUI:
    """
    Panel web opcional con FastAPI y WebSocket.
    Permite interactuar con JARVIS desde el navegador.
    """

    def __init__(self, host: str = WEB_CHAT_HOST, port: int = WEB_CHAT_PORT) -> None:
        self._host = host
        self._port = port
        self._clients: list[Any] = []
        self._message_queue: asyncio.Queue[str] = asyncio.Queue()
        self._running = False

    def start_background(self) -> threading.Thread | None:
        """Inicia el servidor web en un hilo de fondo."""
        try:
            thread = threading.Thread(target=self._run_server, daemon=True)
            thread.start()
            return thread
        except Exception as exc:
            print(f"[WebUI] No se pudo iniciar: {exc}")
            return None

    def _run_server(self) -> None:
        """Ejecuta uvicorn en el hilo."""
        try:
            import uvicorn
            from fastapi import FastAPI, WebSocket, WebSocketDisconnect
            from fastapi.responses import HTMLResponse

            app = FastAPI(title="JARVIS Web UI")
            ui_instance = self

            @app.get("/")
            async def index() -> HTMLResponse:
                return HTMLResponse("""
                <!DOCTYPE html>
                <html><head><title>JARVIS</title>
                <style>
                  body { background:#0a0a0f; color:#00d4ff; font-family:monospace;
                         display:flex; flex-direction:column; align-items:center;
                         min-height:100vh; margin:0; padding:20px; }
                  h1 { letter-spacing:4px; }
                  #log { width:80%; max-width:800px; height:400px; overflow-y:auto;
                         border:1px solid #00d4ff; padding:10px; margin:10px 0; }
                  input { width:80%; max-width:800px; padding:10px; background:#111;
                          color:#00d4ff; border:1px solid #00d4ff; font-size:16px; }
                  .user { color:#ffd700; } .jarvis { color:#00ff88; }
                </style></head><body>
                <h1>J.A.R.V.I.S.</h1>
                <div id="log"></div>
                <input id="input" placeholder="Escriba su comando..." autofocus>
                <script>
                  const ws = new WebSocket(`ws://${location.host}/ws`);
                  const log = document.getElementById('log');
                  const input = document.getElementById('input');
                  ws.onmessage = e => {
                    const d = JSON.parse(e.data);
                    log.innerHTML += `<div class="${d.role}"><b>${d.role}:</b> ${d.text}</div>`;
                    log.scrollTop = log.scrollHeight;
                  };
                  input.onkeydown = e => {
                    if(e.key==='Enter' && input.value.trim()){
                      ws.send(JSON.stringify({text:input.value.trim()}));
                      log.innerHTML += `<div class="user"><b>user:</b> ${input.value}</div>`;
                      input.value='';
                      log.scrollTop = log.scrollHeight;
                    }
                  };
                </script></body></html>
                """)

            @app.websocket("/ws")
            async def websocket_endpoint(websocket: WebSocket) -> None:
                await websocket.accept()
                ui_instance._clients.append(websocket)
                try:
                    while True:
                        data = await websocket.receive_json()
                        await ui_instance._message_queue.put(data.get("text", ""))
                except WebSocketDisconnect:
                    ui_instance._clients.remove(websocket)

            uvicorn.run(app, host=self._host, port=self._port, log_level="warning")
        except ImportError:
            print("[WebUI] FastAPI/uvicorn no instalados. Web UI desactivada.")

    async def broadcast(self, role: str, text: str) -> None:
        """Envía un mensaje a todos los clientes WebSocket."""
        import json

        message = json.dumps({"role": role, "text": text})
        for client in self._clients[:]:
            try:
                await client.send_text(message)
            except Exception:
                self._clients.remove(client)

    def broadcast_sync(self, role: str, text: str) -> None:
        """Versión síncrona de broadcast para uso desde el hilo principal."""
        if not self._clients:
            return
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.broadcast(role, text))
            else:
                loop.run_until_complete(self.broadcast(role, text))
        except RuntimeError:
            pass
