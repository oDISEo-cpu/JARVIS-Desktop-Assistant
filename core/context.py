"""
Contexto persistente de JARVIS.
Gestiona preferencias del usuario, proyectos activos y contexto de sesión.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class UserContext:
    """Gestiona el contexto persistente del usuario entre sesiones."""

    def __init__(self, data_dir: Path) -> None:
        self.data_file = data_dir / "user_context.json"
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.context: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        """Carga el contexto desde archivo."""
        if not self.data_file.exists():
            return self._default_context()
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self._default_context()

    def _default_context(self) -> dict[str, Any]:
        """Devuelve estructura por defecto."""
        return {
            "preferences": {
                "editor": "",
                "browser": "",
                "project_dirs": [],
                "favorite_apps": [],
            },
            "active_projects": [],
            "session_notes": [],
            "learned_patterns": [],
            "last_updated": None,
        }

    def save(self) -> None:
        """Guarda el contexto en archivo."""
        self.context["last_updated"] = datetime.now().isoformat()
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.context, f, indent=2, ensure_ascii=False)

    def set_preference(self, key: str, value: Any) -> None:
        """Establece una preferencia del usuario."""
        self.context["preferences"][key] = value
        self.save()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Obtiene una preferencia del usuario."""
        return self.context["preferences"].get(key, default)

    def add_project(self, name: str, path: str, description: str = "") -> None:
        """Añade un proyecto activo."""
        project = {
            "name": name,
            "path": path,
            "description": description,
            "added_at": datetime.now().isoformat(),
        }
        # Evitar duplicados
        existing = [p for p in self.context["active_projects"] if p["name"] == name]
        if not existing:
            self.context["active_projects"].append(project)
            self.save()

    def remove_project(self, name: str) -> bool:
        """Elimina un proyecto por nombre."""
        before = len(self.context["active_projects"])
        self.context["active_projects"] = [
            p for p in self.context["active_projects"] if p["name"] != name
        ]
        if len(self.context["active_projects"]) < before:
            self.save()
            return True
        return False

    def get_projects(self) -> list[dict[str, Any]]:
        """Devuelve lista de proyectos activos."""
        return self.context["active_projects"]

    def add_session_note(self, note: str) -> None:
        """Añade una nota de sesión (máximo 10)."""
        self.context["session_notes"].append({
            "note": note,
            "timestamp": datetime.now().isoformat(),
        })
        # Mantener solo las últimas 10 notas
        self.context["session_notes"] = self.context["session_notes"][-10:]
        self.save()

    def get_session_notes(self) -> list[str]:
        """Devuelve notas de sesión recientes."""
        return [n["note"] for n in self.context["session_notes"]]

    def clear_session_notes(self) -> None:
        """Limpia todas las notas de sesión."""
        self.context["session_notes"] = []
        self.save()

    def learn_pattern(self, pattern: str, trigger: str, action: str) -> None:
        """Aprende un nuevo patrón de comportamiento."""
        self.context["learned_patterns"].append({
            "pattern": pattern,
            "trigger": trigger,
            "action": action,
            "learned_at": datetime.now().isoformat(),
        })
        self.save()

    def get_learned_patterns(self) -> list[dict[str, Any]]:
        """Devuelve patrones aprendidos."""
        return self.context["learned_patterns"]

    def get_summary(self) -> str:
        """Devuelve resumen del contexto actual."""
        prefs = self.context["preferences"]
        projects = self.context["active_projects"]
        notes = self.context["session_notes"]

        lines = ["📋 **Resumen de Contexto:**"]

        if prefs.get("editor"):
            lines.append(f"   • Editor: {prefs['editor']}")
        if prefs.get("browser"):
            lines.append(f"   • Navegador: {prefs['browser']}")
        if projects:
            lines.append(f"   • Proyectos activos: {len(projects)}")
            for p in projects[:3]:
                lines.append(f"     - {p['name']}: {p['path']}")
        if notes:
            lines.append(f"   • Notas recientes: {len(notes)}")

        if len(lines) == 1:
            lines.append("   (Sin contexto guardado)")

        return "\n".join(lines)

    def export_context(self) -> str:
        """Exporta contexto como JSON string."""
        return json.dumps(self.context, indent=2, ensure_ascii=False)

    def import_context(self, json_str: str) -> bool:
        """Importa contexto desde JSON string."""
        try:
            data = json.loads(json_str)
            self.context.update(data)
            self.save()
            return True
        except json.JSONDecodeError:
            return False
