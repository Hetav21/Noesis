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


def test_url_normalization_and_representative_selection():
    from app.services.research import ResearchWorkflow, SearchResult

    wf = ResearchWorkflow(
        query="Quantum Computing Architecture",
        log_callback=None,
        depth=3,
        breadth=4,
    )

    # Test URL normalization
    url1 = "HTTPS://Example.COM:8080/API/Path?Query=Val#Anchor"
    normalized = wf._normalize_url(url1)
    assert normalized == "https://example.com:8080/API/Path?Query=Val#Anchor"
    # Preserves case of path and query, lowercases scheme and host
    assert "/API/Path" in normalized
    assert "Query=Val" in normalized

    # Test seen_urls with failure retry:
    # URL first fails validation, second attempt succeeds
    failed_result = SearchResult(
        title="Doc 1 Failed",
        url="https://example.com/paperA",
        summary="failed to scrape content from web page",
        iteration=1,
    )
    succeeded_result = SearchResult(
        title="Doc 1 Success",
        url="https://example.com/paperA",
        summary="A comprehensive overview of superconducting qubits and circuit architectures.",
        iteration=2,
    )

    wf.search_results = [failed_result, succeeded_result]
    valid_results = []
    seen = set()
    for res in wf.search_results:
        clean_url = wf._normalize_url(res.url)
        if clean_url in seen:
            continue
        if len(res.summary.strip()) < 30 or "failed to scrape content" in res.summary.lower():
            continue
        seen.add(clean_url)
        valid_results.append(res)

    assert len(valid_results) == 1
    assert valid_results[0].title == "Doc 1 Success"
    assert valid_results[0].iteration == 2

    # Test representative source selection across both iterations and queries within each round
    # Scenario matching CodeRabbit review:
    # 2 rounds, each with 4 queries, 10 sources per query = 80 total sources
    sources = []
    for round_num in (1, 2):
        for q_idx in range(1, 5):
            query_name = f"Round{round_num}_Query{q_idx}"
            for s_idx in range(10):
                sources.append(SearchResult(
                    title=f"Source {query_name}_{s_idx}",
                    url=f"https://source-{round_num}-{q_idx}-{s_idx}.org/page",
                    summary=f"Technical findings for {query_name} item {s_idx}.",
                    iteration=round_num,
                    query=query_name,
                ))

    # Capped at 35 sources
    max_synthesis = 35

    by_round_and_query = {}
    for item in sources:
        by_round_and_query.setdefault((item.iteration, item.query), []).append(item)

    selected = []
    query_queues = [list(q) for q in by_round_and_query.values()]
    while len(selected) < max_synthesis and any(query_queues):
        for q in query_queues:
            if q and len(selected) < max_synthesis:
                selected.append(q.pop(0))

    assert len(selected) == 35
    # Verify that EVERY query across BOTH rounds is represented
    represented_queries = {item.query for item in selected}
    expected_queries = {
        "Round1_Query1", "Round1_Query2", "Round1_Query3", "Round1_Query4",
        "Round2_Query1", "Round2_Query2", "Round2_Query3", "Round2_Query4",
    }
    assert represented_queries == expected_queries
    # Each query gets 4 or 5 sources (35 / 8 = 4 remainder 3)
    for q in expected_queries:
        count = sum(1 for item in selected if item.query == q)
        assert count in (4, 5)


def test_prompt_loader():
    from app.services.prompt_loader import load_system_prompt, render_user_prompt

    # Test system prompt loading
    sys_query = load_system_prompt("query.md")
    assert "Identity & Core Purpose" in sys_query
    assert "Negative Constraints & Guardrails" in sys_query

    sys_synthesis = load_system_prompt("synthesis.md")
    assert "Identity & Core Purpose" in sys_synthesis
    assert "Prompt Injection Defense" in sys_synthesis

    # Test user prompt template rendering
    rendered_query = render_user_prompt("query.md", {
        "topic": "Superconducting Qubits",
        "breadth": 4,
        "target_query_count": 4,
    })
    assert "<research_inquiry>" in rendered_query
    assert "Superconducting Qubits" in rendered_query
    assert "<target_query_count>4</target_query_count>" in rendered_query

    rendered_synthesis = render_user_prompt("synthesis.md", {
        "topic": "Superconducting Qubits",
        "depth": 3,
        "breadth": 6,
        "scope_desc": "Comprehensive Technical Investigation",
        "scope_directives": "Detailed whitepaper with benchmarks",
        "source_count": 2,
        "sources_block": "1. Paper A\n2. Paper B",
    })
    assert "<research_inquiry>" in rendered_synthesis
    assert "Comprehensive Technical Investigation" in rendered_synthesis
    assert "<formatting_reminder>" in rendered_synthesis
    assert "1. Paper A\n2. Paper B" in rendered_synthesis


if __name__ == "__main__":
    test_agents()
    test_research_workflow_config_and_cleaning()
    test_url_normalization_and_representative_selection()
    test_prompt_loader()

