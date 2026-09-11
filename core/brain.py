"""
Motor de IA de JARVIS.
Capa de abstracción para OpenAI, Anthropic y Ollama.
Decide entre conversación casual y ejecución de acciones.
Degrada a modo básico si el LLM no está disponible.
"""

from __future__ import annotations

import json
import re
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests

from config import (
    ANTHROPIC_API_KEY,
    LLM_PROVIDER,
    LLM_TIMEOUT,
    LOGS_DIR,
    OLLAMA_API_KEY,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
    USUARIO_TRATO,
    get_llm_model,
)
from core.memory import Memory
from core.models import BrainResponse, ResponseType
from core.personality import build_system_prompt
from core.planner import Planner

LLM_LOG_FILE = LOGS_DIR / "llm.log"

# Patrones de intención de repetición (sin pasar por el LLM)
_REPEAT_PATTERNS: tuple[str, ...] = (
    r"vuelvelo a hacer",
    r"vuélvelo a hacer",
    r"vuelve a hacerlo",
    r"repítelo",
    r"repetelo",
    r"repetir",
    r"otra vez",
    r"hazlo de nuevo",
    r"hazlo otra vez",
)


@dataclass
class LLMDiagnosticReport:
    """Resultado de diagnóstico del LLM (arranque o /diag)."""

    provider: str
    model: str
    server_ok: bool = False
    model_installed: bool = False
    chat_ok: bool = False
    lines: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.server_ok and self.model_installed and self.chat_ok


def format_llm_error(exc: Exception, model: str | None = None) -> str:
    """
    Resume un error del LLM en una línea legible para el panel Sistema.

    Args:
        exc: Excepción capturada.
        model: Modelo configurado (para mensajes de modelo no encontrado).

    Returns:
        Texto corto, p. ej. "model 'llama3.1:8b' not found" o "timeout tras 120s".
    """
    msg = str(exc).strip()
    lower = msg.lower()
    model_label = model or get_llm_model()

    if isinstance(exc, requests.Timeout):
        return f"timeout tras {LLM_TIMEOUT}s"

    if "timed out" in lower or "timeout" in lower:
        return f"timeout tras {LLM_TIMEOUT}s"

    if "not found" in lower or "does not exist" in lower:
        if model_label in msg:
            return f"model '{model_label}' not found"
        return f"model '{model_label}' not found: {msg[:120]}"

    if "invalid message content type" in lower or "map[string]interface" in lower:
        return "historial de chat corrupto (contenido no textual en memoria)"

    if "connection refused" in lower or "failed to establish" in lower:
        return f"servidor LLM inaccesible: {msg[:120]}"

    if "api_key" in lower or "unauthorized" in lower or "401" in msg:
        return f"credenciales inválidas: {msg[:120]}"

    if hasattr(exc, "status_code"):
        code = getattr(exc, "status_code", "")
        body = getattr(exc, "body", None) or getattr(exc, "message", "")
        if body:
            return f"HTTP {code}: {body}"[:200]
        return f"HTTP {code}: {msg[:120]}"

    if msg:
        return msg[:200]
    return type(exc).__name__


def log_llm_error(context: str, exc: Exception, model: str | None = None) -> str:
    """
    Registra el traceback completo en logs/llm.log y devuelve un resumen corto.

    Args:
        context: Etiqueta del punto de fallo (p. ej. 'process', 'startup').
        exc: Excepción capturada.
        model: Modelo activo al momento del error.

    Returns:
        Resumen formateado para mostrar al usuario.
    """
    summary = format_llm_error(exc, model)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with LLM_LOG_FILE.open("a", encoding="utf-8") as log_file:
            log_file.write(f"\n{'=' * 60}\n")
            log_file.write(f"{datetime.now(timezone.utc).isoformat()} [{context}] {summary}\n")
            log_file.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except OSError:
        pass
    return summary


