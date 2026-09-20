"""LangChain tools the gym enrichment agent can call autonomously."""

import os
import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from pydantic import BaseModel, Field


_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VitroFitGymAgent/2.0; +http://localhost)"
}
_MAX_SITE_TEXT_CHARS = 6000
_SCRAPE_TIMEOUT = float(os.getenv("AGENT_SCRAPE_TIMEOUT", "10"))


# ── Tool 1: Website Scraper ──────────────────────────────────────────────


class ScrapeInput(BaseModel):
    url: str = Field(description="The full URL of the gym's website to scrape")


@tool(args_schema=ScrapeInput)
async def scrape_gym_website(url: str) -> str:
    """Scrape a gym's website to extract visible text content about equipment, classes,
    facilities, and services. Use this when you have the gym's website URL."""
    if not url:
        return "Error: No URL provided."
    if not url.startswith("http"):
        url = f"https://{url}"
    try:
        async with httpx.AsyncClient(
            headers=_HTTP_HEADERS,
            timeout=_SCRAPE_TIMEOUT,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.TimeoutException:
        return f"Error: Website at {url} timed out after {_SCRAPE_TIMEOUT}s."
    except httpx.HTTPStatusError as e:
        return f"Error: Website returned HTTP {e.response.status_code}."
    except Exception as e:
        return f"Error: Could not reach {url} — {type(e).__name__}"

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        if not text:
            return "Error: Website returned no readable text content."
        return text[:_MAX_SITE_TEXT_CHARS]
    except Exception:
        return "Error: Could not parse the website HTML."


# ── Tool 2: Web Search ──────────────────────────────────────────────────


class SearchGymInput(BaseModel):
    query: str = Field(
        description="Search query about the gym, e.g. 'FitZone Colombo gym equipment classes reviews'"
    )


@tool(args_schema=SearchGymInput)
async def search_gym_info(query: str) -> str:
    """Search the web for information about a gym's equipment, classes, and reviews.
    Use this when the gym's website is unavailable or doesn't have enough info.
    Formulate a specific search query including the gym name and city."""
    try:
        from langchain_tavily import TavilySearch

        tavily = TavilySearch(max_results=3, search_depth="advanced")
        results = await tavily.ainvoke({"query": query})
        result_list = results.get("results", []) if isinstance(results, dict) else results
        if isinstance(result_list, list):
            return "\n\n".join(
                f"Source: {r.get('url', 'unknown')}\n{r.get('content', '')}"
                for r in result_list
            )
        return str(results)
    except Exception as e:
        return (
            f"Web search unavailable: {e}. "
            "Try using the scrape_gym_website tool instead if a URL is available."
        )


# ── Tool 3: Similar Gym Lookup (RAG) ────────────────────────────────────


@tool
def lookup_similar_gyms(gym_name: str, city: str) -> str:
    """Look up previously enriched gyms in the database that are similar to this one.
    Useful for inferring equipment/classes when no website data is available.
    Returns equipment and classes from similar gyms as reference."""
    try:
        from vectorstore import find_similar_gyms

        docs = find_similar_gyms(gym_name, city, k=3)
        if not docs:
            return "No similar gyms found in the database yet."
        results = []
        for doc in docs:
            results.append(
                f"Similar gym: {doc.metadata.get('name', 'Unknown')}\n"
                f"Address: {doc.metadata.get('address', 'Unknown')}\n"
                f"Data: {doc.page_content}"
            )
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"Database lookup failed: {e}"


# ── Expose all tools ────────────────────────────────────────────────────


def get_all_tools() -> list:
    """Return all tools available to the enrichment agent."""
    return [scrape_gym_website, search_gym_info, lookup_similar_gyms]

