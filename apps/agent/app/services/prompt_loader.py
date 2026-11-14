import re
from functools import lru_cache
from pathlib import Path
from typing import Any

PROMPTS_ROOT = Path(__file__).parent.parent / "prompts"


@lru_cache(maxsize=32)
def load_system_prompt(name: str) -> str:
    """Load a static system prompt from prompts/system/<name> or prompts/<name>."""
    candidate_paths = [
        PROMPTS_ROOT / "system" / name,
        PROMPTS_ROOT / name,
    ]
    for p in candidate_paths:
        if p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                return f.read().strip()
    raise FileNotFoundError(f"System prompt '{name}' not found under {PROMPTS_ROOT}")


@lru_cache(maxsize=32)
def _load_user_template(name: str) -> str:
    """Load and cache raw user prompt template string from disk."""
    candidate_paths = [
        PROMPTS_ROOT / "user" / name,
        PROMPTS_ROOT / name,
    ]
    for p in candidate_paths:
        if p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    raise FileNotFoundError(f"User prompt template '{name}' not found under {PROMPTS_ROOT}")


def render_user_prompt(name: str, context: dict[str, Any]) -> str:
    """Render a user prompt template using safe key replacement.

    Replaces occurrences of `{variable}` or `{{variable}}` with context[variable],
    leaving unmapped braces intact to avoid KeyError with code blocks or JSON.
    """
    template_str = _load_user_template(name)

    def _replace_match(match: re.Match) -> str:
        key = match.group(1).strip()
        if key in context:
            val = context[key]
            return str(val) if val is not None else ""
        return match.group(0)

    return re.sub(r"\{\{?\s*([a-zA-Z0-9_]+)\s*\}?\}", _replace_match, template_str)
