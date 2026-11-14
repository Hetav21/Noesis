from pathlib import Path

from agents import Agent
from pydantic import BaseModel

from app.config import get_agent_settings
from app.services.prompt_loader import load_system_prompt

QUERY_AGENT_PROMPT = load_system_prompt("query.md")


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
