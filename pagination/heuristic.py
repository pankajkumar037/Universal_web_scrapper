"""Regex-based pagination detection — zero AI calls."""

import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from models import PaginationResult
from utils.logger import get_logger

log = get_logger("pagination_heuristic")

# Known pagination parameter patterns
PAGE_PARAMS = ["page", "p", "pg", "pageNumber"]
OFFSET_PARAMS = ["start", "offset", "from", "skip"]

# Site-specific patterns
SITE_PATTERNS = {
    "scholar.google.com": {"param": "start", "step": 10, "type": "offset"},
    "naukri.com": {"param": "page", "step": 1, "type": "page"},
    "flipkart.com": {"param": "page", "step": 1, "type": "page"},
    "linkedin.com": {"param": "start", "step": 25, "type": "offset"},
}


def _get_site_key(url: str) -> str | None:
    host = urlparse(url).netloc
    for site_key in SITE_PATTERNS:
        if site_key in host:
            return site_key
    return None


def _build_page_urls(url: str, param: str, num_pages: int, step: int = 1, start: int = 1) -> list[str]:
    """Build pagination URLs by setting a query parameter."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    urls = [url]  # Page 1 is always the original URL

    for i in range(1, num_pages):
        query[param] = [str(start + i * step)]
        new_query = urlencode(query, doseq=True)
        new_url = urlunparse(parsed._replace(query=new_query))
        urls.append(new_url)

    return urls


def detect_pagination(url: str, num_pages: int = 3, markdown: str = "") -> PaginationResult:
    """Detect pagination pattern from URL structure. No AI calls.

    Args:
        url: The base URL
        num_pages: Number of pages to generate
        markdown: Optional page content for link-based detection
    """
    if num_pages <= 1:
        return PaginationResult(urls=[url], pattern="single", method="heuristic")

    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)

    # Check for site-specific known patterns
    site_key = _get_site_key(url)
    if site_key:
        pattern = SITE_PATTERNS[site_key]
        if pattern["type"] == "offset":
            urls = _build_page_urls(url, pattern["param"], num_pages, step=pattern["step"], start=0)
        else:
            urls = _build_page_urls(url, pattern["param"], num_pages, step=pattern["step"], start=1)
        log.info(f"Site-specific pattern for {site_key}: {pattern['param']}")
        return PaginationResult(urls=urls, pattern=f"{pattern['param']}={pattern['type']}", method="heuristic")

    # Check if URL already has a page-like parameter
    for param in PAGE_PARAMS:
        if param in query:
            urls = _build_page_urls(url, param, num_pages, step=1, start=1)
            log.info(f"Detected existing page param: {param}")
            return PaginationResult(urls=urls, pattern=f"{param}=N", method="heuristic")

    for param in OFFSET_PARAMS:
        if param in query:
            # Try to detect step size from current value
            current = int(query[param][0]) if query[param][0].isdigit() else 0
            step = current if current > 0 else 10
            urls = _build_page_urls(url, param, num_pages, step=step, start=0)
            log.info(f"Detected existing offset param: {param}")
            return PaginationResult(urls=urls, pattern=f"{param}=offset", method="heuristic")

    # Speculative: try adding ?page=N if no param exists
    urls = _build_page_urls(url, "page", num_pages, step=1, start=1)
    log.info("Speculative pagination: adding ?page=N")
    return PaginationResult(urls=urls, pattern="?page=N (speculative)", method="heuristic")