def sanitize_messages_for_llm(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Garantiza que todo content enviado al LLM sea str.
    Evita 400 cuando la memoria guardó dicts (p. ej. JSON de herramientas).
    """
    clean: list[dict[str, str]] = []
    for msg in messages:
        role = str(msg.get("role", "user"))
        content = msg.get("content", "")
        if isinstance(content, (dict, list)):
            content = json.dumps(content, ensure_ascii=False)
        elif content is None:
            content = ""
        else:
            content = str(content)
        clean.append({"role": role, "content": content})
    return clean


def fetch_ollama_models(base_url: str = OLLAMA_BASE_URL) -> list[dict[str, Any]]:
    """Consulta GET /api/tags y devuelve la lista de modelos instalados."""
    url = f"{base_url.rstrip('/')}/api/tags"
    response = requests.get(url, timeout=min(30, LLM_TIMEOUT))
    response.raise_for_status()
    return response.json().get("models", [])


def _normalize_ollama_base(name: str) -> str:
    """Nombre base sin tag (:latest, :8b, etc.)."""
    return name.split(":")[0]


def _match_ollama_model(configured: str, models: list[dict[str, Any]]) -> str | None:
    """Busca el modelo configurado entre los instalados en Ollama."""
    names = [m.get("name", "") for m in models if m.get("name")]
    if configured in names:
        return configured
    prefix_matches = [
        n for n in names
        if n.startswith(f"{configured}:") or _normalize_ollama_base(n) == configured
    ]
    if prefix_matches:
        for preferred in (f"{configured}:latest", configured):
            if preferred in prefix_matches:
                return preferred
        return sorted(prefix_matches)[0]
    return None


def pick_largest_ollama_model(models: list[dict[str, Any]]) -> str | None:
    """Elige el modelo con mayor tamaño en disco (heurística 'el mayor disponible')."""
    if not models:
        return None
    best = max(models, key=lambda m: int(m.get("size") or 0))
    return str(best.get("name", "")) or None


def resolve_ollama_model(
    configured: str,
    base_url: str = OLLAMA_BASE_URL,
) -> tuple[str, str | None]:
    """
    Resuelve el modelo Ollama a usar.

    Returns:
        Tupla (modelo_a_usar, aviso_opcional_para_el_usuario).
    """
    try:
        models = fetch_ollama_models(base_url)
    except Exception as exc:
        raise ConnectionError(f"No se pudo consultar Ollama en {base_url}: {exc}") from exc

    if not models:
        raise ValueError("Ollama responde pero no hay modelos instalados (ollama pull ...)")

    matched = _match_ollama_model(configured, models)
    if matched:
        return matched, None

    fallback = pick_largest_ollama_model(models)
    if not fallback:
        raise ValueError(f"Modelo '{configured}' no encontrado y no hay alternativa")

    notice = (
        f"Modelo configurado '{configured}' no encontrado; "
        f"usando {fallback}, {USUARIO_TRATO}."
    )
    return fallback, notice


def run_llm_diagnostics(
    provider_name: str | None = None,
    model: str | None = None,
) -> LLMDiagnosticReport:
    """
    Ejecuta chequeos completos: servidor, modelo instalado y chat real (1 token).

    Usado en arranque y en el comando /diag.
    """
    name = (provider_name or LLM_PROVIDER).lower()
    active_model = model or get_llm_model()
    report = LLMDiagnosticReport(provider=name, model=active_model)
    report.lines.append(f"Proveedor: {name}")
    report.lines.append(f"Modelo configurado: {active_model}")
    report.lines.append(f"Timeout: {LLM_TIMEOUT}s")

    if name == "openai" and not OPENAI_API_KEY:
        report.error = "OPENAI_API_KEY no configurada"
        report.lines.append(f"✗ {report.error}")
        return report
    if name == "anthropic" and not ANTHROPIC_API_KEY:
        report.error = "ANTHROPIC_API_KEY no configurada"
        report.lines.append(f"✗ {report.error}")
        return report

    if name == "ollama":
        try:
            models = fetch_ollama_models()
            report.server_ok = True
            report.lines.append(f"✓ Servidor Ollama OK ({len(models)} modelo(s))")
            resolved, notice = resolve_ollama_model(active_model)
            active_model = resolved
            report.model = resolved
            report.model_installed = True
            report.lines.append(f"✓ Modelo disponible: {resolved}")
            if notice:
                report.lines.append(f"⚠ {notice}")
        except Exception as exc:
            summary = format_llm_error(exc, active_model)
            report.error = summary
            report.lines.append(f"✗ Servidor/modelo: {summary}")
            return report
    else:
        report.server_ok = True
        report.model_installed = True
        report.lines.append("✓ Credenciales presentes")

    try:
        provider = create_llm_provider(name, model=active_model)
        ok, chat_msg = provider.test_connection()
        if ok:
            report.chat_ok = True
            report.lines.append(f"✓ Chat de prueba OK ({chat_msg})")
        else:
            report.error = chat_msg
            report.lines.append(f"✗ Chat de prueba: {chat_msg}")
    except Exception as exc:
        summary = log_llm_error("diagnostics", exc, active_model)
        report.error = summary
        report.lines.append(f"✗ Chat de prueba: {summary}")

    return report


def _tool_summary(tool: str, params: dict[str, Any]) -> str:
    """Resume una herramienta en lenguaje natural."""
    summaries: dict[str, Any] = {
        "open_app": lambda p: f"abrí {p.get('name', 'la aplicación')}",
        "close_app": lambda p: f"cerré {p.get('name', 'la aplicación')}",
        "web_search": lambda p: f"busqué '{p.get('query', '')}' en Google",
        "open_url": lambda p: f"abrí {p.get('url', 'la página')}",
        "search_file": lambda p: f"busqué el archivo '{p.get('query', '')}'",
        "create_folder": lambda p: f"creé la carpeta {p.get('path', '')}",
        "run_command": lambda _p: "ejecuté el comando solicitado",
        "list_windows": lambda _p: "listé las ventanas abiertas",
        "set_volume": lambda p: f"ajusté el volumen al {p.get('level', '')}%",
        "lock_screen": lambda _p: "bloqueé la pantalla",
        "notify": lambda p: f"envié la notificación '{p.get('title', '')}'",
    }
    fn = summaries.get(tool)
    if fn:
        return fn(params)
    return f" ejecuté {tool}"


def summarize_steps(steps: list[dict[str, Any]] | None) -> str:
    """
    Genera un resumen natural de los pasos de un plan.

    Args:
        steps: Lista de pasos con tool/params/description.

    Returns:
        Frase legible para mostrar al usuario.
    """
    if not steps:
        return f"Listo, {USUARIO_TRATO}."
    parts: list[str] = []
    for step in steps:
        desc = step.get("description")
        if desc:
            parts.append(desc[0].lower() + desc[1:] if desc else desc)
        else:
            parts.append(_tool_summary(step.get("tool", ""), step.get("params") or {}))
    if len(parts) == 1:
        body = parts[0]
    else:
        body = ", ".join(parts[:-1]) + f" y {parts[-1]}"
    return f"Hecho, {USUARIO_TRATO}: {body}."


def ensure_message_str(message: Any, steps: list[dict[str, Any]] | None = None) -> str:
    """
    Garantiza que el mensaje de respuesta sea siempre un str legible.

    Si el LLM devolvió un dict/list (p. ej. JSON de tool), genera un resumen natural.
    Nunca expone JSON crudo al usuario.
    """
    if isinstance(message, str):
        text = message.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, (dict, list)):
                    return ensure_message_str(parsed, steps)
            except json.JSONDecodeError:
                pass
        return text or "Entendido."

    if isinstance(message, dict):
        if "tool" in message:
            tool_steps = steps or [message]
            return summarize_steps(tool_steps)
        if steps:
            return summarize_steps(steps)
        return f"Entendido, {USUARIO_TRATO}."

    if isinstance(message, list):
        if steps:
            return summarize_steps(steps)
        if message and isinstance(message[0], dict) and "tool" in message[0]:
            return summarize_steps(message)  # type: ignore[arg-type]
        return f"Entendido, {USUARIO_TRATO}."

    if message is None:
        return summarize_steps(steps) if steps else "Entendido."

    return str(message)


def is_repeat_request(text: str) -> bool:
    """Detecta si el usuario pide repetir la última acción."""
    lower = text.lower().strip()
    return any(re.search(pattern, lower) for pattern in _REPEAT_PATTERNS)


class LLMProviderBase(ABC):
    """Interfaz abstracta para proveedores de LLM."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model or get_llm_model()

    @abstractmethod
    def complete(self, messages: list[dict[str, str]], *, max_tokens: int | None = None) -> str:
        """Envía mensajes al LLM y devuelve la respuesta en texto."""
        ...

    def _call_complete(self, messages: list[dict[str, Any]], *, max_tokens: int | None = None) -> str:
        """Wrapper con saneamiento y registro de errores."""
        clean = sanitize_messages_for_llm(messages)
        try:
            return self.complete(clean, max_tokens=max_tokens)
        except Exception as exc:
            log_llm_error("complete", exc, self._model)
            raise

    def test_connection(self) -> tuple[bool, str]:
        """
        Prueba real: chat mínimo con max_tokens=1 al modelo configurado.

        Returns:
            Tupla (disponible, mensaje).
        """
        try:
            result = self._call_complete(
                [
                    {"role": "system", "content": "Responde solo: OK"},
                    {"role": "user", "content": "test"},
                ],
                max_tokens=1,
            )
            if result and result.strip():
                return True, f"modelo {self._model} respondió"
            return False, "Respuesta vacía del LLM"
        except Exception as exc:
            return False, format_llm_error(exc, self._model)


class OpenAIProvider(LLMProviderBase):
    """Proveedor OpenAI (también compatible con Ollama vía base_url)."""

    def __init__(
        self,
        api_key: str = OPENAI_API_KEY,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(model=model)
        self._api_key = api_key
        self._base_url = base_url

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int | None = None) -> str:
        if not self._api_key and not self._base_url:
            raise ValueError("OPENAI_API_KEY no configurada.")

        from openai import OpenAI

        kwargs: dict[str, Any] = {
            "api_key": self._api_key or "not-needed",
            "timeout": LLM_TIMEOUT,
        }
        if self._base_url:
            kwargs["base_url"] = self._base_url

        client = OpenAI(**kwargs)
        create_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,  # type: ignore[arg-type]
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens

        response = client.chat.completions.create(**create_kwargs)
        return response.choices[0].message.content or "{}"


class AnthropicProvider(LLMProviderBase):
    """Proveedor Anthropic Claude."""

    def __init__(self, api_key: str = ANTHROPIC_API_KEY, model: str | None = None) -> None:
        super().__init__(model=model)
        self._api_key = api_key

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int | None = None) -> str:
        if not self._api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada.")

        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key, timeout=LLM_TIMEOUT)
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m for m in messages if m["role"] != "system"]

        response = client.messages.create(
            model=self._model,
            max_tokens=max_tokens or 2048,
            system=system_msg + "\nResponde SOLO con JSON válido, sin markdown.",
            messages=user_msgs,  # type: ignore[arg-type]
            temperature=0.3,
        )
        return response.content[0].text  # type: ignore[union-attr]


