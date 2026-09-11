"""
Chat web local de JARVIS.
FastAPI + WebSocket (/ws) + fallback HTTP (/api/chat, /api/health).
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from typing import Any, Callable

from config import LLM_PROVIDER, WEB_CHAT_HOST, WEB_CHAT_PORT, USUARIO_TRATO

try:
    from fastapi import WebSocket
    from pydantic import BaseModel

    class ChatRequestModel(BaseModel):
        """Cuerpo JSON de POST /api/chat."""

        message: str
except ImportError:
    WebSocket = None  # type: ignore[misc, assignment]
    ChatRequestModel = None  # type: ignore[misc, assignment]

# Tipo: recibe mensaje del usuario → devuelve {"reply": str, "actions": list, "exit": bool?}
MessageHandler = Callable[[str], dict[str, Any]]

HTML_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>J.A.R.V.I.S.</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0a0e14; color: #c5d4e3; font-family: 'Segoe UI', system-ui, sans-serif;
    display: flex; flex-direction: column; height: 100vh;
  }
  header {
    background: linear-gradient(135deg, #0d1b2a, #1b2838);
    border-bottom: 1px solid #00b4d8; padding: 16px 24px;
    display: flex; align-items: center; gap: 12px;
  }
  header h1 { color: #00b4d8; font-size: 1.4rem; letter-spacing: 3px; font-weight: 300; }
  header span { color: #5a6a7a; font-size: 0.85rem; }
  #chat {
    flex: 1; overflow-y: auto; padding: 20px 24px;
    display: flex; flex-direction: column; gap: 12px;
  }
  .msg { max-width: 75%; padding: 10px 14px; border-radius: 12px; line-height: 1.5; font-size: 0.95rem; white-space: pre-wrap; }
  .msg.user { align-self: flex-end; background: #1a3a5c; border: 1px solid #2a5a8c; color: #ffd700; }
  .msg.jarvis { align-self: flex-start; background: #0f2b1f; border: 1px solid #1a5c3a; color: #80ffb0; }
  .msg.system { align-self: center; background: #1a1a2e; border: 1px solid #333; color: #888; font-size: 0.85rem; }
  .msg .role { font-size: 0.75rem; opacity: 0.7; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 1px; }
  footer {
    border-top: 1px solid #1a2a3a; padding: 16px 24px;
    display: flex; gap: 10px; background: #0d1117;
  }
  #input {
    flex: 1; background: #161b22; border: 1px solid #30363d; color: #c5d4e3;
    padding: 12px 16px; border-radius: 8px; font-size: 1rem; outline: none;
  }
  #input:focus { border-color: #00b4d8; }
  button {
    background: #00b4d8; color: #0a0e14; border: none; padding: 12px 24px;
    border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.95rem;
  }
  button:hover { background: #0096b4; }
  button:disabled { opacity: 0.5; cursor: wait; }
  #status { font-size: 0.8rem; color: #5a6a7a; padding: 4px 24px 8px; }
  .connected { color: #80ffb0; }
  .disconnected { color: #ff6b6b; }
  .http-mode { color: #ffd700; }
</style>
</head>
<body>
<header>
  <h1>J.A.R.V.I.S.</h1>
  <span>Just A Rather Very Intelligent System</span>
</header>
<div id="status"><span id="conn" class="disconnected">● Conectando...</span></div>
<div id="chat"></div>
<footer>
  <input id="input" placeholder="Escriba su mensaje, señor..." autofocus autocomplete="off">
  <button id="sendBtn" onclick="sendMsg()">Enviar</button>
</footer>
<script>
  const chat = document.getElementById('chat');
  const input = document.getElementById('input');
  const sendBtn = document.getElementById('sendBtn');
  const conn = document.getElementById('conn');

  let ws = null;
  let mode = 'none';       // 'ws' | 'http' | 'none'
  let wsRetryTimer = null;
  let sending = false;

  function setStatus(text, cls) {
    conn.textContent = text;
    conn.className = cls;
  }

  function appendMsg(role, text) {
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    const safe = String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g, '<br>');
    div.innerHTML = '<div class="role">' + role + '</div>' + safe;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  async function checkHealth() {
    try {
      const r = await fetch('/api/health');
      if (r.ok) return await r.json();
    } catch (e) {}
    return null;
  }

  function connectWebSocket() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = proto + '//' + location.host + '/ws';
    try {
      ws = new WebSocket(url);
    } catch (e) {
      enableHttpMode();
      return;
    }
    ws.onopen = () => {
      mode = 'ws';
      setStatus('● Conectado (WebSocket)', 'connected');
      if (wsRetryTimer) { clearInterval(wsRetryTimer); wsRetryTimer = null; }
    };
    ws.onclose = () => {
      ws = null;
      if (mode === 'ws') enableHttpMode();
      scheduleWsRetry();
    };
    ws.onerror = () => {
      ws = null;
      enableHttpMode();
    };
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        appendMsg(d.role || 'jarvis', d.text || d.reply || '');
      } catch (err) {
        appendMsg('system', 'Error al interpretar respuesta del servidor.');
      }
    };
  }

  async function enableHttpMode() {
    const health = await checkHealth();
    if (health && health.status === 'ok') {
      mode = 'http';
      setStatus('● Conectado (HTTP)', 'http-mode');
    } else {
      mode = 'none';
      setStatus('● Sin conexión — reintentando...', 'disconnected');
    }
  }

  function scheduleWsRetry() {
    if (wsRetryTimer) return;
    wsRetryTimer = setInterval(() => {
      if (mode !== 'ws') connectWebSocket();
    }, 5000);
  }

  async function sendViaHttp(text) {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text}),
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.json();
  }

  function sendViaWs(text) {
    ws.send(JSON.stringify({text: text}));
  }

  async function sendMsg() {
    const text = input.value.trim();
    if (!text || sending) return;

    appendMsg('user', text);
    input.value = '';
    sending = true;
    sendBtn.disabled = true;

    try {
      if (mode === 'ws' && ws && ws.readyState === WebSocket.OPEN) {
        sendViaWs(text);
        // La respuesta llegará por onmessage
      } else {
        // Fallback HTTP — el input nunca queda bloqueado por falta de WS
        if (mode === 'none') await enableHttpMode();
        const data = await sendViaHttp(text);
        appendMsg('jarvis', data.reply || 'Sin respuesta.');
        if (data.actions && data.actions.length) {
          appendMsg('system', 'Acciones: ' + data.actions.map(a => a.tool || a).join(', '));
        }
      }
    } catch (err) {
      appendMsg('system', 'Me temo que hubo un error, señor: ' + err.message);
      await enableHttpMode();
    } finally {
      sending = false;
      sendBtn.disabled = false;
      input.focus();
    }
  }

  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMsg(); });

  // Inicio: comprobar health, intentar WS, activar fallback HTTP si falla
  (async () => {
    await enableHttpMode();
    connectWebSocket();
    scheduleWsRetry();
    appendMsg('system', 'Sistemas en línea. ¿En qué puedo ayudarle, señor?');
  })();
</script>
</body>
</html>"""


