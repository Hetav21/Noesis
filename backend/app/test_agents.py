import os

# Set env settings before importing the agents so they load config
os.environ["QUERY_AGENT_MODEL"] = "gpt-4o"
os.environ["QUERY_AGENT_TEMPERATURE"] = "0.15"

from app.agents.query_agent import query_agent

def test_query_agent():
    assert query_agent.model == "gpt-4o"
    assert query_agent.model_settings.temperature == 0.15
    print("Query agent configured correctly!")

if __name__ == "__main__":
    test_query_agent()
