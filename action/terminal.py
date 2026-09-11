"""
Ejecución segura de comandos de terminal.
Captura stdout/stderr y devuelve el resultado.
"""

from __future__ import annotations

import subprocess
from typing import Any


def run_command(cmd: str, timeout: int = 30, cwd: str | None = None) -> str:
    """
    Ejecuta un comando shell y captura la salida.

    Args:
        cmd: Comando a ejecutar.
        timeout: Tiempo máximo de espera en segundos.
        cwd: Directorio de trabajo opcional.

    Returns:
        Salida del comando o mensaje de error.
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            encoding="utf-8",
            errors="replace",
        )
        output_parts: list[str] = []
        if result.stdout.strip():
            output_parts.append(result.stdout.strip())
        if result.stderr.strip():
            output_parts.append(f"[stderr] {result.stderr.strip()}")

        if result.returncode != 0 and not output_parts:
            return f"Comando falló con código {result.returncode}"

        output = "\n".join(output_parts) if output_parts else "(sin salida)"
        # Truncar salidas muy largas
        if len(output) > 4000:
            output = output[:4000] + "\n... (salida truncada)"
        return output
    except subprocess.TimeoutExpired:
        return f"Comando excedió el tiempo límite de {timeout}s"
    except Exception as exc:
        return f"Error al ejecutar comando: {exc}"
