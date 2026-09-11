"""
Operaciones con archivos y carpetas.
Buscar, crear, mover, copiar y eliminar con confirmación previa.

Resuelve carpetas especiales de Windows (Escritorio, Documentos, Descargas)
mediante SHGetKnownFolderPath, no rutas relativas inventadas.
"""

from __future__ import annotations

import os
import platform
import shutil
import uuid
from pathlib import Path
from typing import Final

# GUIDs de carpetas conocidas de Windows (KNOWNFOLDERID)
_FOLDERID_DESKTOP: Final = "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"
_FOLDERID_DOCUMENTS: Final = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"
_FOLDERID_DOWNLOADS: Final = "{374DE290-123F-4563-9164-39C46DE6B50E}"

# Alias en español e inglés → GUID
SPECIAL_FOLDER_ALIASES: Final[dict[str, str]] = {
    "desktop": _FOLDERID_DESKTOP,
    "escritorio": _FOLDERID_DESKTOP,
    "documents": _FOLDERID_DOCUMENTS,
    "documentos": _FOLDERID_DOCUMENTS,
    "mis documentos": _FOLDERID_DOCUMENTS,
    "my documents": _FOLDERID_DOCUMENTS,
    "downloads": _FOLDERID_DOWNLOADS,
    "descargas": _FOLDERID_DOWNLOADS,
}

# Candidatos de fallback por alias (si SHGetKnownFolderPath falla)
_FALLBACK_SUBDIRS: Final[dict[str, list[str]]] = {
    "desktop": ["Desktop", "Escritorio"],
    "escritorio": ["Desktop", "Escritorio"],
    "documents": ["Documents", "Documentos", "Mis documentos"],
    "documentos": ["Documents", "Documentos", "Mis documentos"],
    "mis documentos": ["Documents", "Documentos", "Mis documentos"],
    "my documents": ["Documents", "Documentos"],
    "downloads": ["Downloads", "Descargas"],
    "descargas": ["Downloads", "Descargas"],
}


# Caché en memoria para no llamar al API repetidamente
_folder_cache: dict[str, Path] = {}


def _fallback_special_folder(alias_key: str) -> Path | None:
    """
    Fallback: busca la carpeta bajo el perfil del usuario.

    Útil cuando SHGetKnownFolderPath falla (p. ej. Descargas en algunos Windows).
    """
    candidates = _FALLBACK_SUBDIRS.get(alias_key, [])
    home = Path.home()
    for subdir in candidates:
        candidate = home / subdir
        if candidate.is_dir():
            return candidate
    if candidates:
        return home / candidates[0]
    return None


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _get_known_folder_path(folder_id: str) -> Path | None:
    """
    Obtiene la ruta absoluta de una carpeta conocida de Windows.

    Usa SHGetKnownFolderPath vía ctypes (sin dependencias extra).

    Args:
        folder_id: GUID de la carpeta (KNOWNFOLDERID).

    Returns:
        Path absoluto o None si falla / no es Windows.
    """
    if not _is_windows():
        return None

    try:
        import ctypes
        from ctypes import Structure, byref, c_ulong, c_ushort, c_wchar_p, c_ubyte, windll

        class GUID(Structure):
            _fields_ = [
                ("Data1", c_ulong),
                ("Data2", c_ushort),
                ("Data3", c_ushort),
                ("Data4", c_ubyte * 8),
            ]

        def _parse_guid(guid_str: str) -> GUID:
            u = uuid.UUID(guid_str)
            data4 = (c_ubyte * 8)(*u.bytes[8:])
            return GUID(u.time_low, u.time_mid, u.time_hi_version, data4)

        path_ptr = c_wchar_p()
        guid = _parse_guid(folder_id)
        # KF_FLAG_DEFAULT = 0
        hr = windll.shell32.SHGetKnownFolderPath(byref(guid), 0, None, byref(path_ptr))
        if hr != 0 or not path_ptr.value:
            return None

        resolved = Path(path_ptr.value)
        windll.ole32.CoTaskMemFree(path_ptr)
        return resolved
    except Exception:
        return None


def _resolve_alias_to_path(alias_key: str, folder_id: str) -> Path | None:
    """Resuelve un alias usando API de Windows y fallback al perfil del usuario."""
    if folder_id in _folder_cache:
        return _folder_cache[folder_id]

    path = _get_known_folder_path(folder_id)
    if path is not None and path.exists():
        _folder_cache[folder_id] = path
        return path

    fallback = _fallback_special_folder(alias_key)
    if fallback is not None:
        _folder_cache[folder_id] = fallback
        return fallback
    return path  # Puede ser None o path del API aunque no exista


