"""Regex-based pagination detection — zero AI calls."""

import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin
from models import PaginationResult
from utils.logger import get_logger

log = get_logger("pagination_heuristic")

# Known pagination parameter patterns
PAGE_PARAMS = ["page", "p", "pg", "pageNumber"]
OFFSET_PARAMS = ["start", "offset", "from", "skip"]

# Site-specific patterns
SITE_PATTERNS = {
    "scholar.google.com": {"param": "start", "step": 10, "type": "offset"},
    "naukri.com": {"type": "path_suffix"},
    "flipkart.com": {"param": "page", "step": 1, "type": "page"},
    "linkedin.com": {"param": "start", "step": 25, "type": "offset"},
}

# Regex to detect trailing page number in path: /jobs-3, /results-12
PATH_PAGE_SUFFIX_RE = re.compile(r'^(.*?)-(\d+)$')

# Regex to extract markdown links: [text](url)
MD_LINK_RE = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')

# Navigation text patterns (Next, >, >>, →, etc.)
NAV_TEXT_PATTERNS = re.compile(
    r'^(?:next(?:\s*page)?|>+|>>|>>>|→|›|»)$',
    re.IGNORECASE,
)

# URL patterns that indicate pagination parameters
PAGINATION_URL_PATTERNS = re.compile(
    r'(?:[\?&](?:page|p|pg|pageNumber|start|offset|from|skip)=\d+|/page[/-]\d+)',
    re.IGNORECASE,
)


def _get_site_key(url: str) -> str | None:
    host = urlparse(url).netloc
    for site_key in SITE_PATTERNS:
        if site_key in host:
            return site_key
    return None


def _build_path_page_urls(url: str, num_pages: int) -> list[str]:
    """Build pagination URLs for sites using path-suffix pagination (e.g. /jobs-2, /jobs-3)."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    # Check if path already ends with -N (user gave e.g. /jobs-4)
    m = PATH_PAGE_SUFFIX_RE.match(path)
    if m:
        base_path = m.group(1)
        current_page = int(m.group(2))
    else:
        base_path = path
        current_page = 1

    urls = [url]
    for i in range(1, num_pages):
        page_num = current_page + i
        new_path = f"{base_path}-{page_num}"
        new_url = urlunparse(parsed._replace(path=new_path))
        urls.append(new_url)
    return urls


def _build_page_urls(url: str, param: str, num_pages: int, step: int = 1, start: int = 1) -> list[str]:
    """Build pagination URLs by setting a query parameter."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)

    # Respect current page value if param already in URL
    if param in query and query[param][0].isdigit():
        effective_start = int(query[param][0])
    else:
        effective_start = start

    urls = [url]  # Page 1 is always the original URL

    for i in range(1, num_pages):
        query[param] = [str(effective_start + i * step)]
        new_query = urlencode(query, doseq=True)
        new_url = urlunparse(parsed._replace(query=new_query))
        urls.append(new_url)

    return urls


def _extract_pagination_from_markdown(
    base_url: str, markdown: str, num_pages: int
) -> list[str] | None:
    """Extract real pagination URLs from markdown content.

    Looks for nav links (Next, >, →), pagination-param links (?page=2),
    and digit links ([2](url)).  Returns a list starting with the current
    page URL, followed by discovered next-page URLs, or None.
    """
    parsed_base = urlparse(base_url)
    base_path = parsed_base.path.rstrip("/")

    nav_urls: list[str] = []       # "Next" / ">" style links
    param_urls: dict[int, str] = {}  # page-number → url from param links
    digit_urls: dict[int, str] = {}  # page-number → url from digit-text links

    prev_re = re.compile(r'^(?:prev(?:ious)?(?:\s*page)?|<+|<<|<<<|←|‹|«)$', re.IGNORECASE)

    for text, href in MD_LINK_RE.findall(markdown):
        text = text.strip()
        href = href.strip()

        # Skip non-http links and anchors
        if href.startswith(("#", "javascript:", "mailto:")):
            continue

        # Resolve relative URLs
        absolute = urljoin(base_url, href)
        abs_parsed = urlparse(absolute)

        # Skip links to a different domain
        if abs_parsed.netloc and abs_parsed.netloc != parsed_base.netloc:
            continue

        # Skip links that resolve to exactly the current page
        if abs_parsed.path.rstrip("/") == base_path and abs_parsed.query == parsed_base.query:
            continue

        # Skip previous/back links
        if prev_re.match(text):
            continue

        # 1) Nav-text links ("Next", ">", "→", etc.)
        if NAV_TEXT_PATTERNS.match(text):
            nav_urls.append(absolute)
            continue

        # 2) Links whose URL contains pagination params
        if PAGINATION_URL_PATTERNS.search(absolute):
            # Try to extract page number
            m = re.search(r'(?:page|p|pg|pageNumber)=(\d+)', absolute, re.IGNORECASE)
            if m:
                param_urls[int(m.group(1))] = absolute
                continue
            m = re.search(r'/page[/-](\d+)', absolute, re.IGNORECASE)
            if m:
                param_urls[int(m.group(1))] = absolute
                continue
            # offset-style — still useful, just store by position
            param_urls[len(param_urls) + 2] = absolute
            continue

        # 3) Digit-only link text ("2", "3", …)
        if text.isdigit():
            page_num = int(text)
            if 2 <= page_num <= 100:
                digit_urls[page_num] = absolute

    # ── Assemble results ──────────────────────────────────────────────
    # Prefer nav links (most reliable "Next" chain), then param, then digit.
    if nav_urls:
        # "Next" link gives us one page at a time — return current + next
        urls = [base_url] + nav_urls[:num_pages - 1]
        log.info(f"Found {len(nav_urls)} nav link(s) in markdown (Next/>/→)")
        return urls

    if param_urls:
        sorted_pages = sorted(param_urls.items())
        urls = [base_url] + [u for _, u in sorted_pages[: num_pages - 1]]
        log.info(f"Found {len(param_urls)} param-pagination link(s) in markdown")
        return urls

    if digit_urls:
        sorted_pages = sorted(digit_urls.items())
        urls = [base_url] + [u for _, u in sorted_pages[: num_pages - 1]]
        log.info(f"Found {len(digit_urls)} digit-pagination link(s) in markdown")
        return urls

    return None


