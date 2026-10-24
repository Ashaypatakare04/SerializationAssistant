import os
import re
import hmac
import hashlib
import json
import base64
import time
from typing import Optional
from pathlib import Path
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from backend.app.core.config import settings

api_key_header = APIKeyHeader(name="X-Studio-Auth", auto_error=False)

def create_access_token(user_id: str, expires_in: int = 86400) -> str:
    """Creates a URL-safe HMAC-SHA256 signed bearer token."""
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + expires_in
    }
    raw = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), raw, hashlib.sha256).digest()
    return f"{base64.urlsafe_b64encode(raw).decode('utf-8')}.{base64.urlsafe_b64encode(sig).decode('utf-8')}"

def verify_token(token: str) -> Optional[str]:
    """Verifies HMAC signature and expiration timestamp. Returns user_id if valid."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 2:
            return None
        raw = base64.urlsafe_b64decode(parts[0].encode('utf-8'))
        sig = base64.urlsafe_b64decode(parts[1].encode('utf-8'))
        expected = hmac.new(settings.SECRET_KEY.encode('utf-8'), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(raw.decode('utf-8'))
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("sub")
    except Exception:
        return None

def validate_safe_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal or reserved names."""
    base = os.path.basename(filename)
    clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base)
    if not clean or clean.startswith("."):
        return f"safe_{clean}" if clean else "unnamed_file"
    return clean

def get_safe_storage_path(base_dir: str, rel_path: str) -> Path:
    """Ensure resolved path stays strictly within base directory."""
    base = Path(base_dir).resolve()
    target = (base / rel_path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
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
    Identity and access resolution with strict environment separation.
    
    In DEVELOPMENT or TEST modes:
      - Accepts verified signed token or plain user_id string for local testing convenience.
      - Falls back to 'creator_default_user' when no header is supplied.
      
    In PRODUCTION mode (Fail-Closed Zero-Trust):
      - Rejects arbitrary unverified string identity assertion.
      - Fails closed (500) if SECRET_KEY is left at insecure dev default.
      - Requires a cryptographically valid HMAC signed token.
    """
    is_dev = settings.APP_ENV in ("development", "test")
    
    if is_dev:
        if auth_header:
            token_user = verify_token(auth_header)
            return token_user if token_user else auth_header
        return "creator_default_user"

    # PRODUCTION MODE - STRICT FAIL-CLOSED ZERO-TRUST
    if not settings.SECRET_KEY or settings.SECRET_KEY == "dev-secret-key-studio-insecure-only-for-local":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Production misconfiguration: SECRET_KEY must be securely configured."
        )

    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication token."
        )

    user_id = verify_token(auth_header)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or unverified authentication token. Arbitrary identity assertion is forbidden in production."
        )

    return user_id

async def verify_project_access(
    project_id: str,
    user_id: str,
    db,
    require_owner: bool = False
):
    """
    Enforces authorization check. Verifies the requesting user is the project owner
    or an authorized collaborator. Raises HTTP 403 Forbidden or HTTP 404 Not Found.
    """
    from sqlalchemy import select
    from backend.app.models.project import Project, ProjectMember

    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    if project.owner_id == user_id:
        return project

    # Check member role
    member_stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    )
    m_res = await db.execute(member_stmt)
    member = m_res.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view or modify this project."
        )

    if require_owner and member.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Project owner privileges required."
        )

    return project
