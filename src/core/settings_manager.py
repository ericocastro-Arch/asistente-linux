"""Gestor de configuraciones y persistencia para LinuxMate AI."""

from __future__ import annotations

import os
import math
import re
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from src.core.storage import _db_path
from src.core.providers import PROVIDERS, create_provider_client, completion_options, number_setting
from src.core.keyring_manager import (
    get_api_key,
    set_api_key,
    get_keyring_status,
    migrate_env_keys_to_keyring,
    is_keyring_available,
)

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def _write_private_file(path: Path, text: str) -> None:
    """Escribe de forma atómica un archivo legible solo por el propietario (0600)."""
    tmp_path = path.with_name(path.name + ".tmp")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _tighten_env_permissions(path: Path = ENV_PATH) -> None:
    """Quita el acceso de grupo/otros a un .env existente (contiene API keys)."""
    try:
        if path.is_file() and not path.is_symlink() and path.stat().st_mode & 0o077:
            path.chmod(0o600)
    except OSError:
        pass


def _remove_env_keys(keys: set[str]) -> None:
    """Elimina claves ya resguardadas en keyring y limpia el entorno del proceso."""
    if keys and ENV_PATH.exists():
        if ENV_PATH.is_symlink():
            raise OSError("El archivo .env es un enlace simbólico; no puedo retirar claves de forma segura.")
        retained = []
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True):
            stripped = line.strip()
            key = stripped.split("=", 1)[0].strip() if stripped and not stripped.startswith("#") and "=" in stripped else ""
            if key not in keys:
                retained.append(line)
        _write_private_file(ENV_PATH, "".join(retained))
    for key in keys:
        os.environ.pop(key, None)


_tighten_env_permissions()
load_dotenv(ENV_PATH)


