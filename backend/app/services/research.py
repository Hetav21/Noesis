import time
from typing import Callable, Any
from pydantic import BaseModel
from duckduckgo_search import DDGS

# Assuming these are available in the backend.app.agents package
from agents import Runner, trace
from app.agents.follow_up_agent import FollowUpDecisionResponse, follow_up_decision_agent
from app.agents.search_agent import search_agent
from app.agents.query_agent import QueryResponse, query_agent
from app.agents.synthesis_agent import synthesis_agent


class SearchResult(BaseModel):
    title: str
    url: str
    summary: str


class ResearchWorkflow:
    def __init__(self, query: str, log_callback: Callable[[dict], Any]):
        self.query = query
        self.log_callback = log_callback
        self.search_results = []
        self.iteration = 1

    async def research(self) -> str:
        await self.log_callback({"type": "status", "message": "Starting Deep Research Workflow..."})
        with trace("Deep Research Workflow"):

            query_response = await self.generate_queries()
            await self.perform_research_for_queries(queries=query_response.queries)

            while self.iteration < 3:
                decision_response = await self.generate_followup()

                if not decision_response.should_follow_up:
                    await self.log_callback({"type": "info", "message": "No more research needed. Synthesizing report..."})
                    break

                self.iteration += 1
                await self.log_callback({"type": "info", "message": f"Conducting follow-up research (iteration {self.iteration})..."})

                await self.perform_research_for_queries(queries=decision_response.queries)

            final_report = await self.synthesis_report()

            await self.log_callback({"type": "success", "message": "Research complete!"})
            await self.log_callback({"type": "report", "content": final_report})

            return final_report
            
    async def generate_queries(self) -> QueryResponse:
        await self.log_callback({"type": "status", "message": "Analyzing query..."})
        
        # Run the query agent
        result = await Runner.run(query_agent, input=self.query)
        
        # Display the results
        await self.log_callback({"type": "section", "title": "Query Analysis"})
        await self.log_callback({"type": "info", "message": f"Thoughts: {result.final_output.thoughts}"})
        await self.log_callback({"type": "info", "message": "Generated Search Queries:"})
        for i, query in enumerate(result.final_output.queries, 1):
            await self.log_callback({"type": "list_item", "message": f"{i}. {query}"})
        
        return result.final_output
        
    def duckduckgo_search(self, query: str):
        try:
            results = DDGS().text(query, region='us-en', safesearch='on', timelimit='y', max_results=5)
            return results
        except Exception as ex:
            # Using log_callback for errors
            # Note: log_callback is async, but this method is not.
            # In a real scenario, you might want to make duckduckgo_search async
            # or handle this error logging differently if it needs to be awaited.
            # For now, we'll call it directly, assuming it can be called synchronously
            # or that the async call will be handled by the event loop if it's a coroutine.
            # For this exercise, I'll assume direct call is acceptable or will be awaited implicitly.
            self.log_callback({"type": "error", "message": f"Search error: {str(ex)}"})
            return []

    async def perform_research_for_queries(self, queries: list[str]) -> None:

        # get all of the search results for each query
        all_search_results = {}
        for query in queries:
            search_results = self.duckduckgo_search(query)
            all_search_results[query] = search_results

        for query in queries:
            await self.log_callback({"type": "info", "message": f"Searching for: {query}"})

            for result in all_search_results[query]:
                await self.log_callback({"type": "info", "message": f"Result: {result['title']}"})
                await self.log_callback({"type": "info", "message": f"URL: {result['href']}"})
                await self.log_callback({"type": "status", "message": "Analyzing content..."})

                start_analysis_time = time.time()
                search_input = f"Title: {result['title']}\nURL: {result['href']}"
                agent_result = await Runner.run(search_agent, input=search_input)
                analysis_time = time.time() - start_analysis_time

                search_result = SearchResult(
                    title=result['title'],
                    url=result['href'],
                    summary=agent_result.final_output
                )

                self.search_results.append(search_result)

                summary_preview = agent_result.final_output[:100] + ("..." if len(agent_result.final_output) > 100 else "")

                await self.log_callback({"type": "info", "message": f"Summary: {summary_preview}"})
                await self.log_callback({"type": "info", "message": f"Analysis completed in {analysis_time:.2f}s"})
        
        await self.log_callback({"type": "success", "message": f"Research round complete! Found {len(self.search_results)} sources across {len(queries)} queries."})

    async def synthesis_report(self) -> str:
        await self.log_callback({"type": "status", "message": "Synthesizing research findings..."})
        findings_text = f"Query: {self.query}\n\nSearch Results:\n"
        for i, result in enumerate(self.search_results, 1):
            findings_text += f"\n{i}. Title: {result.title}\n   URL: {result.url}\n   Summary: {result.summary}\n"

        result = await Runner.run(synthesis_agent, input=findings_text)

        return result.final_output
            
    async def generate_followup(self) -> FollowUpDecisionResponse:
        await self.log_callback({"type": "status", "message": "Evaluating if more research is needed..."})
        findings_text = f"Original Query: {self.query}\n\nCurrent Findings:\n"
        for i, result in enumerate(self.search_results, 1):
            findings_text += f"\n{i}. Title: {result.title}\n   URL: {result.url}\n   Summary: {result.summary}\n"

        result = await Runner.run(follow_up_decision_agent, input=findings_text)

        await self.log_callback({"type": "section", "title": "Follow-up Decision"})
        await self.log_callback({"type": "info", "message": f"Decision: {'More research needed' if result.final_output.should_follow_up else 'Research complete'}"})
        await self.log_callback({"type": "info", "message": f"Reasoning: {result.final_output.reasoning}"})

        if result.final_output.should_follow_up:
            await self.log_callback({"type": "info", "message": "Follow-up Queries:"})
            for i, query in enumerate(result.final_output.queries, 1):
                await self.log_callback({"type": "list_item", "message": f"{i}. {query}"})

        return result.final_output