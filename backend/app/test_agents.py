import os

# Set env settings before importing the agents
os.environ["QUERY_AGENT_MODEL"] = "gpt-4o"
os.environ["QUERY_AGENT_TEMPERATURE"] = "0.15"
os.environ["SEARCH_AGENT_MODEL"] = "gpt-custom-search"
os.environ["SEARCH_AGENT_MAX_TOKENS"] = "500"

from app.agents.query_agent import query_agent
from app.agents.search_agent import search_agent

def test_agents():
    assert query_agent.model == "gpt-4o"
    assert query_agent.model_settings.temperature == 0.15
    
    assert search_agent.model == "gpt-custom-search"
    assert search_agent.model_settings.max_tokens == 500
    print("Query and Search agents configured correctly!")

if __name__ == "__main__":
    test_agents()

