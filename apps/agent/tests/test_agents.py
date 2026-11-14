import asyncio
import os
from unittest.mock import patch

import pytest

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

    quoted = wf._clean_search_query('"Bun Node.js HTTP throughput benchmark real world"')
    assert quoted == "Bun Node.js HTTP throughput benchmark real world"
    assert '"' not in quoted

    smart_quoted = wf._clean_search_query('“Bun vs Node.js production deployment”')
    assert smart_quoted == "Bun vs Node.js production deployment"
    assert '“' not in smart_quoted and '”' not in smart_quoted


@pytest.mark.asyncio
async def test_url_normalization_and_representative_selection():
    from app.services.research import ResearchWorkflow, SearchResult

    wf = ResearchWorkflow(
        query="Quantum Computing Architecture",
        log_callback=None,
        depth=5,
        breadth=4,
    )

    # Test URL normalization
    url1 = "HTTPS://Example.COM:8080/API/Path?Query=Val#Anchor"
    normalized = wf._normalize_url(url1)
    assert normalized == "https://example.com:8080/API/Path?Query=Val#Anchor"
    # Preserves case of path and query, lowercases scheme and host
    assert "/API/Path" in normalized
    assert "Query=Val" in normalized

    # Test triage statement rejection and seen_urls failure retry:
    # URL first fails validation (triage statement), second attempt succeeds
    triage_failed = SearchResult(
        title="Doc 1 Triage Rejection",
        url="https://example.com/paperA",
        summary="Source does not contain substantive findings on the topic.",
        iteration=1,
        query="Round1_Query1",
    )
    succeeded_result = SearchResult(
        title="Doc 1 Success",
        url="https://example.com/paperA",
        summary="A comprehensive overview of superconducting qubits and circuit architectures.",
        iteration=2,
        query="Round2_Query1",
    )

    # 2 rounds, each with 4 queries, 10 sources per query = 80 total sources
    sources = [triage_failed, succeeded_result]
    for round_num in (1, 2):
        for q_idx in range(1, 5):
            query_name = f"Round{round_num}_Query{q_idx}"
            for s_idx in range(10):
                sources.append(SearchResult(
                    title=f"Source {query_name}_{s_idx}",
                    url=f"https://source-{round_num}-{q_idx}-{s_idx}.org/page",
                    summary=f"Technical findings for {query_name} item {s_idx} with rigorous empirical data.",
                    iteration=round_num,
                    query=query_name,
                ))

    wf.search_results = sources

    captured_input = None

    async def mock_runner_run(agent, input):
        nonlocal captured_input
        captured_input = input
        class MockResult:
            final_output = "# Final Report\n\nContent synthesized successfully."
        return MockResult()

    with patch("agents.Runner.run", side_effect=mock_runner_run):
        output = await wf.synthesis_report()

    assert output == "# Final Report\n\nContent synthesized successfully."
    assert captured_input is not None

    # Triage statement should NOT be in the synthesized sources
    assert "Doc 1 Triage Rejection" not in captured_input
    # The valid re-scrape of the same URL MUST be in the synthesized sources
    assert "Doc 1 Success" in captured_input

    # All 8 queries across both rounds MUST be represented in the production selection
    expected_queries = [
        "Round1_Query1", "Round1_Query2", "Round1_Query3", "Round1_Query4",
        "Round2_Query1", "Round2_Query2", "Round2_Query3", "Round2_Query4",
    ]
    for q in expected_queries:
        assert q in captured_input


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


@pytest.mark.asyncio
async def test_cascading_filtering_and_token_budgeting():
    from app.services.research import ResearchWorkflow, SearchResult

    wf = ResearchWorkflow(
        query="Distributed Systems Consensus",
        log_callback=None,
        depth=3,
        breadth=5,
    )

    # 1. Test _is_valid_summary (Tier 2 & Tier 3 filtering)
    assert not wf._is_valid_summary("too short")
    assert not wf._is_valid_summary("Error: Failed to scrape content from url")
    assert not wf._is_valid_summary("Source does not contain substantive findings on the topic.")
    assert wf._is_valid_summary("Raft provides consensus via leader election, log replication, and safety invariants across distributed cluster nodes.")

    # 2. Test token estimation
    sample_text = "a" * 400
    assert wf._estimate_tokens(sample_text) == 100

    # 3. Test token budget ceiling in synthesis
    # Create 30 sources with large summaries that would exceed 15,000 tokens
    large_sources = [
        SearchResult(
            title=f"Paxos Consensus Variant {i}",
            url=f"https://consensus-{i}.org/paper",
            summary="A" * 4000,  # ~1,000 tokens each -> 30 sources = 30,000 tokens
            iteration=1,
            query="paxos consensus",
        )
        for i in range(30)
    ]
    wf.search_results = large_sources

    captured_input = None

    async def mock_runner_run(agent, input):
        nonlocal captured_input
        captured_input = input
        class MockResult:
            final_output = "Report output"
        return MockResult()

    with patch("agents.Runner.run", side_effect=mock_runner_run):
        await wf.synthesis_report()

    assert captured_input is not None
    # Estimated tokens of captured input should not explode past safety budget
    assert len(captured_input) < 70000

    # 4. Test follow-up findings filtering
    triage_failed = SearchResult(
        title="Bad Page",
        url="https://bad.org/page",
        summary="Source does not contain substantive findings on the topic.",
        iteration=1,
        query="bad query",
    )
    good_page = SearchResult(
        title="Good Page",
        url="https://good.org/page",
        summary="Detailed consensus algorithms and benchmark metrics across multi-datacenter clusters.",
        iteration=1,
        query="good query",
    )
    wf.search_results = [triage_failed, good_page]
    captured_followup_input = None

    async def mock_followup_run(agent, input):
        nonlocal captured_followup_input
        captured_followup_input = input
        from app.agents.follow_up_agent import FollowUpDecisionResponse
        class MockResult:
            final_output = FollowUpDecisionResponse(
                should_follow_up=False,
                reasoning="Sufficient research completed.",
                queries=[],
            )
        return MockResult()

    with patch("agents.Runner.run", side_effect=mock_followup_run):
        await wf.generate_followup()

    assert captured_followup_input is not None
    assert "Bad Page" not in captured_followup_input
    assert "Good Page" in captured_followup_input


if __name__ == "__main__":
    test_agents()
    test_research_workflow_config_and_cleaning()
    asyncio.run(test_url_normalization_and_representative_selection())
    asyncio.run(test_cascading_filtering_and_token_budgeting())
    test_prompt_loader()

