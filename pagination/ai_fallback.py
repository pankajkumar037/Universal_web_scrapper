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


def ai_detect_pagination(url: str, markdown: str, num_pages: int = 3) -> PaginationResult:
    """Use Gemini to detect pagination from page content."""

    if not markdown:
        return PaginationResult(urls=[url], pattern="no content", method="ai_fallback")

    genai.configure(api_key=settings.GEMINI_API_KEY)
    client = instructor.from_gemini(
        client=genai.GenerativeModel(model_name=f"models/{settings.GEMINI_MODEL}"),
        mode=instructor.Mode.GEMINI_JSON,
    )

    # Truncate content — we only need links/navigation area
    truncated = markdown[:15000]

    try:
        result = client.create(
            response_model=PaginationAnalysis,
            messages=[{"role": "user", "content": f"""Analyze this webpage content and find pagination.
URL: {url}

Look for:
- "Next page" links
- Page number links (1, 2, 3...)
- "Load more" buttons
- Any navigation to additional pages of results

Content:
{truncated}

Return the full URLs for the next {num_pages - 1} pages if pagination exists."""}],
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
