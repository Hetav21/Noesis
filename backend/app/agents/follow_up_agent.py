from agents import Agent
from pydantic import BaseModel
from app.config import get_agent_settings


FOLLOW_UP_DECISION_PROMPT = (
    "You are a researcher that decides whether we have enough information to stop "
    "researching or whether we need to generate follow-up queries. "
    "You will be given the original query and summaries of information found so far. "
    
    "IMPORTANT: For simple factual questions (e.g., 'How long do dogs live?', 'What is the height of Mount Everest?'), "
    "if the basic information is already present in the findings, you should NOT request follow-up queries. "
    
    "Complex questions about processes, comparisons, or multifaceted topics may need follow-ups, but simple factual "
    "questions rarely need more than one round of research. "
    
    "If you think we have enough information, return should_follow_up=False. If you think we need to generate follow-up queries, return should_follow_up=True. "
    "If you return True, you will also need to generate 2-3 follow-up queries that address specific gaps in the current findings. "
    "Always provide detailed reasoning for your decision."
)

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