def _extract_pagination_from_links(
    base_url: str, links: dict, num_pages: int
) -> list[str] | None:
    """Extract real pagination URLs from Crawl4AI's structured links dict.

    The links dict has the form {"internal": [{"href": ..., "text": ...}, ...], "external": [...]}.
    Only internal links are checked.  Priority: nav-text > pagination-param URLs > digit-text.
    """
    internal = links.get("internal", [])
    if not internal:
        return None

    parsed_base = urlparse(base_url)
    base_path = parsed_base.path.rstrip("/")

    nav_urls: list[str] = []
    param_urls: dict[int, str] = {}
    digit_urls: dict[int, str] = {}

    prev_re = re.compile(r'^(?:prev(?:ious)?(?:\s*page)?|<+|<<|<<<|←|‹|«)$', re.IGNORECASE)

    for link in internal:
        href = (link.get("href") or "").strip()
        text = (link.get("text") or "").strip()

        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue

        absolute = urljoin(base_url, href)
        abs_parsed = urlparse(absolute)

        # Skip links to exactly the current page
        if abs_parsed.path.rstrip("/") == base_path and abs_parsed.query == parsed_base.query:
            continue

        # Skip previous/back links
        if prev_re.match(text):
            continue

        # 1) Nav-text links ("Next", ">", "→", etc.)
        if NAV_TEXT_PATTERNS.match(text):
            nav_urls.append(absolute)
            continue

        # 2) Links whose URL contains pagination params
        if PAGINATION_URL_PATTERNS.search(absolute):
            m = re.search(r'(?:page|p|pg|pageNumber)=(\d+)', absolute, re.IGNORECASE)
            if m:
                param_urls[int(m.group(1))] = absolute
                continue
            m = re.search(r'/page[/-](\d+)', absolute, re.IGNORECASE)
            if m:
                param_urls[int(m.group(1))] = absolute
                continue
            param_urls[len(param_urls) + 2] = absolute
            continue

        # 3) Digit-only link text ("2", "3", …)
        if text.isdigit():
            page_num = int(text)
            if 2 <= page_num <= 100:
                digit_urls[page_num] = absolute

    # Assemble results — same priority as markdown version
    if nav_urls:
        urls = [base_url] + nav_urls[:num_pages - 1]
        log.info(f"Found {len(nav_urls)} nav link(s) in structured links (Next/>/→)")
        return urls

    if param_urls:
        sorted_pages = sorted(param_urls.items())
        urls = [base_url] + [u for _, u in sorted_pages[:num_pages - 1]]
        log.info(f"Found {len(param_urls)} param-pagination link(s) in structured links")
        return urls

    if digit_urls:
        sorted_pages = sorted(digit_urls.items())
        urls = [base_url] + [u for _, u in sorted_pages[:num_pages - 1]]
        log.info(f"Found {len(digit_urls)} digit-pagination link(s) in structured links")
        return urls

    return None


def detect_pagination(url: str, num_pages: int = 3, markdown: str = "", links: dict = None) -> PaginationResult:
    """Detect pagination pattern from URL structure. No AI calls.

    Args:
        url: The base URL
        num_pages: Number of pages to generate
        markdown: Optional page content for link-based detection
        links: Optional structured links dict from Crawl4AI result
    """
    if num_pages <= 1:
        return PaginationResult(urls=[url], pattern="single", method="heuristic")

    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)

    # 1) Real links from Crawl4AI structured links (DOM-based, most reliable)
    if links:
        struct_urls = _extract_pagination_from_links(url, links, num_pages)
        if struct_urls and len(struct_urls) > 1:
            return PaginationResult(urls=struct_urls, pattern="structured_links", method="heuristic")

    # 2) Real links from markdown content (Next/page links)
    if markdown:
        md_urls = _extract_pagination_from_markdown(url, markdown, num_pages)
        if md_urls and len(md_urls) > 1:
            return PaginationResult(urls=md_urls, pattern="markdown_links", method="heuristic")

    # 3) Site-specific hardcoded patterns (fallback)
    site_key = _get_site_key(url)
    if site_key:
        pattern = SITE_PATTERNS[site_key]
        if pattern["type"] == "path_suffix":
            urls = _build_path_page_urls(url, num_pages)
            log.info(f"Site-specific path-suffix pattern for {site_key}")
            return PaginationResult(urls=urls, pattern="path_suffix", method="heuristic")
        elif pattern["type"] == "offset":
            urls = _build_page_urls(url, pattern["param"], num_pages, step=pattern["step"], start=0)
        else:
            urls = _build_page_urls(url, pattern["param"], num_pages, step=pattern["step"], start=1)
        log.info(f"Site-specific pattern for {site_key}: {pattern['param']}")
        return PaginationResult(urls=urls, pattern=f"{pattern['param']}={pattern['type']}", method="heuristic")

    # 4) Existing query params in URL
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

    # 5) Speculative: try adding ?page=N if no param exists (last resort)
    urls = _build_page_urls(url, "page", num_pages, step=1, start=1)
    log.info("Speculative pagination: adding ?page=N")
    return PaginationResult(urls=urls, pattern="?page=N (speculative)", method="heuristic")
