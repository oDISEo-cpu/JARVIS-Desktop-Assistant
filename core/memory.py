"""
Memoria conversacional, persistente y de rutinas de JARVIS.
Historial en JSON; registro de acciones y patrones en SQLite.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import (
    MAX_CONVERSATION_HISTORY,
    MEMORY_FILE,
    ROUTINE_HOUR_TOLERANCE,
    ROUTINE_MIN_OCCURRENCES,
    ROUTINES_DB,
)


@dataclass
class RoutinePattern:
    """Patrón de rutina detectado automáticamente."""

    tool: str
    params: dict[str, Any]
    weekday: int  # 0=lunes … 6=domingo
    hour: int
    count: int
    description: str

    def weekday_name(self) -> str:
        names = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        return names[self.weekday]


class Memory:
    """Gestiona memoria de conversación, preferencias y rutinas."""

    def __init__(
        self,
        storage_path: Path | None = None,
        routines_db: Path | None = None,
        max_history: int = MAX_CONVERSATION_HISTORY,
    ) -> None:
        self._path = storage_path or MEMORY_FILE
        self._routines_db = routines_db or ROUTINES_DB
        self._max_history = max_history
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {
            "conversation": [],
            "long_term": [],
            "preferences": {},
            "frequent_actions": {},
            "last_plan": None,
        }
        self._load()
        self._init_routines_db()

    def _init_routines_db(self) -> None:
        """Crea la tabla de acciones para detección de rutinas."""
        self._routines_db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._routines_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    weekday INTEGER NOT NULL,
                    hour INTEGER NOT NULL,
                    minute INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data.update(loaded)
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[Memory] Error al cargar memoria: {exc}")

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            print(f"[Memory] Error al guardar memoria: {exc}")

    def add_message(self, role: str, content: str) -> None:
        with self._lock:
            self._data["conversation"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            if len(self._data["conversation"]) > self._max_history * 2:
                self._data["conversation"] = self._data["conversation"][-self._max_history * 2:]
            self._save()

    def get_conversation_context(self) -> list[dict[str, str]]:
        with self._lock:
            return [{"role": m["role"], "content": m["content"]} for m in self._data["conversation"]]

    def remember(self, fact: str, category: str = "general") -> None:
        with self._lock:
            self._data["long_term"].append({
                "fact": fact,
                "category": category,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self._save()

    def search_memories(self, query: str) -> list[str]:
        query_lower = query.lower()
        with self._lock:
            return [
                e["fact"] for e in self._data["long_term"]
                if any(w in e["fact"].lower() for w in query_lower.split())
            ]

    def get_all_memories(self) -> list[str]:
        with self._lock:
            return [e["fact"] for e in self._data["long_term"]]

    def set_preference(self, key: str, value: Any) -> None:
        with self._lock:
            self._data["preferences"][key] = value
            self._save()

    def get_preference(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data["preferences"].get(key, default)

    def record_action(self, tool: str, params: dict[str, Any] | None = None) -> None:
        """
        Registra una acción ejecutada con día y hora para detección de rutinas.

        Args:
            tool: Nombre de la herramienta.
            params: Parámetros usados (opcional).
        """
        params = params or {}
        now = datetime.now()
        with self._lock:
            counts = self._data["frequent_actions"]
            key = f"{tool}:{json.dumps(params, sort_keys=True)}"
            counts[key] = counts.get(key, 0) + 1
            self._save()

        try:
            with sqlite3.connect(self._routines_db) as conn:
                conn.execute(
                    "INSERT INTO action_log (tool, params_json, weekday, hour, minute, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (tool, json.dumps(params, ensure_ascii=False), now.weekday(), now.hour, now.minute, now.isoformat()),
                )
                conn.commit()
        except sqlite3.Error as exc:
            print(f"[Memory] Error al registrar rutina: {exc}")

    def detect_routines(self) -> list[RoutinePattern]:
        """
        Detecta patrones: misma acción 3+ veces en horarios similares.

        Returns:
            Lista de rutinas detectadas ordenadas por frecuencia.
        """
        try:
            with sqlite3.connect(self._routines_db) as conn:
                rows = conn.execute(
                    "SELECT tool, params_json, weekday, hour FROM action_log ORDER BY timestamp"
                ).fetchall()
        except sqlite3.Error:
            return []

        # Agrupar por tool+params+weekday+hour_bucket
        groups: dict[tuple, list[int]] = defaultdict(list)
        for tool, params_json, weekday, hour in rows:
            key = (tool, params_json, weekday, hour)
            groups[key].append(hour)

        patterns: list[RoutinePattern] = []
        seen: set[tuple] = set()

        for (tool, params_json, weekday, hour), _hours in groups.items():
            if (tool, params_json, weekday) in seen:
                continue
            # Contar ocurrencias en ventana horaria ±tolerance
            count = sum(
                1 for t, pj, wd, h in rows
                if t == tool and pj == params_json and wd == weekday
                and abs(h - hour) <= ROUTINE_HOUR_TOLERANCE
            )
            if count >= ROUTINE_MIN_OCCURRENCES:
                params = json.loads(params_json)
                desc = self._describe_action(tool, params)
                patterns.append(RoutinePattern(tool=tool, params=params, weekday=weekday, hour=hour, count=count, description=desc))
                seen.add((tool, params_json, weekday))

        patterns.sort(key=lambda p: p.count, reverse=True)
        return patterns

    @staticmethod
    def _describe_action(tool: str, params: dict[str, Any]) -> str:
        """Genera descripción legible de una acción."""
        if tool == "open_app":
            return f"Abrir {params.get('name', 'aplicación')}"
        if tool == "web_search":
            return f"Buscar '{params.get('query', '')}' en Google"
        if tool == "search_file":
            return f"Buscar archivo '{params.get('query', '')}'"
        if tool == "open_url":
            return f"Abrir {params.get('url', 'URL')}"
        return f"{tool}({params})"

    def get_startup_suggestion(self) -> str | None:
        """
        Sugiere proactivamente una rutina si coincide la hora actual.

        Returns:
            Mensaje de sugerencia o None.
        """
        now = datetime.now()
        for routine in self.detect_routines():
            if routine.weekday == now.weekday() and abs(routine.hour - now.hour) <= ROUTINE_HOUR_TOLERANCE:
                return (
                    f"Son las {now.strftime('%H:%M')}. "
                    f"¿Desea que {routine.description.lower()}? "
                    f"(Rutina detectada {routine.count} veces los {routine.weekday_name()}s)"
                )
        return None

    def format_routines_list(self) -> str:
        """Formatea la lista de rutinas para el comando /rutinas."""
        routines = self.detect_routines()
        if not routines:
            return "No he detectado rutinas recurrentes aún. Siga usándome y aprenderé sus hábitos."

        lines = ["Rutinas detectadas:"]
        for i, r in enumerate(routines, 1):
            lines.append(
                f"  {i}. {r.description} — los {r.weekday_name()}s ~{r.hour:02d}:00 "
                f"({r.count} veces)"
            )
        return "\n".join(lines)

    def get_context_summary(self) -> str:
        parts: list[str] = []
        memories = self.get_all_memories()
        if memories:
            parts.append("Recuerdos del usuario:\n- " + "\n- ".join(memories[-10:]))
        prefs = self._data.get("preferences", {})
        if prefs:
            parts.append("Preferencias:\n- " + "\n- ".join(f"{k}: {v}" for k, v in prefs.items()))
        routines = self.detect_routines()[:3]
        if routines:
            rlines = [f"{r.description} (los {r.weekday_name()}s ~{r.hour:02d}:00)" for r in routines]
            parts.append("Rutinas habituales:\n- " + "\n- ".join(rlines))
        return "\n\n".join(parts)

    def clear_conversation(self) -> None:
        with self._lock:
            self._data["conversation"] = []
            self._save()

    def set_last_plan(self, steps: list[dict[str, Any]], reasoning: str = "") -> None:
        """
        Guarda el último plan de acción ejecutado con éxito.

        Args:
            steps: Pasos del plan (tool + params).
            reasoning: Razonamiento opcional asociado al plan.
        """
        with self._lock:
            self._data["last_plan"] = {
                "steps": steps,
                "reasoning": reasoning,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._save()

    def get_last_plan(self) -> dict[str, Any] | None:
        """
        Recupera el último plan ejecutado con éxito.

        Returns:
            Dict con 'steps' y 'reasoning', o None si no hay plan previo.
        """
        with self._lock:
            plan = self._data.get("last_plan")
            if isinstance(plan, dict) and plan.get("steps"):
                return plan
            return None

    def has_last_plan(self) -> bool:
        """Indica si existe un plan previo repetible."""
        return self.get_last_plan() is not None
