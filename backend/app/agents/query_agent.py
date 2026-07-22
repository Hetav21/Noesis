from agents import Agent
from pydantic import BaseModel
from app.config import get_agent_settings


QUERY_AGENT_PROMPT = """You are a helpful assistant that can generate search queries for research.
For each query, follow these steps:

1. First, think through and explain:
   - Break down the key aspects that need to be researched
   - Consider potential challenges and how you'll address them
   - Explain your strategy for finding comprehensive information

2. Then generate 3 search queries that:
   - Are specific and focused on retrieving high-quality information
   - Cover different aspects of the topic
   - Will help find relevant and diverse information

Always provide both your thinking process and the generated queries.
"""

class QueryResponse(BaseModel):
    queries: list[str]
    thoughts: str

model, settings = get_agent_settings("QUERY_AGENT", "gpt-4o-mini")

query_agent = Agent(
    name="Query Generator Agent",
    instructions=QUERY_AGENT_PROMPT,
    output_type=QueryResponse,
    model=model,
    model_settings=settings
)

