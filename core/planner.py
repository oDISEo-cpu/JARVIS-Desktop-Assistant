"""
Planificador de JARVIS.
Valida y estructura los planes de acción generados por el cerebro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Registro de herramientas disponibles y sus parámetros requeridos
AVAILABLE_TOOLS: dict[str, list[str]] = {
    # Control de aplicaciones
    "open_app": ["name"],
    "close_app": ["name"],
    "list_windows": [],
    "focus_window": ["title"],
    "minimize_window": ["title"],
    "maximize_window": ["title"],
    # Terminal
    "run_command": ["cmd"],
    # Archivos
    "search_file": ["query"],
    "create_folder": ["path"],
    "move_file": ["src", "dst"],
    "copy_file": ["src", "dst"],
    "delete_file": ["path"],
    # Web
    "open_url": ["url"],
    "web_search": ["query"],
    # Sistema
    "set_volume": ["level"],
    "get_volume": [],
    "set_brightness": ["level"],
    "suspend_pc": [],
    "shutdown_pc": [],
    "restart_pc": [],
    "lock_screen": [],
    # Automatización
    "click": ["x", "y"],
    "type_text": ["text"],
    "screenshot": [],
    "clipboard_read": [],
    "clipboard_write": ["text"],
    # Notificaciones
    "notify": ["title", "message"],
    # Memoria
    "remember": ["fact"],
}


@dataclass
class PlanStep:
    """Un paso individual del plan de ejecución."""

    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class Plan:
    """Plan completo con uno o más pasos."""

    steps: list[PlanStep] = field(default_factory=list)
    reasoning: str = ""
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)


class Planner:
    """Valida planes y herramientas antes de la ejecución."""

    def __init__(self, tools: dict[str, list[str]] | None = None) -> None:
        self._tools = tools or AVAILABLE_TOOLS

    @property
    def tool_names(self) -> list[str]:
        """Lista de nombres de herramientas disponibles."""
        return list(self._tools.keys())

    def tool_exists(self, tool_name: str) -> bool:
        """Comprueba si una herramienta está registrada."""
        return tool_name in self._tools

    def validate_step(self, tool: str, params: dict[str, Any]) -> list[str]:
        """
        Valida un paso individual del plan.

        Args:
            tool: Nombre de la herramienta.
            params: Parámetros proporcionados.

        Returns:
            Lista de errores de validación (vacía si es válido).
        """
        errors: list[str] = []
        if tool not in self._tools:
            errors.append(f"Herramienta desconocida: '{tool}'")
            return errors

        required = self._tools[tool]
        for param in required:
            if param not in params or params[param] in (None, ""):
                errors.append(f"Parámetro requerido '{param}' faltante en '{tool}'")
        return errors

    def build_plan(
        self,
        steps_data: list[dict[str, Any]],
        reasoning: str = "",
    ) -> Plan:
        """
        Construye y valida un plan a partir de datos JSON del LLM.

        Args:
            steps_data: Lista de dicts con 'tool' y 'params'.
            reasoning: Razonamiento del LLM sobre el plan.

        Returns:
            Plan validado con posibles errores.
        """
        plan = Plan(reasoning=reasoning)
        all_errors: list[str] = []

        for i, step_data in enumerate(steps_data):
            tool = step_data.get("tool", "")
            params = step_data.get("params", {}) or {}
            description = step_data.get("description", "")

            errors = self.validate_step(tool, params)
            if errors:
                all_errors.extend([f"Paso {i + 1}: {e}" for e in errors])
            else:
                plan.steps.append(PlanStep(tool=tool, params=params, description=description))

        plan.validation_errors = all_errors
        plan.is_valid = len(all_errors) == 0 and len(plan.steps) > 0
        return plan

    def build_single_action(self, tool: str, params: dict[str, Any]) -> Plan:
        """
        Construye un plan de un solo paso.

        Args:
            tool: Nombre de la herramienta.
            params: Parámetros de la herramienta.

        Returns:
            Plan con un único paso validado.
        """
        return self.build_plan([{"tool": tool, "params": params}])

    def get_tools_description(self) -> str:
        """
        Genera descripción de herramientas para el prompt del LLM.

        Returns:
            Texto formateado con todas las herramientas y parámetros.
        """
        lines = []
        for tool, params in self._tools.items():
            param_str = ", ".join(params) if params else "sin parámetros"
            lines.append(f"- {tool}({param_str})")
        return "\n".join(lines)
