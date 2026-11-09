import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def to_float(val: str | None) -> float | None:
    """Safely convert string to float or return None."""
    if val is None or val.strip() == "":
        return None
    try:
        return float(val)
    except ValueError as e:
        logger.warning(f"Invalid float value '{val}': {e}")
        return None


def to_int(val: str | None) -> int | None:
    """Safely convert string to int or return None."""
    if val is None or val.strip() == "":
        return None
    try:
        return int(val)
    except ValueError as e:
        logger.warning(f"Invalid integer value '{val}': {e}")
        return None


def get_api_settings() -> dict:
    """Retrieve core API configuration."""
    return {
        "database_url": os.getenv("DATABASE_URL", ""),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "session_secret": os.getenv("SESSION_SECRET", ""),
        "agent_service_url": os.getenv("AGENT_SERVICE_URL", ""),
        "agent_internal_secret": os.getenv("AGENT_INTERNAL_SECRET", "")
        or os.getenv("INTERNAL_SERVICE_KEY", ""),
        "allowed_origins": os.getenv("ALLOWED_ORIGINS", ""),
        "max_concurrent_jobs": to_int(os.getenv("MAX_CONCURRENT_JOBS_PER_SESSION")) or 1,
        "hourly_jobs_limit": to_int(os.getenv("RATE_LIMIT_JOBS_PER_HOUR")) or 5,
    }
