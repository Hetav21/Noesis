from pathlib import Path

from agents import Agent
from pydantic import BaseModel

from app.config import get_agent_settings
from app.services.prompt_loader import load_system_prompt

FOLLOW_UP_DECISION_PROMPT = load_system_prompt("follow_up.md")


class FollowUpDecisionResponse(BaseModel):
    should_follow_up: bool
    reasoning: str
    queries: list[str]


model, settings = get_agent_settings("FOLLOW_UP_AGENT", "gpt-4o-mini")

follow_up_decision_agent = Agent(
    name="Follow-up Decision Agent",
    instructions=FOLLOW_UP_DECISION_PROMPT,
    output_type=FollowUpDecisionResponse,
    model=model,
    model_settings=settings,
)
