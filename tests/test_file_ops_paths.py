"""
Tests de resolución de rutas en file_ops.
Verifica carpetas especiales de Windows vía SHGetKnownFolderPath.
"""

from __future__ import annotations

import platform
from pathlib import Path

import pytest

from action.file_ops import expand_path, resolve_special_folder


@pytest.mark.skipif(platform.system() != "Windows", reason="Carpetas conocidas solo en Windows")
class TestWindowsSpecialFolders:
    """Pruebas de resolución de Escritorio, Documentos y Descargas."""

    @pytest.mark.parametrize(
        "alias",
        ["Escritorio", "escritorio", "Desktop", "desktop"],
    )
    def test_escritorio_existe(self, alias: str) -> None:
        resolved = resolve_special_folder(alias)
        assert resolved is not None, f"No se pudo resolver '{alias}'"
        assert resolved.is_dir(), f"La ruta no es un directorio: {resolved}"
        assert resolved.exists(), f"La ruta no existe: {resolved}"
        assert resolved.is_absolute()

    @pytest.mark.parametrize("alias", ["Documentos", "documentos", "Documents", "documents"])
    def test_documentos_existe(self, alias: str) -> None:
        resolved = resolve_special_folder(alias)
        assert resolved is not None
        assert resolved.is_dir()
        assert resolved.exists()

    @pytest.mark.parametrize("alias", ["Descargas", "descargas", "Downloads", "downloads"])
    def test_descargas_existe(self, alias: str) -> None:
        resolved = resolve_special_folder(alias)
        assert resolved is not None
        assert resolved.is_dir()
        assert resolved.exists()

    @pytest.mark.parametrize(
        ("input_path", "expected_leaf"),
        [
            ("Escritorio", "Desktop"),
            ("~/Escritorio", "Desktop"),
            ("/Escritorio", "Desktop"),
            ("Escritorio/prueba_jarvis", "prueba_jarvis"),
            ("~/Documentos/informe.pdf", "informe.pdf"),
            ("Descargas/archivo.zip", "archivo.zip"),
        ],
    )
    def test_expand_path_formatos(self, input_path: str, expected_leaf: str) -> None:
        resolved = expand_path(input_path)
        assert resolved.exists() or resolved.parent.exists(), (
            f"Ruta inválida para '{input_path}': {resolved}"
        )
        assert resolved.name.lower() == expected_leaf.lower() or resolved.parts[-1].lower() == expected_leaf.lower()

    def test_escritorio_no_es_ruta_relativa_raiz(self) -> None:
        """Evita el bug /Escritorio → \\Escritorio en la raíz del disco."""
        resolved = expand_path("/Escritorio/prueba_jarvis")
        assert str(resolved).startswith("C:") or resolved.drive, (
            f"Debe ser ruta absoluta del usuario, no raíz: {resolved}"
        )
        assert "Escritorio" not in str(resolved) or resolved.name == "prueba_jarvis"
        assert resolved.parent.exists()

    def test_tres_carpetas_distintas(self) -> None:
        desktop = resolve_special_folder("Escritorio")
        documents = resolve_special_folder("Documentos")
        downloads = resolve_special_folder("Descargas")
        assert desktop and documents and downloads
        assert desktop != documents
        assert desktop != downloads