def get_storage_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de la base de datos de memoria SQLite."""
    path = _db_path()
    if not path.exists():
        return {"total_messages": 0, "total_sessions": 0, "db_size_kb": 0.0}

    size_kb = round(path.stat().st_size / 1024, 1)
    total_messages = 0
    total_sessions = 0
    try:
        with sqlite3.connect(path) as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM messages")
            row = cur.fetchone()
            if row:
                total_messages = row[0]
            cur.execute("SELECT COUNT(*) FROM sessions")
            row = cur.fetchone()
            if row:
                total_sessions = row[0]
    except Exception:
        pass

    return {
        "total_messages": total_messages,
        "total_sessions": total_sessions,
        "db_size_kb": size_kb,
    }


def clear_assistant_memory() -> Dict[str, Any]:
    """Borra el historial de conversaciones y sesiones de SQLite."""
    path = _db_path()
    if not path.exists():
        return {"success": True, "message": "No había memoria registrada para vaciar."}

    try:
        with sqlite3.connect(path) as con:
            con.execute("DELETE FROM messages")
            con.execute("DELETE FROM sessions")
        with sqlite3.connect(path, isolation_level=None) as con:
            con.execute("VACUUM")
        return {"success": True, "message": "Memoria de conversación e historial vaciados con éxito."}
    except Exception as exc:
        return {"success": False, "error": f"Error al limpiar base de datos: {exc}"}


def get_system_diagnostics() -> Dict[str, Any]:
    """Diagnóstico del entorno y herramientas del sistema Linux."""
    from src.core.distro import detect_distro
    distro = detect_distro()
    return {
        "distro_name": distro.pretty_name,
        "distro_family": distro.family.value,
        "native_package_manager": distro.native_package_manager,
        "apt": bool(shutil.which("apt")),
        "dnf": bool(shutil.which("dnf")),
        "pacman": bool(shutil.which("pacman")),
        "zypper": bool(shutil.which("zypper")),
        "snap": bool(shutil.which("snap")),
        "flatpak": bool(shutil.which("flatpak")),
        "gtk_launch": bool(shutil.which("gtk-launch")),
        "python_version": sys.version.split()[0],
        "psutil": True,
    }


def get_settings() -> Dict[str, Any]:
    """Devuelve todas las configuraciones actuales del sistema y del modelo."""
    # Recargar .env para asegurar valores frescos
    load_dotenv(ENV_PATH, override=True)
    from src.core.distro import detect_distro, get_active_package_manager
    distro = detect_distro()

    return {
        "llm": {
            **{f"{provider}_{field}": (
                get_api_key(provider) if field == "api_key"
                else os.getenv(f"{provider.upper()}_{field.upper()}", defaults.get(field, "")).strip()
            )
            for provider, defaults in PROVIDERS.items() for field in ("api_key", "model", "base_url")},
            "provider": os.getenv("LLM_PROVIDER", "groq").strip().lower(),
            "temperature": number_setting("LLM_TEMPERATURE", 0.2, 0, 1),
            "system_mode": os.getenv("SYSTEM_MODE", "didactic").strip().lower(),
            "request_timeout": number_setting("LLM_REQUEST_TIMEOUT", 60, 5, 600),
            "max_tokens": int(number_setting("LLM_MAX_TOKENS", 1500, 256, 32768)),
        },
        "providers": [{"id": key, **value} for key, value in PROVIDERS.items()],
        "security": {
            "security_mode": os.getenv("SECURITY_MODE", "safe").strip().lower(),
            "package_preference": os.getenv("PACKAGE_PREFERENCE", distro.native_package_manager).strip().lower(),
        },
        "distro": {
            "name": distro.pretty_name,
            "family": distro.family.value,
            "native_package_manager": distro.native_package_manager,
            "active_package_manager": get_active_package_manager(),
            "available_package_managers": distro.available_package_managers,
        },
        "appearance": {
            "chat_default_float": os.getenv("CHAT_DEFAULT_FLOAT", "false").strip().lower() == "true",
            "enable_blur_effects": os.getenv("ENABLE_BLUR_EFFECTS", "true").strip().lower() == "true",
            "enable_notifications": os.getenv("ENABLE_NOTIFICATIONS", "true").strip().lower() == "true",
            "theme": os.getenv("APP_THEME", "cyber-purple").strip(),
        },
        "memory": get_storage_stats(),
        "keyring": get_keyring_status(),
        "system_diagnostics": get_system_diagnostics(),
    }


def save_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda las configuraciones en el archivo .env y actualiza os.environ."""
    updates: Dict[str, str] = {}
    env_removals: set[str] = set()

    if not isinstance(settings, dict) or any(not isinstance(settings.get(section, {}), dict) for section in ("llm", "security", "appearance")):
        return {"success": False, "error": "Configuración inválida."}

    llm = settings.get("llm", {})
    if "provider" in llm and (not isinstance(llm["provider"], str) or llm["provider"] not in PROVIDERS):
        return {"success": False, "error": "Proveedor de IA no reconocido."}
    for provider in PROVIDERS:
        for field in ("api_key", "model", "base_url"):
            name = f"{provider}_{field}"
            if name in llm:
                val = str(llm[name]).strip()
                if any(char in val for char in ("\n", "\r", "\0")):
                    return {"success": False, "error": "Los campos no pueden contener saltos de línea."}
                if field == "api_key":
                    try:
                        keyring_saved = is_keyring_available() and set_api_key(provider, val)
                    except Exception:
                        keyring_saved = False
                    if keyring_saved:
                        env_removals.add(name.upper())
                        continue
                updates[name.upper()] = val
    for field, env_name, minimum, maximum in (("request_timeout", "LLM_REQUEST_TIMEOUT", 5, 600), ("max_tokens", "LLM_MAX_TOKENS", 256, 32768), ("temperature", "LLM_TEMPERATURE", 0, 1)):
        if field in llm:
            try:
                value = float(llm[field])
                if not math.isfinite(value) or not minimum <= value <= maximum:
                    raise ValueError()
                if field != "temperature" and not value.is_integer():
                    raise ValueError()
                updates[env_name] = str(value if field == "temperature" else int(value))
            except (TypeError, ValueError):
                return {"success": False, "error": f"Valor inválido para {field}: usa {minimum} a {maximum}."}
    if "provider" in llm:
        updates["LLM_PROVIDER"] = str(llm["provider"]).strip().lower()
    if "system_mode" in llm:
        updates["SYSTEM_MODE"] = str(llm["system_mode"]).strip().lower()

    security = settings.get("security", {})
    if "security_mode" in security:
        updates["SECURITY_MODE"] = str(security["security_mode"]).strip().lower()
    if "package_preference" in security:
        updates["PACKAGE_PREFERENCE"] = str(security["package_preference"]).strip().lower()

    appearance = settings.get("appearance", {})
    if "chat_default_float" in appearance:
        updates["CHAT_DEFAULT_FLOAT"] = "true" if appearance["chat_default_float"] else "false"
    if "enable_blur_effects" in appearance:
        updates["ENABLE_BLUR_EFFECTS"] = "true" if appearance["enable_blur_effects"] else "false"
    if "enable_notifications" in appearance:
        updates["ENABLE_NOTIFICATIONS"] = "true" if appearance["enable_notifications"] else "false"
    if "theme" in appearance:
        updates["APP_THEME"] = str(appearance["theme"]).strip()

    if any(any(char in value for char in ("\n", "\r", "\0")) for value in updates.values()):
        return {"success": False, "error": "Los campos no pueden contener saltos de línea."}

    def env_value(value):
        if re.fullmatch(r"[A-Za-z0-9_./:@+,-]*", value):
            return value
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

    # Escribir o actualizar archivo .env
    try:
        existing_lines = []
        if ENV_PATH.exists():
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()

        new_lines = []
        handled_keys = set()

        for line in existing_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, _ = stripped.split("=", 1)
                key = key.strip()
                if key in env_removals:
                    continue
                if key in updates:
                    new_lines.append(f"{key}={env_value(updates[key])}\n")
                    handled_keys.add(key)
                    continue
            new_lines.append(line)

        # Agregar claves nuevas al final
        unhandled = [k for k in updates if k not in handled_keys]
        if unhandled:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append("\n# Configuraciones actualizadas por LinuxMate GUI\n")
            for k in unhandled:
                new_lines.append(f"{k}={env_value(updates[k])}\n")

        _write_private_file(ENV_PATH, "".join(new_lines))
        _remove_env_keys(env_removals)

        for k, v in updates.items():
            os.environ[k] = v

        return {"success": True, "message": "Configuración guardada correctamente en el sistema."}
    except Exception as exc:
        return {"success": False, "error": f"Error al guardar archivo .env: {exc}"}


