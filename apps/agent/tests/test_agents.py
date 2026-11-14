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

    # Test representative source selection across iterations
    # Create 30 sources: 15 from iteration 1, 10 from iteration 2, 5 from iteration 3
    sources = []
    for i in range(15):
        sources.append(SearchResult(
            title=f"Source Iter1-{i}",
            url=f"https://source1-{i}.org/page",
            summary=f"Substantial technical summary for source {i} in round 1.",
            iteration=1,
        ))
    for i in range(10):
        sources.append(SearchResult(
            title=f"Source Iter2-{i}",
            url=f"https://source2-{i}.org/page",
            summary=f"Substantial technical summary for source {i} in round 2.",
            iteration=2,
        ))
    for i in range(5):
        sources.append(SearchResult(
            title=f"Source Iter3-{i}",
            url=f"https://source3-{i}.org/page",
            summary=f"Substantial technical summary for source {i} in round 3.",
            iteration=3,
        ))

    # For depth=3, max_synthesis_sources = min(30, max(10, 3 * 7)) = 21
    max_synthesis = min(len(sources), max(10, wf.depth * 7))
    assert max_synthesis == 21

    by_iteration = {}
    for item in sources:
        by_iteration.setdefault(item.iteration, []).append(item)

    selected = []
    iter_queues = [list(q) for q in by_iteration.values()]
    while len(selected) < max_synthesis and any(iter_queues):
        for q in iter_queues:
            if q and len(selected) < max_synthesis:
                selected.append(q.pop(0))

    assert len(selected) == 21
    iterations_in_selection = {item.iteration for item in selected}
    # All 3 iterations MUST be represented
    assert iterations_in_selection == {1, 2, 3}
    iter3_count = sum(1 for item in selected if item.iteration == 3)
    assert iter3_count == 5  # All 5 available from iteration 3 got selected


if __name__ == "__main__":
    test_agents()
    test_research_workflow_config_and_cleaning()
    test_url_normalization_and_representative_selection()

