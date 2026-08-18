import base64
import hashlib
from typing import Optional

from app.core.config import settings

# Cryptography Fernet for API key storage encryption
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


def _get_fernet_key() -> bytes:
    """Derive a consistent 32-byte URL-safe base64 key from configuration."""
    if settings.ENCRYPTION_KEY:
        try:
            return settings.ENCRYPTION_KEY.encode()
        except Exception:
            pass
    key_hash = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key_hash)


def encrypt_api_key(raw_api_key: Optional[str]) -> Optional[str]:
    """Encrypt sensitive LLM API key before persisting to database."""
    if not raw_api_key:
        return None
    if HAS_CRYPTOGRAPHY:
        fernet = Fernet(_get_fernet_key())
        return fernet.encrypt(raw_api_key.encode()).decode()
    else:
        encoded = base64.b64encode(raw_api_key.encode()).decode()
        return f"b64:{encoded}"


def decrypt_api_key(encrypted_api_key: Optional[str]) -> Optional[str]:
    """Decrypt stored LLM API key for provider requests."""
    if not encrypted_api_key:
        return None
    try:
        if encrypted_api_key.startswith("b64:"):
            return base64.b64decode(encrypted_api_key[4:].encode()).decode()
        if HAS_CRYPTOGRAPHY:
            fernet = Fernet(_get_fernet_key())
            return fernet.decrypt(encrypted_api_key.encode()).decode()
        return encrypted_api_key
    except Exception:
        return encrypted_api_key


def mask_api_key(raw_api_key: Optional[str]) -> str:
    """Return a masked representation of an API key for safe API responses (e.g. sk-abc...1234)."""
    if not raw_api_key:
        return ""
    if len(raw_api_key) <= 8:
        return "********"
    prefix = raw_api_key[:4]
    suffix = raw_api_key[-4:]
    return f"{prefix}...{suffix}"
