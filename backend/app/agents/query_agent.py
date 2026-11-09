from pathlib import Path

from agents import Agent
from pydantic import BaseModel

from app.config import get_agent_settings

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "query.md"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    QUERY_AGENT_PROMPT = f.read()


class QueryResponse(BaseModel):
    queries: list[str]
    thoughts: str


model, settings = get_agent_settings("QUERY_AGENT", "gpt-4o-mini")

query_agent = Agent(
    name="Query Generator Agent",
    instructions=QUERY_AGENT_PROMPT,
    output_type=QueryResponse,
    model=model,
    model_settings=settings,
)
