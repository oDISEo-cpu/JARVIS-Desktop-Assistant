"""
Guardia de seguridad de JARVIS.
Whitelist de comandos, confirmación para acciones destructivas y logging.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from config import ACTION_LOG_FILE, DESTRUCTIVE_KEYWORDS, SHELL_WHITELIST


class SecurityGuard:
    """Controla permisos, confirmaciones y registro de acciones."""

    def __init__(
        self,
        whitelist: list[str] | None = None,
        destructive_keywords: list[str] | None = None,
        log_path: Path | None = None,
        confirm_callback: Callable[[str], bool] | None = None,
    ) -> None:
        self._whitelist = [cmd.lower() for cmd in (whitelist or SHELL_WHITELIST)]
        self._destructive = [kw.lower() for kw in (destructive_keywords or DESTRUCTIVE_KEYWORDS)]
        self._log_path = log_path or ACTION_LOG_FILE
        self._confirm_callback = confirm_callback or self._default_confirm
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configura el logger de acciones."""
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger("jarvis.actions")
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            handler = logging.FileHandler(self._log_path, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
            self._logger.addHandler(handler)

    @staticmethod
    def _default_confirm(message: str) -> bool:
        """Confirmación por consola por defecto."""
        try:
            answer = input(f"\n⚠️  CONFIRMACIÓN REQUERIDA: {message}\n¿Confirmar? (s/n): ").strip().lower()
            return answer in ("s", "si", "sí", "y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    def log_action(self, tool: str, params: dict, result: str, success: bool = True) -> None:
        """
        Registra una acción ejecutada con timestamp.

        Args:
            tool: Nombre de la herramienta.
            params: Parámetros usados.
            result: Resultado de la ejecución.
            success: Si la acción fue exitosa.
        """
        status = "OK" if success else "FAIL"
        self._logger.info(f"[{status}] {tool} | params={params} | result={result[:200]}")

    def is_destructive(self, tool: str, params: dict) -> bool:
        """
        Detecta si una acción es potencialmente destructiva.

        Args:
            tool: Nombre de la herramienta.
            params: Parámetros de la acción.

        Returns:
            True si requiere confirmación explícita.
        """
        destructive_tools = {
            "delete_file", "shutdown_pc", "restart_pc", "kill_process",
        }
        if tool in destructive_tools:
            return True

        # Analizar comandos shell
        if tool == "run_command":
            cmd = str(params.get("cmd", "")).lower()
            return any(kw in cmd for kw in self._destructive)

        return False

    def is_command_whitelisted(self, cmd: str) -> bool:
        """
        Verifica si el comando base está en la whitelist.

        Args:
            cmd: Comando shell completo.

        Returns:
            True si el comando base está permitido.
        """
        base_cmd = cmd.strip().split()[0].lower() if cmd.strip() else ""
        # Eliminar ruta si es absoluta (ej. C:\Windows\System32\cmd.exe)
        base_cmd = Path(base_cmd).name.lower()
        return base_cmd in self._whitelist

    def check_shell_command(self, cmd: str) -> tuple[bool, str]:
        """
        Evalúa un comando shell antes de ejecutarlo.

        Args:
            cmd: Comando a evaluar.

        Returns:
            Tupla (permitido, razón).
        """
        cmd_lower = cmd.lower()

        if any(kw in cmd_lower for kw in self._destructive):
            return False, "Comando destructivo detectado"

        if not self.is_command_whitelisted(cmd):
            return False, f"Comando '{cmd.split()[0]}' no está en la whitelist"

        return True, "Comando permitido"

    def request_confirmation(self, message: str) -> bool:
        """
        Solicita confirmación al usuario para una acción peligrosa.

        Args:
            message: Descripción de la acción.

        Returns:
            True si el usuario confirma.
        """
        confirmed = self._confirm_callback(message)
        self._logger.info(f"CONFIRMATION | msg={message} | confirmed={confirmed}")
        return confirmed

    def authorize_action(self, tool: str, params: dict) -> tuple[bool, str]:
        """
        Autoriza una acción completa antes de ejecutarla.

        Args:
            tool: Nombre de la herramienta.
            params: Parámetros.

        Returns:
            Tupla (autorizado, mensaje).
        """
        if self.is_destructive(tool, params):
            desc = f"Ejecutar '{tool}' con parámetros {params}"
            if not self.request_confirmation(desc):
                return False, "Acción cancelada por el usuario"

        if tool == "run_command":
            cmd = str(params.get("cmd", ""))
            allowed, reason = self.check_shell_command(cmd)
            if not allowed:
                if not self.request_confirmation(f"Comando no permitido: {cmd}. ¿Ejecutar de todos modos?"):
                    return False, f"Comando rechazado: {reason}"

        return True, "Autorizado"