def resolve_special_folder(name: str) -> Path | None:
    """
    Resuelve un alias de carpeta especial al path absoluto del sistema.

    Args:
        name: Nombre como 'Escritorio', 'Documentos', 'Downloads', etc.

    Returns:
        Path absoluto existente en el SO, o None si no se reconoce.
    """
    key = name.strip().strip("/\\").lower()
    folder_id = SPECIAL_FOLDER_ALIASES.get(key)
    if folder_id is None:
        return None
    return _resolve_alias_to_path(key, folder_id)


def expand_path(path: str) -> Path:
    """
    Expande una ruta incluyendo carpetas especiales de Windows.

    Soporta:
      - Escritorio/carpeta, ~/Escritorio/carpeta, /Escritorio/carpeta
      - Documentos, Descargas (y equivalentes en inglés)
      - ~, variables de entorno y rutas normales

    Args:
        path: Ruta ingresada por el usuario o el LLM.

    Returns:
        Path absoluto resuelto.
    """
    raw = path.strip()
    if not raw:
        return Path(".")

    normalized = raw.replace("\\", "/")

    # ~/Escritorio/... o ~\Documentos\...
    if normalized.startswith("~"):
        remainder = normalized[1:].lstrip("/")
        if remainder:
            parts = remainder.split("/")
            special = resolve_special_folder(parts[0])
            if special is not None:
                rest = parts[1:]
                return special.joinpath(*rest) if rest else special
        return Path(os.path.expandvars(os.path.expanduser(raw)))

    # Escritorio/..., /Escritorio/..., \Escritorio\... (evita raíz del disco)
    stripped = normalized.lstrip("/")
    parts = stripped.split("/") if stripped else []
    if parts:
        special = resolve_special_folder(parts[0])
        if special is not None:
            rest = parts[1:]
            return special.joinpath(*rest) if rest else special

    return Path(os.path.expandvars(os.path.expanduser(raw)))


# Alias interno usado por las funciones del módulo
_expand_path = expand_path


def search_file(query: str, path: str = "~", max_results: int = 20) -> str:
    """
    Busca archivos por nombre en un directorio.

    Args:
        query: Nombre o patrón a buscar.
        path: Directorio base (default: home del usuario).
        max_results: Máximo de resultados.

    Returns:
        Lista de archivos encontrados.
    """
    base = expand_path(path)
    if not base.exists():
        return f"La ruta '{base}' no existe"

    found: list[str] = []
    query_lower = query.lower()

    try:
        for root, _dirs, files in os.walk(base):
            for fname in files:
                if query_lower in fname.lower():
                    found.append(str(Path(root) / fname))
                    if len(found) >= max_results:
                        break
            if len(found) >= max_results:
                break
    except PermissionError:
        return f"Sin permisos para buscar en '{base}'"

    if not found:
        return f"No encontré archivos con '{query}' en '{base}'"

    lines = "\n".join(f"- {f}" for f in found)
    return f"Encontrados {len(found)} archivo(s):\n{lines}"


def create_folder(path: str) -> str:
    """Crea una carpeta (y padres si no existen)."""
    target = expand_path(path)
    try:
        target.mkdir(parents=True, exist_ok=True)
        return f"Carpeta creada: {target}"
    except OSError as exc:
        return f"Error al crear carpeta: {exc}"


def move_file(src: str, dst: str) -> str:
    """Mueve un archivo o carpeta."""
    source = expand_path(src)
    destination = expand_path(dst)
    try:
        shutil.move(str(source), str(destination))
        return f"Movido '{source}' → '{destination}'"
    except OSError as exc:
        return f"Error al mover: {exc}"


def copy_file(src: str, dst: str) -> str:
    """Copia un archivo o carpeta."""
    source = expand_path(src)
    destination = expand_path(dst)
    try:
        if source.is_dir():
            shutil.copytree(str(source), str(destination))
        else:
            shutil.copy2(str(source), str(destination))
        return f"Copiado '{source}' → '{destination}'"
    except OSError as exc:
        return f"Error al copiar: {exc}"


def delete_file(path: str) -> str:
    """
    Elimina un archivo o carpeta.
    Nota: requiere confirmación del SecurityGuard antes de llamar.

    Args:
        path: Ruta del archivo o carpeta.

    Returns:
        Mensaje de resultado.
    """
    target = expand_path(path)
    try:
        if target.is_dir():
            shutil.rmtree(str(target))
        elif target.is_file():
            target.unlink()
        else:
            return f"No existe: {target}"
        return f"Eliminado: {target}"
    except OSError as exc:
        return f"Error al eliminar: {exc}"
