"""Gemini-based pagination detection for unusual sites."""

import google.generativeai as genai
import instructor
from urllib.parse import urljoin
from pydantic import BaseModel, Field
from config import settings
from models import PaginationResult
from utils.logger import get_logger

log = get_logger("pagination_ai")


class PaginationAnalysis(BaseModel):
    """AI-detected pagination pattern."""
    has_pagination: bool = Field(description="Whether the page has pagination")
    next_page_urls: list[str] = Field(default_factory=list, description="Detected next page URLs")
    pattern_description: str = Field(default="", description="Description of the pagination pattern")


def ai_detect_pagination(
    url: str,
    markdown: str,
    num_pages: int = 3,
    links: dict | None = None,
    heuristic_pattern: str | None = None,
) -> PaginationResult:
    """Use Gemini to detect pagination from page content."""

    if not markdown:
        return PaginationResult(urls=[url], pattern="no content", method="ai_fallback")

    genai.configure(api_key=settings.GEMINI_API_KEY)
    client = instructor.from_gemini(
        client=genai.GenerativeModel(model_name=f"models/{settings.GEMINI_MODEL}"),
        mode=instructor.Mode.GEMINI_JSON,
    )

    # Build links section from crawl4ai structured links
    links_section = ""
    if links:
        internal = links.get("internal", [])
        pagination_keywords = {"next", "page", "→", ">", "»", "load more", "show more"}
        candidates = [
            f"  {lnk.get('href','')}  [{lnk.get('text','')}]"
            for lnk in internal
            if any(kw in (lnk.get("text", "") + lnk.get("href", "")).lower() for kw in pagination_keywords)
        ]
        if candidates:
            links_section = "\n\nCrawl4AI discovered these pagination-candidate links:\n" + "\n".join(candidates[:30])

    heuristic_section = ""
    if heuristic_pattern:
        heuristic_section = f"\n\nHeuristic code detected pattern: {heuristic_pattern!r} (may be speculative)"

    prompt = f"""You are analyzing a web page to find its pagination mechanism.

URL: {url}
{heuristic_section}
{links_section}

Full page content:
{markdown}

Task:
1. Identify if this page has pagination (Next button, page numbers, load-more, offset params, etc.)
2. If yes, return the URLs for pages 2 through {num_pages}
3. If no real pagination found, set has_pagination=false

Output ONLY valid JSON matching this schema:
{{"has_pagination": bool, "next_page_urls": [list of URL strings], "pattern_description": "short description"}}"""

    try:
        result = client.create(
            response_model=PaginationAnalysis,
            messages=[{"role": "user", "content": prompt}],
            generation_config={"temperature": settings.GEMINI_TEMP_STRICT},
        )

        if result.has_pagination and result.next_page_urls:
            resolved = [urljoin(url, u) for u in result.next_page_urls[:num_pages - 1]]
            urls = [url] + resolved
            log.info(f"AI detected pagination: {result.pattern_description}")
            return PaginationResult(
                urls=urls,
                pattern=result.pattern_description,
                method="ai_fallback",
            )

    except Exception as e:
        log.warning(f"AI pagination detection failed: {e}")

    return PaginationResult(urls=[url], pattern="none detected", method="ai_fallback")
