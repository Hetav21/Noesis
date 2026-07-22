from agents import Agent
from app.config import get_agent_settings
from pathlib import Path

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "synthesis.md"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYNTHESIS_AGENT_PROMPT = f.read()

model, settings = get_agent_settings("SYNTHESIS_AGENT", "gpt-4o")

synthesis_agent = Agent(
    name="Synthesis Agent",
    instructions=SYNTHESIS_AGENT_PROMPT,
    model=model,
    model_settings=settings,
)
