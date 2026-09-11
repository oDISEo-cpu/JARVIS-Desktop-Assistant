"""
Orquestador de acciones de JARVIS.
Recibe un plan y ejecuta cada paso usando los módulos de action/.
"""

from __future__ import annotations

from typing import Any, Callable

from action import app_control, automation, file_ops, notifications, system_control, terminal, web_ops
from core.memory import Memory
from core.planner import Plan, PlanStep, Planner
from security.guard import SecurityGuard


# Mapa de herramientas → funciones ejecutoras
TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    # Apps
    "open_app": app_control.open_app,
    "close_app": app_control.close_app,
    "list_windows": lambda **_: app_control.list_windows(),
    "focus_window": app_control.focus_window,
    "minimize_window": app_control.minimize_window,
    "maximize_window": app_control.maximize_window,
    # Terminal
    "run_command": terminal.run_command,
    # Archivos
    "search_file": file_ops.search_file,
    "create_folder": file_ops.create_folder,
    "move_file": file_ops.move_file,
    "copy_file": file_ops.copy_file,
    "delete_file": file_ops.delete_file,
    # Web
    "open_url": web_ops.open_url,
    "web_search": web_ops.web_search,
    # Sistema
    "set_volume": system_control.set_volume,
    "get_volume": lambda **_: system_control.get_volume(),
    "set_brightness": system_control.set_brightness,
    "suspend_pc": lambda **_: system_control.suspend_pc(),
    "shutdown_pc": lambda **_: system_control.shutdown_pc(),
    "restart_pc": lambda **_: system_control.restart_pc(),
    "lock_screen": lambda **_: system_control.lock_screen(),
    # Automatización
    "click": automation.click,
    "type_text": automation.type_text,
    "screenshot": lambda **_: automation.screenshot(),
    "clipboard_read": lambda **_: automation.clipboard_read(),
    "clipboard_write": automation.clipboard_write,
    # Notificaciones
    "notify": notifications.notify,
}


class Executor:
    """Ejecuta planes de acción paso a paso con control de seguridad."""

    def __init__(
        self,
        guard: SecurityGuard | None = None,
        planner: Planner | None = None,
        memory: Memory | None = None,
        tool_registry: dict[str, Callable[..., str]] | None = None,
        dry_run: bool = False,
    ) -> None:
        self._guard = guard or SecurityGuard()
        self._planner = planner or Planner()
        self._memory = memory
        self._tools = tool_registry or TOOL_REGISTRY
        self._dry_run = dry_run

    def execute_step(self, tool: str, params: dict[str, Any]) -> tuple[bool, str]:
        """
        Ejecuta un único paso del plan.

        Args:
            tool: Nombre de la herramienta.
            params: Parámetros de la herramienta.

        Returns:
            Tupla (éxito, resultado).
        """
        # Manejo especial de 'remember' vía memoria
        if tool == "remember" and self._memory:
            fact = params.get("fact", "")
            self._memory.remember(fact)
            result = f"Memorizado: {fact}"
            self._guard.log_action(tool, params, result, success=True)
            return True, result

        if tool not in self._tools:
            return False, f"Herramienta '{tool}' no implementada"

        # Modo dry-run: simular sin ejecutar ni pedir confirmación
        if self._dry_run:
            result = f"[DRY-RUN] {tool}({params})"
            self._guard.log_action(tool, params, result, success=True)
            return True, result

        # Autorización de seguridad
        authorized, auth_msg = self._guard.authorize_action(tool, params)
        if not authorized:
            self._guard.log_action(tool, params, auth_msg, success=False)
            return False, auth_msg

        try:
            func = self._tools[tool]
            result = func(**params)
            success = not result.lower().startswith("error")
            self._guard.log_action(tool, params, result, success=success)
            if self._memory:
                self._memory.record_action(tool, params)
            return success, result
        except TypeError as exc:
            msg = f"Parámetros incorrectos para '{tool}': {exc}"
            self._guard.log_action(tool, params, msg, success=False)
            return False, msg
        except Exception as exc:
            msg = f"Error ejecutando '{tool}': {exc}"
            self._guard.log_action(tool, params, msg, success=False)
            return False, msg

    def execute_plan(self, steps: list[dict[str, Any]], reasoning: str = "") -> str:
        """
        Ejecuta un plan completo de múltiples pasos.

        Args:
            steps: Lista de pasos con 'tool' y 'params'.
            reasoning: Razonamiento del plan (informativo).

        Returns:
            Resumen de resultados de todos los pasos.
        """
        plan = self._planner.build_plan(steps, reasoning)
        if not plan.is_valid:
            return "Plan inválido: " + "; ".join(plan.validation_errors)

        results: list[str] = []
        for i, step in enumerate(plan.steps, 1):
            desc = f" ({step.description})" if step.description else ""
            success, result = self.execute_step(step.tool, step.params)
            status = "✓" if success else "✗"
            results.append(f"{status} Paso {i}: {step.tool}{desc}\n  → {result}")

        return "\n".join(results)

    def execute_single(self, tool: str, params: dict[str, Any]) -> str:
        """
        Ejecuta una acción individual.

        Args:
            tool: Nombre de la herramienta.
            params: Parámetros.

        Returns:
            Resultado de la ejecución.
        """
        _success, result = self.execute_step(tool, params)
        return result
