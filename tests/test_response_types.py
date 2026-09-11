"""
Tests de regresión: tipos de respuesta y comando repetir.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.brain import Brain, ensure_message_str, is_repeat_request
from core.models import BrainResponse
from core.memory import Memory
from main import JarvisAssistant


class TestEnsureMessageStr:
    """Normalización de message a str legible."""

    def test_dict_tool_se_convierte_en_resumen(self) -> None:
        msg = {"tool": "open_app", "params": {"name": "chrome"}}
        result = ensure_message_str(msg)
        assert isinstance(result, str)
        assert "chrome" in result.lower()
        assert "{" not in result

    def test_list_no_crash(self) -> None:
        steps = [{"tool": "web_search", "params": {"query": "hora"}, "description": "Buscar la hora"}]
        result = ensure_message_str([{"tool": "web_search"}], steps)
        assert isinstance(result, str)
        assert "hora" in result.lower() or "buscar" in result.lower()

    def test_str_passthrough(self) -> None:
        assert ensure_message_str("Hola, señor.") == "Hola, señor."


class TestRepeatRequest:
    """Detección de intención de repetición."""

    @pytest.mark.parametrize("phrase", ["vuelvelo a hacer", "repítelo", "otra vez", "hazlo de nuevo"])
    def test_detecta_repeticion(self, phrase: str) -> None:
        assert is_repeat_request(phrase) is True

    def test_no_detecta_frase_normal(self) -> None:
        assert is_repeat_request("abre chrome") is False


class TestProcessInputMessageTypes:
    """_process_input no crashea con message=dict."""

    def test_message_dict_no_crash(self, tmp_path) -> None:
        assistant = JarvisAssistant(dry_run=True)
        assistant.memory = Memory(
            storage_path=tmp_path / "mem.json",
            routines_db=tmp_path / "routines.db",
        )
        assistant.brain = Brain(memory=assistant.memory, force_basic_mode=True)

        dict_message = {"tool": "open_app", "params": {"name": "chrome"}}
        fake_response = BrainResponse(
            type="action",
            message=dict_message,  # type: ignore[arg-type]
            steps=[{"tool": "open_app", "params": {"name": "chrome"}, "description": "Abrir Chrome"}],
        )

        with patch.object(assistant.brain, "process", return_value=fake_response):
            # No debe lanzar AttributeError en .split()
            result = assistant._process_input("abre chrome")
        assert result is True

    def test_message_dict_produce_texto_legible(self, tmp_path) -> None:
        assistant = JarvisAssistant(dry_run=True)
        assistant.memory = Memory(
            storage_path=tmp_path / "mem.json",
            routines_db=tmp_path / "routines.db",
        )

        msg_dict = {"tool": "web_search", "params": {"query": "clima"}}
        steps = [{"tool": "web_search", "params": {"query": "clima"}, "description": "Buscar el clima"}]
        fake_response = BrainResponse(
            type="action",
            message=msg_dict,  # type: ignore[arg-type]
            steps=steps,
        )

        with patch.object(assistant.brain, "process", return_value=fake_response):
            assistant._process_input("busca el clima")

        # El mensaje principal de JARVIS (sin detalle técnico de ejecución) debe ser legible
        last_jarvis = [t for t in assistant.chat._history if t[0] == "jarvis"][-1][1]
        assert isinstance(last_jarvis, str)
        main_part = last_jarvis.split("\n\n")[0]
        assert "{" not in main_part
        assert "clima" in main_part.lower()


class TestRepeatLastPlan:
    """Comando 'vuelvelo a hacer' con y sin last_plan."""

    def test_repetir_con_last_plan_dry_run(self, tmp_path) -> None:
        memory = Memory(
            storage_path=tmp_path / "mem.json",
            routines_db=tmp_path / "routines.db",
        )
        plan_steps = [
            {"tool": "open_app", "params": {"name": "notepad"}, "description": "Abrir notepad"},
            {"tool": "web_search", "params": {"query": "hora"}, "description": "Buscar la hora"},
        ]
        memory.set_last_plan(plan_steps, "Plan de prueba")

        assistant = JarvisAssistant(dry_run=True)
        assistant.memory = memory
        assistant.brain = Brain(memory=memory, force_basic_mode=True)
        from action.executor import Executor
        assistant.executor = Executor(memory=memory, dry_run=True)

        result = assistant._process_input("vuelvelo a hacer")

        assert result is True
        last_jarvis = [t for t in assistant.chat._history if t[0] == "jarvis"][-1][1]
        assert "[DRY-RUN]" in last_jarvis
        assert "notepad" in last_jarvis.lower() or "open_app" in last_jarvis

    def test_repetir_sin_historial(self, tmp_path) -> None:
        memory = Memory(
            storage_path=tmp_path / "mem.json",
            routines_db=tmp_path / "routines.db",
        )
        brain = Brain(memory=memory, force_basic_mode=True)
        response = brain.process("vuelvelo a hacer")

        assert response.type == "conversation"
        assert isinstance(response.message, str)
        assert "ninguna acción previa" in response.message.lower()
        assert "{" not in response.message