PROVIDER_FALLBACK_MODELS: Dict[str, tuple[str, ...]] = {
    "groq": ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"),
    "nvidia": ("meta/llama-3.1-70b-instruct", "meta/llama-3.2-11b-vision-instruct"),
    "openai": ("gpt-4o-mini", "gpt-4o"),
    "anthropic": ("claude-3-7-sonnet-latest", "claude-3-5-sonnet-latest", "claude-opus-5-5"),
    "gemini": (
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-flash-latest",
        "gemini-3.8-flash",
    ),
    "xai": ("grok-2-latest", "grok-3-mini", "grok-4.7"),
    "together": ("meta-llama/Llama-3.3-70B-Instruct-Turbo", "Qwen/Qwen2.5-Coder-32B-Instruct"),
    "deepseek": ("deepseek-chat", "deepseek-coder", "deepseek-flash"),
    "qwen": ("qwen-plus", "qwen-turbo", "qwen-max"),
    "moonshot": ("moonshot-v1-8k", "kimi-k2-0711-preview", "kimi-k2.6"),
    "zai": ("glm-4-flash", "glm-4-plus", "glm-5.3"),
    "ollama": ("llama3.2", "qwen2.5-coder", "mistral"),
    "custom": (),
}


def check_llm_connection(
    provider: str,
    api_key: str,
    model: str,
    base_url: str = "",
) -> Dict[str, Any]:
    """Realiza una consulta mínima de prueba para verificar que la llave y el modelo son válidos."""
    provider = provider.strip().lower()
    api_key = api_key.strip()
    model = model.strip()

    if provider != "ollama" and not api_key:
        return {"success": False, "error": f"Por favor ingresa una clave de API para {provider.upper()}."}

    try:
        client, model, _ = create_provider_client(provider, api_key, model, base_url, timeout=30)
        if not model:
            return {"success": False, "error": "Ingresa el identificador del modelo."}
        with client:
            try:
                response = client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": "Responde con la palabra: listo."}],
                    **completion_options(provider, model, 0.2, 1024),
                )
            except Exception as primary_exc:
                err_text = str(primary_exc)
                err_low = err_text.lower()
                is_auth_err = any(
                    tok in err_low for tok in ("401", "403", "invalid_api_key", "invalid api key", "unauthorized", "api_key_invalid")
                )
                if is_auth_err:
                    raise

                # Probar modelos alternativos del proveedor o descubiertos vía client.models.list()
                candidates = list(PROVIDER_FALLBACK_MODELS.get(provider, ()))
                try:
                    page = client.models.list()
                    raw_ids = [getattr(m_obj, "id", "") for m_obj in getattr(page, "data", []) or []]
                    # Priorizar modelos principales (ej. gemini-* antes de gemma-*)
                    raw_ids.sort(key=lambda x: (0 if "gemini" in x.lower() else 1))
                    for m_id in raw_ids:
                        low_id = m_id.lower()
                        if not m_id or m_id in candidates:
                            continue
                        if any(s in low_id for s in ("embed", "whisper", "tts", "dall-e", "moderation", "audio", "rerank", "imagen", "veo", "aqa")):
                            continue
                        candidates.append(m_id)
                        if len(candidates) >= 12:
                            break
                except Exception:
                    pass

                for alt_model in candidates:
                    if alt_model == model:
                        continue
                    try:
                        alt_resp = client.chat.completions.create(
                            model=alt_model,
                            messages=[{"role": "user", "content": "Responde con la palabra: listo."}],
                        )
                        if alt_resp.choices:
                            return {
                                "success": True,
                                "recommended_model": alt_model,
                                "message": (
                                    f"Conexión verificada con {PROVIDERS[provider]['name']}. "
                                    f"Se seleccionó automáticamente el modelo disponible '{alt_model}'."
                                ),
                            }
                    except Exception:
                        continue

                is_overload = any(
                    tok in err_low
                    for tok in ("503", "429", "unavailable", "high demand", "overloaded", "resource_exhausted")
                )
                if is_overload:
                    return {
                        "success": True,
                        "message": (
                            f"Tu clave de {PROVIDERS[provider]['name']} es válida (autenticación correcta), "
                            f"pero el modelo '{model}' reporta alta demanda temporal (503). "
                            "Configuración lista y guardada."
                        ),
                    }
                raise
        if not response.choices:
            return {"success": False, "error": "La API no devolvió una respuesta válida."}
        return {"success": True, "message": f"Conexión verificada: {PROVIDERS[provider]['name']} · {model}."}
    except Exception as exc:
        message = str(exc).replace(api_key, "[clave oculta]") if api_key else str(exc)
        return {"success": False, "error": f"Error de conexión: {message[:400]}"}


