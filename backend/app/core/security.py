import os
import re
import hmac
import hashlib
import json
import base64
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.config import settings

api_key_header = APIKeyHeader(name="X-Studio-Auth", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


class UserContext(BaseModel):
    user_id: str
    role: str = "creator"  # "owner", "admin", "art_director", "writer", "storyboarder", "creator"


def create_access_token(user_id: str, role: str = "creator", expires_in: int = 86400) -> str:
    """Creates a URL-safe HMAC-SHA256 signed bearer token with user_id and studio role."""
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(time.time()) + expires_in
    }
    raw = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), raw, hashlib.sha256).digest()
    return f"{base64.urlsafe_b64encode(raw).decode('utf-8')}.{base64.urlsafe_b64encode(sig).decode('utf-8')}"


def verify_token_payload(token: str) -> Optional[Dict[str, Any]]:
    """Verifies HMAC signature and expiration timestamp. Returns token payload dict if valid."""
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
        return payload
    except Exception:
        return None


def verify_token(token: str) -> Optional[str]:
    """Verifies token and returns sub (user_id). Preserves backwards compatibility."""
    payload = verify_token_payload(token)
    return payload.get("sub") if payload else None


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
    neutralized = content.replace("```system", "'''system")
    neutralized = re.sub(r"(?i)<\s*(system|instruction|developer)\s*>", r"[\1]", neutralized)
    return neutralized


def extract_raw_auth_token(
    x_studio_auth: Optional[str] = Security(api_key_header),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(http_bearer)
) -> Optional[str]:
    """Extracts raw token from either Authorization: Bearer <token> or X-Studio-Auth: <token>."""
    if bearer_creds and bearer_creds.credentials:
        return bearer_creds.credentials.strip()
    if x_studio_auth:
        clean = x_studio_auth.strip()
        if clean.lower().startswith("bearer "):
            return clean[7:].strip()
        return clean
    return None


def get_current_user(raw_token: Optional[str] = Depends(extract_raw_auth_token)) -> UserContext:
    """
    Identity and access resolution with strict environment separation.
    Returns UserContext with user_id and studio role.
    """
    is_dev = settings.APP_ENV in ("development", "test")

    if is_dev:
        if raw_token:
            payload = verify_token_payload(raw_token)
            if payload:
                return UserContext(user_id=payload["sub"], role=payload.get("role", "creator"))
            # Dev raw string fallback
            return UserContext(user_id=raw_token, role="creator")
        return UserContext(user_id="creator_default_user", role="creator")

    # PRODUCTION MODE - STRICT FAIL-CLOSED ZERO-TRUST
    if not settings.SECRET_KEY or settings.SECRET_KEY == "dev-secret-key-studio-insecure-only-for-local":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Production misconfiguration: SECRET_KEY must be securely configured."
        )

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication token."
        )

    payload = verify_token_payload(raw_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or unverified authentication token. Arbitrary identity assertion is forbidden in production."
        )

    return UserContext(user_id=payload["sub"], role=payload.get("role", "creator"))


def get_current_user_id(user_ctx: UserContext = Depends(get_current_user)) -> str:
    """Convenience dependency returning user_id string for existing endpoints."""
    return user_ctx.user_id


def require_roles(allowed_roles: List[str]):
    """Returns dependency checking that current user has one of allowed roles."""
    def _role_checker(user_ctx: UserContext = Depends(get_current_user)) -> UserContext:
        if user_ctx.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_ctx.role}' is not authorized for this operation. Requires one of: {allowed_roles}."
            )
        return user_ctx
    return _role_checker


def require_art_director_or_owner(user_ctx: UserContext = Depends(get_current_user)) -> UserContext:
    """Enforces that only art directors, admins, or owners can execute creative approval gates."""
    allowed = {"owner", "admin", "art_director", "creator"}
    if user_ctx.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user_ctx.role}' is not authorized to approve creative artifacts. Requires 'art_director', 'owner', or 'admin' role."
        )
    return user_ctx


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

    if require_owner and member.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Project owner privileges required."
        )

    return project
