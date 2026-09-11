"""
Tests del chat web: health, HTTP chat y handshake WebSocket.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from ui.web_chat import WebChat, create_fastapi_app


@pytest.fixture
def mock_handler():
    """Handler simulado en modo básico."""
    def handler(message: str) -> dict:
        lower = message.lower()
        if lower in ("salir", "hasta luego"):
            return {"reply": "Hasta luego, señor.", "actions": [], "exit": True}
        if "abre" in lower:
            return {
                "reply": "Enseguida, señor. Abriré la aplicación.",
                "actions": [{"tool": "open_app", "params": {"name": "notepad"}}],
                "exit": False,
            }
        return {"reply": f"Recibido: {message}", "actions": [], "exit": False}
    return handler


@pytest.fixture
def client(mock_handler):
    app = create_fastapi_app(mock_handler)
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_ok(self, client: TestClient) -> None:
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "llm" in data


class TestChatHttpEndpoint:
    def test_chat_respuesta_basica(self, client: TestClient) -> None:
        r = client.post("/api/chat", json={"message": "hola"})
        assert r.status_code == 200
        data = r.json()
        assert "reply" in data
        assert isinstance(data["reply"], str)
        assert "Recibido: hola" in data["reply"]

    def test_chat_con_acciones(self, client: TestClient) -> None:
        r = client.post("/api/chat", json={"message": "abre notepad"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["actions"]) == 1
        assert data["actions"][0]["tool"] == "open_app"

    def test_chat_mensaje_vacio(self, client: TestClient) -> None:
        r = client.post("/api/chat", json={"message": "   "})
        assert r.status_code == 200
        assert "vacío" in r.json()["reply"].lower()

    def test_chat_error_handler(self) -> None:
        def bad_handler(_msg: str) -> dict:
            raise RuntimeError("Ollama caído")

        app = create_fastapi_app(bad_handler)
        c = TestClient(app)
        r = c.post("/api/chat", json={"message": "test"})
        assert r.status_code == 200
        assert "error" in r.json()["reply"].lower() or "tem" in r.json()["reply"].lower()


class TestWebSocketEndpoint:
    def test_ws_handshake_y_respuesta(self, client: TestClient) -> None:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"text": "hola"})
            data = ws.receive_json()
            assert data["role"] == "jarvis"
            assert isinstance(data["text"], str)
            assert "Recibido: hola" in data["text"]

    def test_ws_no_crash_con_error(self) -> None:
        def bad_handler(_msg: str) -> dict:
            raise ValueError("brain lento")

        app = create_fastapi_app(bad_handler)
        c = TestClient(app)
        with c.websocket_connect("/ws") as ws:
            ws.send_json({"text": "falla"})
            data = ws.receive_json()
            assert data["role"] == "system"
            assert "error" in data["text"].lower() or "tem" in data["text"].lower()
            # Conexión sigue viva
            ws.send_json({"text": "otro"})
            data2 = ws.receive_json()
            assert "role" in data2


class TestWebChatClass:
    def test_get_app_con_handler(self, mock_handler) -> None:
        chat = WebChat(message_handler=mock_handler)
        app = chat.get_app()
        c = TestClient(app)
        r = c.get("/api/health")
        assert r.status_code == 200

    def test_index_html(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert "J.A.R.V.I.S." in r.text
        assert "/ws" in r.text
        assert "/api/chat" in r.text
