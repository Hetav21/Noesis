import os

# Set env settings before importing the agents
os.environ["QUERY_AGENT_MODEL"] = "gpt-4o"
os.environ["QUERY_AGENT_TEMPERATURE"] = "0.15"
os.environ["SEARCH_AGENT_MODEL"] = "gpt-custom-search"
os.environ["SEARCH_AGENT_MAX_TOKENS"] = "500"
os.environ["FOLLOW_UP_AGENT_MODEL"] = "gpt-custom-followup"
os.environ["FOLLOW_UP_AGENT_TOP_P"] = "0.99"
os.environ["SYNTHESIS_AGENT_MODEL"] = "gpt-custom-synthesis"
os.environ["SYNTHESIS_AGENT_TOP_K"] = "30"

from app.agents.follow_up_agent import follow_up_decision_agent
from app.agents.query_agent import query_agent
from app.agents.search_agent import search_agent
from app.agents.synthesis_agent import synthesis_agent


def test_agents():
    assert query_agent.model == "gpt-4o"
    assert query_agent.model_settings.temperature == 0.15

    assert search_agent.model == "gpt-custom-search"
    assert search_agent.model_settings.max_tokens == 500

    assert follow_up_decision_agent.model == "gpt-custom-followup"
    assert follow_up_decision_agent.model_settings.top_p == 0.99

    assert synthesis_agent.model == "gpt-custom-synthesis"
    assert synthesis_agent.model_settings.extra_args == {"top_k": 30}
    print("All agents configured correctly!")


def test_research_workflow_config_and_cleaning():
    from app.services.research import ResearchWorkflow

    wf = ResearchWorkflow(
        query="What are the potential ethical implications of future AI advancements?",
        log_callback=None,
        depth=5,
        breadth=10,
    )
    assert wf.depth == 5
    assert wf.breadth == 10
    assert wf.max_iterations == 6
    assert wf.max_results_per_query == 10

    cleaned = wf._clean_search_query("What are the potential ethical implications of future AI advancements?")
    assert cleaned == "potential ethical implications of future AI advancements"
    assert "what are" not in cleaned.lower()

    how_cleaned = wf._clean_search_query("How do leading experts predict AI will influence job markets?")
    assert how_cleaned == "leading experts predict AI will influence job markets"


if __name__ == "__main__":
    test_agents()
    test_research_workflow_config_and_cleaning()

