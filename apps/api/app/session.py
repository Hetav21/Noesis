import hashlib
import hmac
import os
import uuid
from typing import Annotated

from fastapi import Depends, Request, Response

SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "noesis_session")
SESSION_MAX_AGE = int(os.getenv("SESSION_COOKIE_MAX_AGE", str(30 * 24 * 3600)))  # 30 days


def get_session_secret() -> str:
    """Retrieve and validate the HMAC signing secret from the environment.

    Raises:
        ValueError: If SESSION_SECRET is not configured or uses an insecure placeholder.
    """
    secret = os.getenv("SESSION_SECRET", "").strip()
    if not secret:
        raise ValueError(
            "SESSION_SECRET environment variable is required and must not be empty. "
            "Please configure a cryptographically random secret string."
        )
    insecure_placeholders = {
        "change-this-to-a-secure-random-secret-in-production",
        "change-this-to-a-cryptographically-random-secret-in-production",
    }
    if secret in insecure_placeholders or secret.startswith("change-this-to-"):
        raise ValueError(
            "SESSION_SECRET is configured with an example placeholder value. "
            "Please configure a secure unique random string."
        )
    return secret


def sign_session_id(session_id: str, secret: str | None = None) -> str:
    """Generate an HMAC-SHA256 signature for a session ID.

    Args:
        session_id: The UUID session string to sign.
        secret: Optional secret string override (defaults to get_session_secret()).

    Returns:
        A dot-separated token consisting of '{session_id}.{hex_digest}'.
    """
    active_secret = secret or get_session_secret()
    sig = hmac.new(
        active_secret.encode("utf-8"),
        session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{session_id}.{sig}"


def verify_session_token(token: str | None, secret: str | None = None) -> str | None:
    """Verify an HMAC-signed session token.

    Args:
        token: The signed token string '{session_id}.{sig}'.
        secret: Optional secret override.

    Returns:
        The raw session ID if signature matches, or None if invalid or tampered.
    """
    if not token or "." not in token:
        return None

    parts = token.split(".", 1)
    if len(parts) != 2:
        return None

    raw_session_id, received_sig = parts[0], parts[1]
    if not raw_session_id or not received_sig:
        return None

    # Enforce ASCII-only to prevent unexpected parsing/unicode issues
    if not raw_session_id.isascii() or not received_sig.isascii():
        return None

    try:
        active_secret = secret or get_session_secret()
    except ValueError:
        return None

    expected_sig = hmac.new(
        active_secret.encode("utf-8"),
        raw_session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if hmac.compare_digest(received_sig, expected_sig):
        return raw_session_id

    return None


def generate_session_id() -> str:
    """Generate a random UUIDv4 session identifier string."""
    return str(uuid.uuid4())


def get_client_ip(request: Request) -> str:
    """Extract verified client IP address from proxy headers or direct socket connection.

    Only respects proxy headers (X-Forwarded-For, CF-Connecting-IP, X-Real-IP)
    when the immediate connecting peer is a verified trusted proxy.

    Args:
        request: The incoming FastAPI HTTP request.

    Returns:
        The resolved IP string.
    """
    direct_host = request.client.host if request.client else "127.0.0.1"

    trusted_proxies_env = os.getenv("TRUSTED_PROXIES", "127.0.0.1,localhost,::1")
    trusted_proxies = {p.strip() for p in trusted_proxies_env.split(",") if p.strip()}
    trust_all_proxies = os.getenv("TRUST_ALL_PROXIES", "false").lower() in ("true", "1")

    # Only inspect forwarded headers if immediate socket peer is trusted
    is_trusted_peer = trust_all_proxies or (direct_host in trusted_proxies)

    if is_trusted_peer:
        cf_connecting_ip = request.headers.get("cf-connecting-ip")
        if cf_connecting_ip:
            return cf_connecting_ip.strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # When behind trusted reverse proxies, the rightmost entry appended by
            # the trusted proxy boundary is authoritative against client-injected values
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                return parts[-1]

    return direct_host


def is_secure_request(request: Request) -> bool:
    """Check if the request is running over HTTPS or behind an SSL-terminating proxy.

    Args:
        request: The incoming FastAPI HTTP request.

    Returns:
        True if the request was made via TLS/HTTPS, False otherwise.
    """
    if os.getenv("SESSION_COOKIE_SECURE", "").lower() in ("true", "1"):
        return True
    if os.getenv("ENVIRONMENT", "").lower() in ("production", "prod"):
        return True
    if request.url.scheme == "https":
        return True
    return request.headers.get("x-forwarded-proto", "").lower() == "https"


def set_signed_session_cookie(
    response: Response,
    session_id: str,
    request: Request | None = None,
) -> None:
    """Attach the signed session cookie to the response with robust security attributes.

    Args:
        response: The FastAPI Response object to set cookies on.
        session_id: The verified session UUID to sign and store.
        request: Optional request context for HTTPS protocol detection.
    """
    signed_val = sign_session_id(session_id)
    is_secure = is_secure_request(request) if request else False
    samesite = os.getenv("SESSION_COOKIE_SAMESITE", "lax").lower()
    if samesite not in ("lax", "strict", "none"):
        samesite = "lax"

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
    """FastAPI dependency: resolves and verifies session ID, issuing a signed cookie if missing/invalid.

    Args:
        request: Incoming HTTP request.
        response: Outgoing HTTP response for setting cookies.

    Returns:
        A verified session UUID string.
    """
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    session_id = verify_session_token(cookie_token)

    # Check header fallback (useful for API clients or cross-origin reverse proxies)
    if not session_id:
        header_token = request.headers.get("x-session-token") or request.headers.get("x-session-id")
        session_id = verify_session_token(header_token)

    if not session_id:
        session_id = generate_session_id()

    # Renew signed cookie for active sessions to keep max-age fresh
    set_signed_session_cookie(response, session_id, request)

    return session_id


SessionIdDep = Annotated[str, Depends(get_or_create_session_id)]
ClientIpDep = Annotated[str, Depends(get_client_ip)]
