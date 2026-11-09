import requests
from agents import Agent, function_tool
from bs4 import BeautifulSoup

from app.config import get_agent_settings


@function_tool
def url_scrape(url: str) -> str:
    """
    Scrapes a website for it's contents given a url
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        try:
            soup = BeautifulSoup(response.text, "html.parser")

            for script in soup(["script", "style"]):
                script.extract()

            text = soup.get_text(separator=" ", strip=True)

            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            return text[:5000] if len(text) > 5000 else text
        except ImportError:
            return response.text[:5000]
    except Exception as e:  # noqa: BLE001
        return f"Failed to scrape content from {url}: {e!s}"


from pathlib import Path

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "search.md"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SEARCH_AGENT_PROMPT = f.read()


model, settings = get_agent_settings("SEARCH_AGENT", "gpt-4o-mini")

search_agent = Agent(
    name="Search Agent",
    instructions=SEARCH_AGENT_PROMPT,
    tools=[url_scrape],
    model=model,
    model_settings=settings,
)
