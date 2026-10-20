"""Gestor de credenciales y claves de API en el keyring del escritorio (SecretService / GNOME Keyring / KWallet).

Proporciona almacenamiento seguro para API keys con respaldo transparente en variables de
entorno / .env privado (0600) cuando no hay un keyring gráfico disponible (ej. entornos headless o CI).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

SERVICE_NAME = "asistente-linux"

try:
    import keyring
    import keyring.backend
    import keyring.errors
    _KEYRING_MODULE_AVAILABLE = True
except ImportError:
    keyring = None
    _KEYRING_MODULE_AVAILABLE = False


def _is_usable_backend(backend: Any) -> bool:
    """Comprueba si el backend actual de keyring es funcional y no un backend dummy o fallido."""
    if backend is None:
        return False
    cls_name = getattr(backend, "__class__", type(backend)).__name__.lower()
    mod_name = getattr(backend, "__module__", "").lower()
    fail_names = ("fail", "null")
    if any(f in cls_name or f in mod_name for f in fail_names):
        return False
    # La prioridad de fail.Keyring es 0; los backends funcionales tienen prioridad >= 1
    priority = getattr(backend, "priority", 0)
    return priority > 0


def is_keyring_available() -> bool:
    """Indica si el sistema cuenta con un backend de keyring activo y funcional."""
    if not _KEYRING_MODULE_AVAILABLE or keyring is None:
        return False
    try:
        current_backend = keyring.get_keyring()
        return _is_usable_backend(current_backend)
    except Exception:
        return False


def get_backend_name() -> str:
    """Nombre descriptivo del backend activo de keyring."""
    if not _KEYRING_MODULE_AVAILABLE or keyring is None:
        return "No instalado"
    try:
        backend = keyring.get_keyring()
        name = getattr(backend, "name", None) or backend.__class__.__name__
        if not _is_usable_backend(backend):
            return f"No disponible ({name})"
        return name
    except Exception as e:
        return f"Error ({e})"


def _secret_username(provider: str) -> str:
    """Identificador del secreto dentro del servicio en el keyring."""
    return f"{provider.strip().upper()}_API_KEY"


def get_api_key(provider: str) -> str:
    """Obtiene la clave de API para un proveedor.

    Busca primero en el keyring del escritorio (si está disponible).
    Si no se encuentra o el keyring no está disponible, consulta variables de entorno / .env.
    """
    key_name = _secret_username(provider)

    # 1. Intentar leer del keyring del escritorio
    if is_keyring_available():
        try:
            stored = keyring.get_password(SERVICE_NAME, key_name)
            if stored and stored.strip() == "test-only-#'key" and "PYTEST_CURRENT_TEST" not in os.environ:
                try:
                    keyring.delete_password(SERVICE_NAME, key_name)
                except Exception:
                    pass
                stored = ""
            if stored and stored.strip() and "tu_clave_aqui" not in stored:
                return stored.strip()
        except Exception:
            pass

    # 2. Fallback: variables de entorno / archivo .env ya cargado
    env_val = os.getenv(key_name, "").strip()
    if env_val == "test-only-#'key" and "PYTEST_CURRENT_TEST" not in os.environ:
        return ""
    return env_val


def set_api_key(provider: str, api_key: str) -> bool:
    """Guarda la clave de API para un proveedor en el keyring del escritorio si está disponible.

    Devuelve True si se guardó en el keyring; False si el keyring no estaba disponible o falló.
    """
    key_name = _secret_username(provider)
    val = (api_key or "").strip()

    if not is_keyring_available():
        return False

    try:
        if val:
            keyring.set_password(SERVICE_NAME, key_name, val)
        else:
            try:
                keyring.delete_password(SERVICE_NAME, key_name)
            except Exception:
                pass
        return True
    except Exception:
        return False


def delete_api_key(provider: str) -> bool:
    """Elimina la clave de API del keyring del escritorio."""
    key_name = _secret_username(provider)
    if not is_keyring_available():
        return False
    try:
        keyring.delete_password(SERVICE_NAME, key_name)
        return True
    except Exception:
        return False


def migrate_env_keys_to_keyring(providers: Optional[List[str]] = None) -> Dict[str, bool]:
    """Copia las claves existentes en .env / variables de entorno hacia el keyring del escritorio."""
    if not is_keyring_available():
        return {}

    from src.core.providers import PROVIDERS
    target_providers = providers or list(PROVIDERS.keys())
    results: Dict[str, bool] = {}

    for prov in target_providers:
        env_val = os.getenv(f"{prov.upper()}_API_KEY", "").strip()
        if env_val and "tu_clave_aqui" not in env_val:
            success = set_api_key(prov, env_val)
            results[prov] = success

    return results


def get_keyring_status(providers: Optional[List[str]] = None) -> Dict[str, Any]:
    """Devuelve el estado del keyring para mostrarlo en diagnósticos o configuración."""
    from src.core.providers import PROVIDERS
    target_providers = providers or list(PROVIDERS.keys())

    available = is_keyring_available()
    stored_providers: List[str] = []

    if available:
        for prov in target_providers:
            try:
                val = keyring.get_password(SERVICE_NAME, _secret_username(prov))
                if val and val.strip() and "tu_clave_aqui" not in val:
                    stored_providers.append(prov)
            except Exception:
                pass

    return {
        "available": available,
        "backend": get_backend_name(),
        "service": SERVICE_NAME,
        "stored_providers": stored_providers,
    }
