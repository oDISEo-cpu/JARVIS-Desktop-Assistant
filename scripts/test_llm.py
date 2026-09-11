"""
Script de prueba de conexión LLM para JARVIS.
Verifica que Ollama (u otro proveedor configurado) responde correctamente.
Imprime la respuesta o el error exacto.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Asegurar que el directorio jarvis esté en el path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import LLM_PROVIDER, LLM_TIMEOUT, get_llm_model, OLLAMA_BASE_URL  # noqa: E402
from core.brain import (  # noqa: E402
    Brain,
    create_llm_provider,
    format_llm_error,
    log_llm_error,
    run_llm_diagnostics,
)

def main() -> int:
    """Prueba la conexión con el LLM configurado."""
    model = get_llm_model()
    print("=" * 60)
    print("JARVIS — Test de conexión LLM")
    print("=" * 60)
    print(f"Proveedor : {LLM_PROVIDER}")
    print(f"Modelo    : {model}")
    print(f"Timeout   : {LLM_TIMEOUT}s")
    if LLM_PROVIDER == "ollama":
        print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print("-" * 60)

    print("\n[1/3] Diagnóstico completo (servidor + modelo + chat real)...")
    report = run_llm_diagnostics()
    for line in report.lines:
        print(f"  {line}")
    if not report.ok:
        print(f"\n✗ Diagnóstico fallido: {report.error or 'desconocido'}")
        print(f"  Detalle en: {ROOT / 'logs' / 'llm.log'}")
        return 1

    print("\n[2/3] Cliente LLM directo...")
    try:
        provider = create_llm_provider(model=report.model)
        print(f"  Cliente OK — modelo activo: {report.model}")
    except Exception as exc:
        summary = log_llm_error("test_llm_init", exc, report.model)
        print(f"  ERROR al inicializar: {summary}")
        traceback.print_exc()
        return 1

    test_message = "Hola, ¿quién eres?"
    messages = [
        {"role": "system", "content": "Responde en español de forma breve y amable."},
        {"role": "user", "content": test_message},
    ]

    print(f'\n[3/3] Enviando: "{test_message}"')
    print("-" * 60)

    try:
        raw = provider._call_complete(messages)
        print("Respuesta cruda del LLM:")
        print(raw)
        print("-" * 60)

        brain = Brain()
        if brain.is_basic_mode:
            print(f"\n⚠️  Brain en modo básico: {brain.last_llm_error}")
            return 1

        response = brain.process(test_message)
        print(f"\nRespuesta vía Brain ({response.type}):")
        print(response.message)
        if response.reasoning:
            print(f"\nRazonamiento: {response.reasoning}")
        if response.basic_mode:
            print(f"\n⚠️  Brain cayó a modo básico: {brain.last_llm_error}")
            return 1

        print("\n✓ Conexión LLM OK")
        return 0

    except Exception as exc:
        summary = format_llm_error(exc, report.model)
        log_llm_error("test_llm", exc, report.model)
        print(f"\nERROR en la prueba: {summary}")
        traceback.print_exc()
        print(f"\nTraceback completo en: {ROOT / 'logs' / 'llm.log'}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
