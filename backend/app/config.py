import logging
import os
from dotenv import load_dotenv
from agents import ModelSettings

# Load environment variables on startup
load_dotenv()

logger = logging.getLogger(__name__)


def to_float(val: str | None) -> float | None:
    if val is None or val.strip() == "":
        return None
    try:
        return float(val)
    except ValueError as e:
        logger.warning(f"Invalid float value '{val}': {e}")
        return None


def to_int(val: str | None) -> int | None:
    if val is None or val.strip() == "":
        return None
    try:
        return int(val)
    except ValueError as e:
        logger.warning(f"Invalid integer value '{val}': {e}")
        return None


def get_agent_settings(prefix: str, default_model: str) -> tuple[str, ModelSettings]:
    """
    Get the configured model and ModelSettings for a given agent prefix.
    If the env vars are not set or invalid, fall back to defaults.
    """
    model = os.getenv(f"{prefix}_MODEL", default_model)
    
    temperature = os.getenv(f"{prefix}_TEMPERATURE")
    top_p = os.getenv(f"{prefix}_TOP_P")
    presence_penalty = os.getenv(f"{prefix}_PRESENCE_PENALTY")
    frequency_penalty = os.getenv(f"{prefix}_FREQUENCY_PENALTY")
    top_k = os.getenv(f"{prefix}_TOP_K")
    max_tokens = os.getenv(f"{prefix}_MAX_TOKENS")

    extra_args = {}
    top_k_val = to_int(top_k)
    if top_k_val is not None:
        extra_args["top_k"] = top_k_val

    settings = ModelSettings(
        temperature=to_float(temperature),
        top_p=to_float(top_p),
        presence_penalty=to_float(presence_penalty),
        frequency_penalty=to_float(frequency_penalty),
        max_tokens=to_int(max_tokens),
        extra_args=extra_args if extra_args else None
    )
    
    return model, settings
