from agents import Agent
from pydantic import BaseModel
from app.config import get_agent_settings
from pathlib import Path

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "follow_up.md"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    FOLLOW_UP_DECISION_PROMPT = f.read()

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
