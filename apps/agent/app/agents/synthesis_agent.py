from pathlib import Path

from agents import Agent

from app.config import get_agent_settings
from app.services.prompt_loader import load_system_prompt

SYNTHESIS_AGENT_PROMPT = load_system_prompt("synthesis.md")

model, settings = get_agent_settings("SYNTHESIS_AGENT", "gpt-4o")

synthesis_agent = Agent(
    name="Synthesis Agent",
    instructions=SYNTHESIS_AGENT_PROMPT,
    model=model,
    model_settings=settings,
)