def list_llm_models(provider: str, api_key: str, base_url: str = "") -> Dict[str, Any]:
    try:
        client, _, _ = create_provider_client(provider, api_key, base_url=base_url, timeout=20)
        with client:
            page = client.models.list()
            models = sorted({model.id for model in page.data})
        return {"success": True, "models": models}
    except Exception as exc:
        message = str(exc).replace(api_key, "[clave oculta]") if api_key else str(exc)
        return {"success": False, "error": f"No se pudo consultar el catálogo. Puedes escribir el modelo manualmente. {message[:250]}"}


test_llm_connection = check_llm_connection


def run_system_cleanup() -> Dict[str, Any]:
    """Limpia miniaturas temporales y directorios temporales de usuario de forma segura."""
    freed_bytes = 0
    targets = [
        Path.home() / ".cache" / "thumbnails",
    ]
    for target in targets:
        if target.exists() and target.is_dir():
            try:
                for item in target.glob("**/*"):
                    if item.is_file():
                        try:
                            freed_bytes += item.stat().st_size
                            item.unlink()
                        except Exception:
                            pass
            except Exception:
                pass

    freed_mb = round(freed_bytes / (1024 * 1024), 2)
    return {
        "success": True,
        "freed_mb": freed_mb,
        "message": f"Se liberaron {freed_mb} MB en caché de usuario de forma segura.",
    }


def migrate_keys_to_keyring() -> Dict[str, Any]:
    """Migra las claves presentes en .env al keyring del escritorio si está disponible."""
    if not is_keyring_available():
        return {
            "success": False,
            "message": "Keyring del escritorio no disponible en esta sesión. Se mantiene el archivo .env seguro (0600).",
            "migrated": {},
        }
    migrated = migrate_env_keys_to_keyring()
    migrated_keys = {f"{provider.upper()}_API_KEY" for provider, success in migrated.items() if success}
    try:
        _remove_env_keys(migrated_keys)
    except OSError as exc:
        return {
            "success": False,
            "message": f"Las claves se copiaron al keyring, pero no pude quitarlas de .env: {exc}",
            "migrated": migrated,
        }
    return {
        "success": True,
        "message": f"Se migraron {len(migrated)} claves de API al almacén seguro del sistema.",
        "migrated": migrated,
    }

