import asyncio
import time
import urllib.parse
from collections.abc import Callable
from typing import Any

# Assuming these are available in the backend.app.agents package
from agents import Runner, trace
from ddgs import DDGS
from pydantic import BaseModel

from app.agents.follow_up_agent import (
    FollowUpDecisionResponse,
    follow_up_decision_agent,
)
from app.agents.query_agent import QueryResponse, query_agent
from app.agents.search_agent import search_agent
from app.agents.synthesis_agent import synthesis_agent
from app.services.prompt_loader import render_user_prompt


class SearchResult(BaseModel):
    title: str
    url: str
    summary: str
    iteration: int = 1
    query: str = ""


class ResearchWorkflow:
    def __init__(
        self,
        query: str,
        log_callback: Callable[[dict], Any],
        depth: int = 2,
        breadth: int = 4,
    ):
        self.query = query
        self.log_callback = log_callback
        self.depth = max(1, min(5, depth))
        self.breadth = max(2, min(10, breadth))
        self.search_results = []
        self.iteration = 1
        # Validate and clamp config values
        self.max_iterations = self.depth + 1  # depth 1-5 -> iterations 2-6
        self.max_results_per_query = self.breadth  # breadth 2-10

    async def _log(self, entry: dict):
        if self.log_callback:
            try:
                res = self.log_callback(entry)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:  # noqa: BLE001
                print(f"Log callback error: {e}")

    async def research(self) -> str:
        await self._log({"type": "status", "message": "Starting research workflow..."})
        with trace("Noesis Research Workflow"):
            query_response = await self.generate_queries()
            await self.perform_research_for_queries(queries=query_response.queries)

            while self.iteration < self.max_iterations:
                decision_response = await self.generate_followup()

                if not decision_response.should_follow_up:
                    await self._log(
                        {
                            "type": "info",
                            "message": "No more research needed. Synthesizing report...",
                        }
                    )
                    break

                self.iteration += 1
                await self._log(
                    {
                        "type": "info",
                        "message": f"Conducting follow-up research (iteration {self.iteration} of {self.max_iterations - 1})...",
                    }
                )

                await self.perform_research_for_queries(
                    queries=decision_response.queries
                )

            final_report = await self.synthesis_report()

            await self._log({"type": "success", "message": "Research complete!"})
            await self._log({"type": "report", "content": final_report})

            return final_report

    async def generate_queries(self) -> QueryResponse:
        await self._log({"type": "status", "message": "Analyzing query..."})

        # Run the query agent with user research topic and breadth
        target_query_count = max(3, min(6, self.breadth))
        query_input = render_user_prompt(
            "query.md",
            {
                "topic": self.query,
                "breadth": self.breadth,
                "depth": self.depth,
                "target_query_count": target_query_count,
            },
        )
        result = await Runner.run(query_agent, input=query_input)

        # Display the results
        await self._log({"type": "section", "title": "Query Analysis"})
        await self._log(
            {"type": "info", "message": f"Thoughts: {result.final_output.thoughts}"}
        )
        await self._log({"type": "info", "message": "Generated Search Queries:"})
        for i, query in enumerate(result.final_output.queries, 1):
            await self._log({"type": "list_item", "message": f"{i}. {query}"})

        return result.final_output

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for deduplication by lowercasing scheme and netloc while preserving path and query case."""
        try:
            parts = urllib.parse.urlsplit(url.strip())
            return urllib.parse.urlunsplit((
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path,
                parts.query,
                parts.fragment,
            ))
        except Exception:
            return url.strip()

    def _clean_search_query(self, query: str) -> str:
        """Strip conversational questions and stop-word prefixes for search engine relevance."""
        import re
        q = query.strip()
        # Remove conversational question starters
        q = re.sub(
            r"^(what\s+(is|are|was|were|will|can)|how\s+(do|does|can|will|should)|why\s+(do|does|is|are)|when\s+(will|did)|can\s+you\s+(find|search|tell))\s+",
            "",
            q,
            flags=re.IGNORECASE,
        )
        q = re.sub(r"^(what|how|why|where)\s+", "", q, flags=re.IGNORECASE)
        q = re.sub(r"^(the|a|an)\s+", "", q, flags=re.IGNORECASE)
        # Strip trailing punctuation and question marks
        q = re.sub(r"[?!.]+$", "", q).strip()
        # If query became too short, fallback to original query stripped of punctuation
        if len(q.split()) < 2:
            q = re.sub(r"[?!.]+$", "", query).strip()
        return q

    def _sync_ddgs_search(self, query: str):
        blocked_domains = [
            "baidu.com",
            "zhihu.com",
            "zhidao.baidu.com",
            "jingyan.baidu.com",
            "symbolab.com",
            "wordreference.com",
            "cpsenglish.com",
            "ell.stackexchange.com",
            "forum.wordreference.com",
            # Block generic dictionary / thesaurus definitions that hijack search keywords
            "merriam-webster.com",
            "dictionary.cambridge.org",
            "dictionary.com",
            "thesaurus.com",
            "thefreedictionary.com",
            "vocabulary.com",
            "collinsdictionary.com",
            "definitions.net",
            "wiktionary.org",
            "usdictionary.com",
            # Block unrelated betting / entertainment aggregators that match 'prediction' or artist names
            "forebet.com",
            "predictz.com",
            "footballpredictions.com",
            "pickswise.com",
            "dimers.com",
            "ticketmaster.com",
            "genius.com",
        ]
        blocked_tlds = [".cn", ".jp", ".kr", ".ru"]

        cleaned_query = self._clean_search_query(query)

        # Backends to try:
        # 1. "yahoo": fast, highly reliable across cloud datacenter IPs, returns authoritative web articles.
        # 2. None (ddgs auto multi-engine pool): queries across available engines as fallback.
        backends_to_try: list[str | None] = ["yahoo", None]
        results: list[dict[str, Any]] = []
        last_err: Exception | None = None

        for backend in backends_to_try:
            for attempt in range(2):
                try:
                    kwargs: dict[str, Any] = {
                        "max_results": self.max_results_per_query * 3,
                    }
                    if backend:
                        kwargs["backend"] = backend

                    res = DDGS().text(cleaned_query, **kwargs)
                    if res:
                        results = list(res)
                        break
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    time.sleep(0.4 * (attempt + 1))
                    continue
            if results:
                break

        # If cleaned query had no results, attempt with raw query once
        if not results and cleaned_query != query:
            try:
                res = DDGS().text(query, backend="yahoo", max_results=self.max_results_per_query * 3)
                if res:
                    results = list(res)
            except Exception as e:  # noqa: BLE001
                last_err = e

        if not results and last_err:
            raise last_err

        filtered_results = []
        seen_urls = set()
        for r in results:
            raw_url = r.get("href", "")
            if not raw_url:
                continue
            normalized_url = self._normalize_url(raw_url)
            if normalized_url in seen_urls:
                continue
            url_lower = raw_url.lower()
            if any(domain in url_lower for domain in blocked_domains):
                continue
            if any(url_lower.endswith(tld) or f"{tld}/" in url_lower for tld in blocked_tlds):
                continue
            seen_urls.add(normalized_url)
            filtered_results.append(r)
            if len(filtered_results) >= self.max_results_per_query:
                break

        return (
            filtered_results
            if filtered_results
            else results[: self.max_results_per_query]
        )

    async def duckduckgo_search(self, query: str):
        try:
            return await asyncio.to_thread(self._sync_ddgs_search, query)
        except Exception as ex:  # noqa: BLE001
            await self._log(
                {"type": "error", "message": f"Search error for '{query}': {ex!s}"}
            )
            return []

    async def perform_research_for_queries(self, queries: list[str]) -> None:
        # get all of the search results for each query
        all_search_results = {}
        for query in queries:
            search_results = await self.duckduckgo_search(query)
            all_search_results[query] = search_results

        for query in queries:
            results_for_query = all_search_results.get(query, [])
            await self._log({"type": "info", "message": f"Searching for: {query}"})

            if not results_for_query:
                await self._log(
                    {
                        "type": "warning",
                        "message": f"No search results returned for: {query}",
                    }
                )
                continue

            for result in results_for_query:
                await self._log(
                    {"type": "info", "message": f"Result: {result['title']}"}
                )
                await self._log({"type": "info", "message": f"URL: {result['href']}"})
                await self._log({"type": "status", "message": "Analyzing content..."})

                start_analysis_time = time.time()
                search_input = render_user_prompt(
                    "search.md",
                    {
                        "topic": self.query,
                        "title": result["title"],
                        "url": result["href"],
                    },
                )
                agent_result = await Runner.run(search_agent, input=search_input)
                analysis_time = time.time() - start_analysis_time

                search_result = SearchResult(
                    title=result["title"],
                    url=result["href"],
                    summary=agent_result.final_output,
                    iteration=self.iteration,
                    query=query,
                )

                self.search_results.append(search_result)

                summary_preview = agent_result.final_output[:100] + (
                    "..." if len(agent_result.final_output) > 100 else ""
                )

                await self._log(
                    {"type": "info", "message": f"Summary: {summary_preview}"}
                )
                await self._log(
                    {
                        "type": "info",
                        "message": f"Analysis completed in {analysis_time:.2f}s",
                    }
                )

        await self._log(
            {
                "type": "success",
                "message": f"Research round complete! Found {len(self.search_results)} sources across {len(queries)} queries.",
            }
        )

    async def synthesis_report(self) -> str:
        await self._log(
            {"type": "status", "message": "Synthesizing research findings..."}
        )

        def _is_valid_summary(text: str) -> bool:
            clean = text.strip().lower()
            return (
                len(clean) >= 30
                and "failed to scrape content" not in clean
                and "does not contain substantive findings" not in clean
            )

        # Deduplicate and prioritize sources with substantial summaries
        valid_results: list[SearchResult] = []
        seen_urls = set()
        for res in self.search_results:
            clean_url = self._normalize_url(res.url)
            if clean_url in seen_urls:
                continue
            # Filter out error messages, empty summaries, or triage rejections
            if not _is_valid_summary(res.summary):
                continue
            seen_urls.add(clean_url)
            valid_results.append(res)

        # If too few valid sources survived filtering, use all available search results
        sources_to_synthesize = valid_results if valid_results else self.search_results

        # Cap the number of synthesized sources to prevent context saturation
        # Quick (depth 1): up to 12 sources
        # Medium (depth 2): up to 20 sources
        # Deep (depth 3-5): up to 35 sources
        max_synthesis_sources = min(len(sources_to_synthesize), max(10, self.depth * 7))

        if len(sources_to_synthesize) <= max_synthesis_sources:
            selected_sources = list(sources_to_synthesize)
        else:
            # Group sources by (iteration, query) to ensure representative selection across rounds and search vectors
            by_round_and_query: dict[tuple[int, str], list[SearchResult]] = {}
            for item in sources_to_synthesize:
                by_round_and_query.setdefault((item.iteration, item.query), []).append(item)

            selected_sources: list[SearchResult] = []
            query_queues = [list(q) for q in by_round_and_query.values()]
            while len(selected_sources) < max_synthesis_sources and any(query_queues):
                for q in query_queues:
                    if q and len(selected_sources) < max_synthesis_sources:
                        selected_sources.append(q.pop(0))

        if self.depth <= 1:
            scope_desc = "Quick Overview (Target: 4-5 focused sections, key findings, and direct answers)"
            scope_directives = (
                "Target 4-5 focused sections, concise key takeaways, and direct answers without exhaustive depth."
            )
        elif self.depth == 2:
            scope_desc = "Standard Deep Dive (Target: 5-6 detailed sections with technical nuance)"
            scope_directives = (
                "Target 5-6 detailed sections with technical nuance, architectural mechanisms, and benchmark comparisons."
            )
        else:
            scope_desc = f"Comprehensive Technical Investigation (Target: Exhaustive multi-section whitepaper, deep architectural analysis, empirical comparisons, and future outlook - Depth {self.depth}, Breadth {self.breadth})"
            scope_directives = (
                "Write an exhaustive, deeply technical whitepaper covering underlying architectures, empirical comparisons, trade-offs, edge cases, implementation nuances, and future outlook."
            )

        sources_block = "\n".join(
            f"{i}. Title: {result.title}\n   URL: {result.url}\n   Summary: {result.summary}"
            for i, result in enumerate(selected_sources, 1)
        )

        findings_text = render_user_prompt(
            "synthesis.md",
            {
                "topic": self.query,
                "depth": self.depth,
                "breadth": self.breadth,
                "scope_desc": scope_desc,
                "scope_directives": scope_directives,
                "source_count": len(selected_sources),
                "sources_block": sources_block,
            },
        )

        result = await Runner.run(synthesis_agent, input=findings_text)

        return result.final_output

    async def generate_followup(self) -> FollowUpDecisionResponse:
        await self._log(
            {"type": "status", "message": "Evaluating if more research is needed..."}
        )
        # Give follow-up agent progress context: iteration vs target depth
        recent_results = self.search_results[-20:]
        recent_findings_text = "\n".join(
            f"{i}. Title: {result.title}\n   URL: {result.url}\n   Summary: {result.summary}"
            for i, result in enumerate(recent_results, 1)
        )
        findings_text = render_user_prompt(
            "follow_up.md",
            {
                "topic": self.query,
                "iteration": self.iteration,
                "depth": self.depth,
                "total_sources": len(self.search_results),
                "recent_findings": recent_findings_text,
            },
        )

        result = await Runner.run(follow_up_decision_agent, input=findings_text)

        await self._log({"type": "section", "title": "Follow-up Decision"})
        await self._log(
            {
                "type": "info",
                "message": f"Decision: {'More research needed' if result.final_output.should_follow_up else 'Research complete'}",
            }
        )
        await self._log(
            {"type": "info", "message": f"Reasoning: {result.final_output.reasoning}"}
        )

        if result.final_output.should_follow_up:
            await self._log({"type": "info", "message": "Follow-up Queries:"})
            for i, query in enumerate(result.final_output.queries, 1):
                await self._log({"type": "list_item", "message": f"{i}. {query}"})

        return result.final_output
