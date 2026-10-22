import os
import re
from pathlib import Path
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from backend.app.core.config import settings

api_key_header = APIKeyHeader(name="X-Studio-Auth", auto_error=False)

def validate_safe_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal or reserved names."""
    base = os.path.basename(filename)
    clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base)
    if not clean or clean.startswith("."):
        return f"safe_{clean}" if clean else "unnamed_file"
    return clean

def get_safe_storage_path(base_dir: str, rel_path: str) -> Path:
    """Ensure resolved path stays within base directory."""
    base = Path(base_dir).resolve()
    target = (base / rel_path).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Illegal path traversal detected."
        )
    return target

def sanitize_untrusted_text(content: str) -> str:
    """
    Sanitize untrusted manuscript content to prevent prompt injection 
    from overwriting system directives when fed to AI models.
    """
    # Neutralize common system prompt delimiter hijacking attempts
    neutralized = content.replace("```system", "'''system")
    neutralized = re.sub(r"(?i)<\s*(system|instruction|developer)\s*>", r"[\1]", neutralized)
    return neutralized

def get_current_user_id(auth_header: str = Security(api_key_header)) -> str:
    """
    In development mode, returns a default user or the specified header.
    In production mode, requires a valid token.
    """
    if auth_header:
        return auth_header
    if settings.APP_ENV == "development":
        return "creator_default_user"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication token."
    )