class OllamaProvider(OpenAIProvider):
    """
    Ollama vía cliente OpenAI apuntando a localhost:11434/v1.
    Fallback a API nativa de Ollama si el cliente OpenAI falla.
    """

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str | None = None) -> None:
        super().__init__(
            api_key=OLLAMA_API_KEY,
            model=model,
            base_url=f"{base_url.rstrip('/')}/v1",
        )
        self._native_url = base_url.rstrip("/")

    def complete(self, messages: list[dict[str, str]], *, max_tokens: int | None = None) -> str:
        try:
            return super().complete(messages, max_tokens=max_tokens)
        except Exception as openai_exc:
            log_llm_error("ollama_openai_compat", openai_exc, self._model)
            try:
                return self._complete_native(messages, max_tokens=max_tokens)
            except Exception as native_exc:
                log_llm_error("ollama_native", native_exc, self._model)
                raise native_exc from openai_exc

    def _complete_native(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
    ) -> str:
        """Fallback: API REST nativa de Ollama."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "format": "json",
        }
        if max_tokens is not None:
            payload["options"] = {"num_predict": max_tokens}

        response = requests.post(
            f"{self._native_url}/api/chat",
            json=payload,
            timeout=LLM_TIMEOUT,
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "{}")


def create_llm_provider(
    provider_name: str | None = None,
    model: str | None = None,
) -> LLMProviderBase:
    """Factory para crear el proveedor LLM según configuración."""
    name = (provider_name or LLM_PROVIDER).lower()
    providers: dict[str, type[LLMProviderBase]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
    }
    if name not in providers:
        raise ValueError(f"Proveedor LLM desconocido: {name}. Usa: {list(providers.keys())}")
    return providers[name](model=model)


class Brain:
    """Cerebro de JARVIS: procesa entradas y decide respuesta o plan de acción."""

    def __init__(
        self,
        memory: Memory | None = None,
        planner: Planner | None = None,
        llm: LLMProviderBase | None = None,
        force_basic_mode: bool = False,
    ) -> None:
        self._memory = memory or Memory()
        self._planner = planner or Planner()
        self._llm: LLMProviderBase | None = None
        self._llm_available = False
        self._basic_mode = force_basic_mode
        self._llm_error = ""
        self._last_llm_error = ""
        self._model = get_llm_model()
        self._model_notice: str | None = None
        self._diag_report: LLMDiagnosticReport | None = None

        if not force_basic_mode:
            if not self._credentials_ok():
                self._basic_mode = True
                self._llm_error = "Credenciales LLM no configuradas"
            else:
                self._initialize_llm(llm)

        self._system_prompt = self._build_system_prompt()

    def _initialize_llm(self, llm: LLMProviderBase | None) -> None:
        """Resuelve modelo, crea proveedor y ejecuta chequeo real de arranque."""
        try:
            if LLM_PROVIDER == "ollama":
                resolved, notice = resolve_ollama_model(self._model)
                self._model = resolved
                if notice:
                    self._model_notice = notice

            self._llm = llm or create_llm_provider(model=self._model)
            self._diag_report = run_llm_diagnostics(model=self._model)

            if self._diag_report.ok:
                self._llm_available = True
                self._basic_mode = False
                self._llm_error = ""
            else:
                self._basic_mode = True
                self._llm_available = False
                self._llm_error = self._diag_report.error or "LLM no disponible en arranque"
        except Exception as exc:
            self._basic_mode = True
            self._llm_error = log_llm_error("startup", exc, self._model)
            self._llm_available = False

    @staticmethod
    def _credentials_ok() -> bool:
        """Verifica que existan credenciales mínimas sin llamar al API."""
        if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
            return False
        if LLM_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
            return False
        return True

    def _build_system_prompt(self) -> str:
        return build_system_prompt(
            tools_description=self._planner.get_tools_description(),
            memory_context=self._memory.get_context_summary() or "Sin recuerdos previos.",
        )

    @property
    def is_basic_mode(self) -> bool:
        return self._basic_mode

    @property
    def active_model(self) -> str:
        return self._model

    @property
    def model_notice(self) -> str | None:
        return self._model_notice

    @property
    def last_llm_error(self) -> str:
        return self._last_llm_error or self._llm_error

    @property
    def llm_status(self) -> tuple[bool, str]:
        if self._basic_mode:
            detail = self._llm_error or "Modo básico activo"
            return False, detail
        model_info = f" ({self._model})" if self._model else ""
        return True, f"LLM operativo{model_info}"

    def run_diagnostics(self) -> LLMDiagnosticReport:
        """Re-ejecuta chequeos completos (comando /diag)."""
        report = run_llm_diagnostics(model=self._model)
        self._diag_report = report
        if report.ok:
            self._basic_mode = False
            self._llm_available = True
            self._llm_error = ""
        else:
            self._basic_mode = True
            self._llm_available = False
            self._llm_error = report.error or "Diagnóstico fallido"
        return report

    def _parse_llm_response(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"type": "conversation", "message": raw, "steps": None}

    def process(self, user_message: str) -> BrainResponse:
        """Procesa un mensaje del usuario."""
        from core.basic_mode import process_basic_command

        cmd = user_message.strip().lower()

        # Comando especial: rutinas
        if cmd in ("rutinas", "/rutinas"):
            return BrainResponse(
                type="conversation",
                message=self._memory.format_routines_list(),
                reasoning="Listado de rutinas",
            )

        # Repetir último plan (determinista, sin LLM)
        if is_repeat_request(user_message):
            last = self._memory.get_last_plan()
            if not last:
                return BrainResponse(
                    type="conversation",
                    message=f"No tengo ninguna acción previa que repetir, {USUARIO_TRATO}.",
                    reasoning="Repetición solicitada sin last_plan",
                )
            steps = last["steps"]
            self._memory.add_message("user", user_message)
            msg = f"Enseguida, {USUARIO_TRATO}. Repito la acción anterior."
            self._memory.add_message("assistant", msg)
            return BrainResponse(
                type="action",
                message=msg,
                steps=steps,
                reasoning=last.get("reasoning", "Repetición de último plan"),
            )

        remember_match = re.match(r"(?:recuerda\s+que|recuerda)\s+(.+)", user_message.strip(), re.IGNORECASE)
        if remember_match:
            fact = remember_match.group(1).strip()
            self._memory.remember(fact)
            return BrainResponse(
                type="remember",
                message=f"Queda registrado, {USUARIO_TRATO}. He memorizado: {fact}",
                remember_fact=fact,
            )

        # Modo básico
        if self._basic_mode:
            basic = process_basic_command(user_message)
            if basic:
                basic.basic_mode = True
                basic.message = ensure_message_str(basic.message, basic.steps)
                self._memory.add_message("user", user_message)
                self._memory.add_message("assistant", basic.message)
                return basic
            return BrainResponse(
                type="conversation",
                message=(
                    f"No he reconocido ese comando en modo básico, {USUARIO_TRATO}. "
                    f"Error LLM: {self._llm_error or 'desconocido'}. "
                    "Escriba 'ayuda' o '/diag' para más información."
                ),
                basic_mode=True,
            )

        self._memory.add_message("user", user_message)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
            *self._memory.get_conversation_context(),
        ]

        try:
            assert self._llm is not None
            raw_response = self._llm._call_complete(messages)
        except Exception as exc:
            summary = log_llm_error("process", exc, self._model)
            self._basic_mode = True
            self._llm_error = summary
            self._last_llm_error = summary
            basic = process_basic_command(user_message)
            if basic:
                basic.basic_mode = True
                basic.message = ensure_message_str(basic.message, basic.steps)
                return basic
            error_msg = f"Error LLM: {summary}"
            self._memory.add_message("assistant", error_msg)
            return BrainResponse(type="conversation", message=error_msg, basic_mode=True)

        parsed = self._parse_llm_response(raw_response)
        response_type: ResponseType = parsed.get("type", "conversation")
        message = parsed.get("message", "Entendido.")
        reasoning = parsed.get("reasoning", "")
        steps = parsed.get("steps")
        remember_fact = parsed.get("remember_fact")

        if response_type == "remember" and remember_fact:
            self._memory.remember(remember_fact)
            message = message or f"He memorizado: {remember_fact}"

        if response_type == "action" and steps:
            plan = self._planner.build_plan(steps, reasoning)
            if not plan.is_valid:
                error_detail = "; ".join(plan.validation_errors)
                message = f"No pude planificar la acción: {error_detail}"
                response_type = "conversation"
                steps = None
            else:
                steps = [{"tool": s.tool, "params": s.params, "description": s.description} for s in plan.steps]

        message = ensure_message_str(message, steps if isinstance(steps, list) else None)

        self._memory.add_message("assistant", message)
        return BrainResponse(
            type=response_type,
            message=message,
            steps=steps,
            reasoning=reasoning,
            remember_fact=remember_fact,
            raw_json=raw_response,
        )

    @property
    def memory(self) -> Memory:
        return self._memory

    @property
    def planner(self) -> Planner:
        return self._planner
