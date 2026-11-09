import hashlib
import hmac
import os
import uuid
from typing import Annotated

from fastapi import Depends, Request, Response

SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "noesis_session")
DEFAULT_SECRET = "noesis-session-secret-key-change-in-production-2026"
SESSION_SECRET = os.getenv("SESSION_SECRET", DEFAULT_SECRET)
SESSION_MAX_AGE = int(os.getenv("SESSION_COOKIE_MAX_AGE", str(30 * 24 * 3600)))  # 30 days


def get_session_secret() -> str:
    return os.getenv("SESSION_SECRET", DEFAULT_SECRET)


def sign_session_id(session_id: str, secret: str | None = None) -> str:
    """Generate an HMAC-SHA256 signature for a session ID."""
    active_secret = secret or get_session_secret()
    sig = hmac.new(
        active_secret.encode("utf-8"),
        session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{session_id}.{sig}"


def verify_session_token(token: str | None, secret: str | None = None) -> str | None:
    """Verify an HMAC-signed session token. Return the session ID if valid, None otherwise."""
    if not token or "." not in token:
        return None

    parts = token.split(".", 1)
    if len(parts) != 2:
        return None

    raw_session_id, received_sig = parts[0], parts[1]
    if not raw_session_id or not received_sig:
        return None

    active_secret = secret or get_session_secret()
    expected_sig = hmac.new(
        active_secret.encode("utf-8"),
        raw_session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if hmac.compare_digest(received_sig, expected_sig):
        return raw_session_id

    return None


def generate_session_id() -> str:
    """Generate a random UUIDv4 session identifier."""
    return str(uuid.uuid4())


def get_client_ip(request: Request) -> str:
    """Extract real client IP address from proxy headers or direct socket connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First entry in X-Forwarded-For is the originating client IP
        return forwarded.split(",")[0].strip()

    cf_connecting_ip = request.headers.get("cf-connecting-ip")
    if cf_connecting_ip:
        return cf_connecting_ip.strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


def is_secure_request(request: Request) -> bool:
    """Check if the request is running over HTTPS or behind an SSL-terminating proxy."""
    if os.getenv("SESSION_COOKIE_SECURE", "").lower() in ("true", "1"):
        return True
    if os.getenv("ENVIRONMENT", "").lower() in ("production", "prod"):
        return True
    if request.url.scheme == "https":
        return True
    if request.headers.get("x-forwarded-proto", "").lower() == "https":
        return True
    return False


def set_signed_session_cookie(
    response: Response,
    session_id: str,
    request: Request | None = None,
) -> None:
    """Attach the signed session cookie to the response with robust security attributes."""
    signed_val = sign_session_id(session_id)
    is_secure = is_secure_request(request) if request else False
    samesite = os.getenv("SESSION_COOKIE_SAMESITE", "lax").lower()
    if samesite not in ("lax", "strict", "none"):
        samesite = "lax"

    # SameSite=None requires Secure=True in modern browsers
    if samesite == "none":
        is_secure = True

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=signed_val,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite=samesite,
        secure=is_secure,
        path="/",
    )


async def get_or_create_session_id(
    request: Request,
    response: Response,
) -> str:
    """FastAPI dependency: resolves and verifies session ID, issuing a signed cookie if missing/invalid."""
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    session_id = verify_session_token(cookie_token)

    # Check header fallback (useful for API clients or cross-origin reverse proxies)
    if not session_id:
        header_token = request.headers.get("x-session-token") or request.headers.get("x-session-id")
        session_id = verify_session_token(header_token)

    if not session_id:
        session_id = generate_session_id()
        set_signed_session_cookie(response, session_id, request)

    return session_id


SessionIdDep = Annotated[str, Depends(get_or_create_session_id)]
ClientIpDep = Annotated[str, Depends(get_client_ip)]