async def _run_ws_session(websocket: Any, handler: MessageHandler | None) -> None:
    """
    Maneja una sesión WebSocket completa.
    Separado de create_fastapi_app para evitar problemas de closure con TestClient.
    """
    from fastapi import WebSocketDisconnect

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            text = str(data.get("text", "")).strip()
            if not text:
                continue
            if handler is None:
                await websocket.send_json({"role": "system", "text": "Servidor no configurado."})
                continue
            try:
                result = await asyncio.to_thread(handler, text)
                await websocket.send_json({
                    "role": "jarvis",
                    "text": result.get("reply", ""),
                    "actions": result.get("actions", []),
                })
                if result.get("exit"):
                    await websocket.send_json({"role": "system", "text": "Sesión finalizada."})
                    break
            except Exception as exc:
                await websocket.send_json({
                    "role": "system",
                    "text": f"Me temo que ocurrió un error, {USUARIO_TRATO}: {exc}",
                })
    except WebSocketDisconnect:
        pass


def create_fastapi_app(message_handler: MessageHandler | None = None) -> Any:
    """
    Crea la aplicación FastAPI con rutas HTTP y WebSocket.

    Args:
        message_handler: Callback síncrono que procesa mensajes del usuario.

    Returns:
        Instancia FastAPI configurada.
    """
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="JARVIS Web Chat")
    handler = message_handler

    @app.get("/")
    async def index() -> HTMLResponse:
        return HTMLResponse(HTML_PAGE)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "llm": LLM_PROVIDER}

    @app.post("/api/chat")
    async def chat_http(req: ChatRequestModel) -> dict[str, Any]:
        text = req.message.strip()
        if not text:
            return {"reply": "Mensaje vacío.", "actions": []}
        if handler is None:
            return {"reply": "Servidor no configurado.", "actions": []}
        try:
            result = await asyncio.to_thread(handler, text)
            return {
                "reply": result.get("reply", ""),
                "actions": result.get("actions", []),
                "exit": result.get("exit", False),
            }
        except Exception as exc:
            return {
                "reply": f"Me temo que ocurrió un error, {USUARIO_TRATO}: {exc}",
                "actions": [],
            }

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await _run_ws_session(websocket, handler)

    return app


class WebChat:
    """
    Servidor de chat web.
    En modo --web corre uvicorn como proceso principal (no en hilo daemon).
    """

    def __init__(
        self,
        host: str = WEB_CHAT_HOST,
        port: int = WEB_CHAT_PORT,
        message_handler: MessageHandler | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._message_handler = message_handler
        self._incoming: deque[str] = deque()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._app: Any = None

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Registra el callback que procesa mensajes del chat."""
        self._message_handler = handler
        if self._app is not None:
            # Recrear app con handler actualizado (tests)
            self._app = create_fastapi_app(handler)

    def get_app(self) -> Any:
        """Devuelve la app FastAPI (para TestClient y uvicorn)."""
        if self._app is None:
            self._app = create_fastapi_app(self._message_handler)
        return self._app

    def run_blocking(self) -> None:
        """Ejecuta uvicorn en el hilo principal (modo --web)."""
        try:
            import uvicorn

            self._running = True
            app = self.get_app()
            # ws='websockets' requiere el paquete websockets instalado
            uvicorn.run(
                app,
                host=self._host,
                port=self._port,
                log_level="info",
                ws="auto",
            )
        except ImportError as exc:
            print(f"[WebChat] Dependencias faltantes: {exc}")
            print("[WebChat] Ejecute: pip install fastapi uvicorn[standard] websockets")

    def start_background(self) -> threading.Thread | None:
        """Inicia servidor en hilo daemon (compatibilidad con modo terminal+web)."""
        try:
            self._thread = threading.Thread(target=self.run_blocking, daemon=True)
            self._thread.start()
            self._running = True
            return self._thread
        except Exception as exc:
            print(f"[WebChat] No se pudo iniciar: {exc}")
            return None

    def poll_message(self) -> str | None:
        with self._lock:
            return self._incoming.popleft() if self._incoming else None

    def wait_for_message(self, timeout: float = 0.5) -> str | None:
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = self.poll_message()
            if msg:
                return msg
            time.sleep(0.05)
        return None

    def broadcast(self, role: str, text: str) -> None:
        """Compatibilidad: en modo handler directo las respuestas van por WS/HTTP."""
        pass
