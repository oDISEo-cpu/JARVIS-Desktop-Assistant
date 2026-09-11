"""
Tests seguros de JARVIS.
No tocan el sistema real: dry-run, memoria y whitelist de seguridad.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from action.executor import Executor
from core.memory import Memory
from core.planner import Planner
from security.guard import SecurityGuard


@pytest.fixture
def temp_memory(tmp_path: Path) -> Memory:
    """Memoria aislada en directorio temporal."""
    return Memory(
        storage_path=tmp_path / "memory.json",
        routines_db=tmp_path / "routines.db",
    )


@pytest.fixture
def guard_no_confirm() -> SecurityGuard:
    """Guard que rechaza confirmaciones (simula usuario que dice 'no')."""
    return SecurityGuard(confirm_callback=lambda _msg: False)


@pytest.fixture
def guard_yes_confirm() -> SecurityGuard:
    """Guard que acepta confirmaciones."""
    return SecurityGuard(confirm_callback=lambda _msg: True)


class TestExecutorDryRun:
    """Pruebas de executor en modo dry-run."""

    def test_dry_run_no_ejecuta_comando(self, temp_memory: Memory) -> None:
        executor = Executor(memory=temp_memory, dry_run=True)
        with patch("action.terminal.run_command") as mock_run:
            ok, result = executor.execute_step("run_command", {"cmd": "echo test"})
            assert ok is True
            assert "[DRY-RUN]" in result
            mock_run.assert_not_called()

    def test_dry_run_no_abre_app(self, temp_memory: Memory) -> None:
        executor = Executor(memory=temp_memory, dry_run=True)
        with patch("action.app_control.open_app") as mock_open:
            ok, result = executor.execute_step("open_app", {"name": "notepad"})
            assert ok is True
            assert "open_app" in result
            mock_open.assert_not_called()

    def test_dry_run_plan_completo(self, temp_memory: Memory) -> None:
        executor = Executor(memory=temp_memory, dry_run=True)
        steps = [
            {"tool": "open_app", "params": {"name": "calc"}},
            {"tool": "web_search", "params": {"query": "test"}},
        ]
        with patch("action.app_control.open_app") as mock_open, \
             patch("action.web_ops.web_search") as mock_search:
            result = executor.execute_plan(steps)
            assert "[DRY-RUN]" in result
            mock_open.assert_not_called()
            mock_search.assert_not_called()


class TestMemoryRoutines:
    """Pruebas de memoria y detección de rutinas."""

    def test_registra_acciones(self, temp_memory: Memory) -> None:
        for _ in range(3):
            temp_memory.record_action("open_app", {"name": "notepad"})
        routines = temp_memory.detect_routines()
        assert len(routines) >= 1
        assert routines[0].tool == "open_app"

    def test_format_routines_vacio(self, temp_memory: Memory) -> None:
        result = temp_memory.format_routines_list()
        assert "No he detectado rutinas" in result

    def test_format_routines_con_datos(self, temp_memory: Memory) -> None:
        for _ in range(4):
            temp_memory.record_action("open_app", {"name": "chrome"})
        result = temp_memory.format_routines_list()
        assert "Rutinas detectadas" in result
        assert "chrome" in result.lower() or "Abrir" in result


class TestSecurityGuard:
    """Pruebas de whitelist y comandos destructivos."""

    def test_bloquea_comando_destructivo(self) -> None:
        guard = SecurityGuard()
        allowed, reason = guard.check_shell_command("del /f important.txt")
        assert allowed is False
        assert "destructivo" in reason.lower()

    def test_permite_comando_whitelist(self) -> None:
        guard = SecurityGuard()
        allowed, _ = guard.check_shell_command("echo hola")
        assert allowed is True

    def test_rechaza_comando_no_whitelist(self) -> None:
        guard = SecurityGuard()
        allowed, reason = guard.check_shell_command("curl http://evil.com")
        assert allowed is False
        assert "whitelist" in reason.lower()

    def test_delete_file_requiere_confirmacion(self, guard_no_confirm: SecurityGuard) -> None:
        authorized, msg = guard_no_confirm.authorize_action("delete_file", {"path": "/tmp/test.txt"})
        assert authorized is False
        assert "cancelada" in msg.lower()

    def test_delete_file_con_confirmacion(self, guard_yes_confirm: SecurityGuard) -> None:
        authorized, _ = guard_yes_confirm.authorize_action("delete_file", {"path": "/tmp/test.txt"})
        assert authorized is True

    def test_is_destructive_shutdown(self) -> None:
        guard = SecurityGuard()
        assert guard.is_destructive("shutdown_pc", {}) is True
        assert guard.is_destructive("open_app", {"name": "notepad"}) is False


class TestBasicMode:
    """Pruebas del modo básico sin LLM."""

    def test_abrir_app(self) -> None:
        from core.basic_mode import process_basic_command
        resp = process_basic_command("abre el bloc de notas")
        assert resp is not None
        assert resp.type == "action"
        assert resp.steps[0]["tool"] == "open_app"

    def test_ayuda(self) -> None:
        from core.basic_mode import process_basic_command
        resp = process_basic_command("ayuda")
        assert resp is not None
        assert resp.type == "conversation"
        assert "modo básico" in resp.message.lower()

    def test_comando_desconocido(self) -> None:
        from core.basic_mode import process_basic_command
        resp = process_basic_command("xyzabc123 random")
        assert resp is None
