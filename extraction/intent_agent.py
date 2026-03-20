"""Conversational intent agent: collects site, topic, pages in ≤3 turns, then resolves URL."""

import json
import re

import google.generativeai as genai
from pydantic import BaseModel

from config import settings


class IntentState(BaseModel):
    site: str | None = None
    query: str | None = None
    num_pages: int | None = None
    description: str | None = None
    location: str | None = None
    turn: int = 0


KNOWN_PATTERNS: dict[str, str] = {
    # --- Jobs (India + Global) ---
    "linkedin":           "https://www.linkedin.com/jobs/search/?keywords={q}&location={location}",
    "linkedin.com":       "https://www.linkedin.com/jobs/search/?keywords={q}&location={location}",
    "naukri":             "https://www.naukri.com/{slug}-jobs",
    "naukri.com":         "https://www.naukri.com/{slug}-jobs",
    "indeed":             "https://www.indeed.com/jobs?q={q}&l={location}",
    "indeed.com":         "https://www.indeed.com/jobs?q={q}&l={location}",
    "indeed.co.in":       "https://www.indeed.co.in/jobs?q={q}&l={location}",
    "glassdoor":          "https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={q}",
    "glassdoor.com":      "https://www.glassdoor.com/Job/jobs.htm?sc.keyword={q}",
    "glassdoor.co.in":    "https://www.glassdoor.co.in/Job/jobs.htm?sc.keyword={q}",
    "internshala":        "https://internshala.com/internships/{slug}-internship/",
    "internshala.com":    "https://internshala.com/internships/{slug}-internship/",
    # --- E-Commerce ---
    "flipkart":           "https://www.flipkart.com/search?q={q}",
    "flipkart.com":       "https://www.flipkart.com/search?q={q}",
    "amazon.in":          "https://www.amazon.in/{slug}/s?k={q}",
    "myntra":             "https://www.myntra.com/{slug}",
    "myntra.com":         "https://www.myntra.com/{slug}",


    # --- Research / Dev ---
    "scholar.google":     "https://scholar.google.com/scholar?q={q}",
    "scholar.google.com": "https://scholar.google.com/scholar?q={q}",
    # --- Social / Content ---
    
    "reddit":             "https://www.reddit.com/search/?q={q}",
    "reddit.com":         "https://www.reddit.com/search/?q={q}",
    "medium":             "https://medium.com/search?q={q}",
    "medium.com":         "https://medium.com/search?q={q}",
    "quora":              "https://www.quora.com/search?q={q}",
    "quora.com":          "https://www.quora.com/search?q={q}",
}

_SYSTEM_PROMPT = """You are a web scraping assistant helping users describe what they want to scrape.
Extract information from the user message and merge it with the current state.
Output ONLY a valid JSON object — no markdown, no explanation.

JSON schema:
{
  "site": "<website name or domain, or null if not mentioned>",
  "query": "<what to search/scrape, or null if not mentioned>",
  "num_pages": <integer number of pages, or null if not mentioned>,
  "description": "<any field/schema info the user mentioned (e.g. 'title, company, salary'), or null>",
  "location": "<city/country/region explicitly mentioned by user, or null if not mentioned>",
  "ready": <true if BOTH site AND query are non-null>,
  "follow_up_question": "<ONE concise question if not ready, else null>"
}

Rules:
- ready=true only when both site and query are known.
- Never ask about pages or description — only ask about site or query.
- follow_up_question must be null when ready=true.
- If turn==3, always set ready=true and follow_up_question=null.
- Extract location ONLY if explicitly mentioned (e.g. "in USA", "London jobs"). Never infer or assume.
- Output pure JSON only."""


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _match_known_site(site: str) -> str | None:
    """Return the matching key from KNOWN_PATTERNS, or None."""
    site_lower = site.lower().strip()
    # Exact match first
    for key in KNOWN_PATTERNS:
        if site_lower == key:
            return key
    # Substring containment
    for key in KNOWN_PATTERNS:
        if key in site_lower or site_lower in key:
            return key
    return None


def _build_known_url(site_key: str, query: str, location: str | None = None) -> str:
    pattern = KNOWN_PATTERNS[site_key]
    slug = _slugify(query)
    q = query.replace(" ", "+")
    loc = (location or "India").replace(" ", "+")
    return pattern.format(q=q, slug=slug, location=loc)


def _execute_search(query: str, include_domains: list[str] | None = None) -> str:
    """Call Tavily and return results as a formatted string for the LLM."""
    api_key = settings.TAVILY_API_KEY
    if not api_key:
        return "Error: TAVILY_API_KEY not set — cannot search"
    try:
        from tavily import TavilyClient
    except ModuleNotFoundError:
        return "Error: tavily-python not installed — run: pip install tavily-python"
    try:
        client = TavilyClient(api_key=api_key)
        kwargs: dict = {"query": query, "max_results": 5}
        if include_domains:
            kwargs["include_domains"] = include_domains
        result = client.search(**kwargs)
        rows = [f"- {r['url']}  ({r.get('title', '')})" for r in result.get("results", [])]
        return "\n".join(rows) if rows else "No results found"
    except Exception as e:
        return f"Search failed: {e}"


def _resolve_via_agent(site: str, query: str, location: str) -> tuple[str, str]:
    """Gemini function-calling loop: LLM uses search_web tool to find URL."""
    if not settings.GEMINI_API_KEY:
        return "__error__:GEMINI_API_KEY not configured", "tavily_error"

    search_tool = genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="search_web",
                description=(
                    "Search the web to find URLs. Use this to locate the search/listing "
                    "page URL for a specific website. Call multiple times with different "
                    "queries if needed."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "query": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Search query string"
                        ),
                        "include_domains": genai.protos.Schema(
                            type=genai.protos.Type.ARRAY,
                            items=genai.protos.Schema(type=genai.protos.Type.STRING),
                            description="Restrict results to these domains (optional)"
                        ),
                    },
                    required=["query"],
                ),
            )
        ]
    )

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=f"models/{settings.GEMINI_MODEL}",
        tools=[search_tool],
    )
    prompt = (
        f"Find the search results page URL for:\n"
        f"  website: {site}\n"
        f"  query: {query}\n"
        f"  location: {location}\n\n"
        f"Use search_web to find a real, working URL. "
        f"When done, output ONLY the URL on a single line."
    )

    try:
        chat = model.start_chat()
        response = chat.send_message(prompt)

        for _ in range(4):  # allow up to 4 tool calls
            parts = response.candidates[0].content.parts if response.candidates else []
            fc = next((p.function_call for p in parts if hasattr(p, "function_call") and p.function_call.name), None)
            if fc is None:
                break
            tool_result = _execute_search(
                query=fc.args.get("query", ""),
                include_domains=list(fc.args.get("include_domains", [])) or None,
            )
            response = chat.send_message(
                genai.protos.Content(parts=[
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc.name, response={"result": tool_result}
                        )
                    )
                ])
            )

        # Extract URL from final text response
        text = ""
        for part in (response.candidates[0].content.parts if response.candidates else []):
            if hasattr(part, "text") and part.text:
                text = part.text.strip()
                break

        url_match = re.search(r"https?://[^\s\"'<>]+", text)
        if url_match:
            return url_match.group(0).rstrip(".,)\"'"), "tavily"

        # Gemini sometimes omits the protocol — try to salvage a bare www. URL
        bare_match = re.search(r"\bwww\.[a-z0-9-]+\.[a-z]{2,6}[/\w?.=&%+#@-]*", text)
        if bare_match:
            return "https://" + bare_match.group(0).rstrip(".,)\"'"), "tavily"

        return f"__error__:Agent could not find a URL for '{query}' on {site}", "tavily_error"

    except Exception as e:
        return f"__error__:{e}", "tavily_error"


def _resolve_via_llm_knowledge(site: str, query: str, location: str) -> tuple[str, str]:
    """Ask Gemini directly (no tools) to construct the URL from its training knowledge."""
    if not settings.GEMINI_API_KEY:
        return "__error__:GEMINI_API_KEY not configured", "tavily_error"
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=f"models/{settings.GEMINI_MODEL}")
        prompt = (
            f"Construct the search results page URL for:\n"
            f"  site: {site}\n"
            f"  query: {query}\n"
            f"  location: {location}\n\n"
            f"Use your knowledge to build the most likely working search/listing URL.\n"
            f"Output ONLY the complete URL starting with https://, nothing else."
        )
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.0),
        )
        text = response.text.strip()
        url_match = re.search(r"https?://[^\s\"'<>]+", text)
        if url_match:
            return url_match.group(0).rstrip(".,)\"'"), "llm_inferred"
        bare_match = re.search(r"\bwww\.[a-z0-9-]+\.[a-z]{2,6}[/\w?.=&%+#-]*", text)
        if bare_match:
            return "https://" + bare_match.group(0).rstrip(".,)\"'"), "llm_inferred"
        return f"__error__:LLM could not construct a URL for '{query}' on {site}", "tavily_error"
    except Exception as e:
        return f"__error__:{e}", "tavily_error"


def resolve_url(site: str, query: str, location: str | None = None) -> tuple[str, str]:
    """Return (url, source) where source is 'known_site', 'tavily', 'llm_inferred', or 'tavily_error'."""
    matched = _match_known_site(site)
    if matched:
        return _build_known_url(matched, query, location), "known_site"

    loc = location or "India"
    url, source = _resolve_via_agent(site, query, loc)
    if source == "tavily_error":
        url, source = _resolve_via_llm_knowledge(site, query, loc)
    return url, source


def run_intent_turn(state: IntentState, user_message: str) -> tuple[IntentState, str | None]:
    """Process one conversation turn.

    Returns (updated_state, follow_up_question).
    follow_up_question is None when the agent has enough info (site + query known, or turn 3 reached).
    """
    state = state.model_copy(deep=True)
    state.turn += 1

    prompt = f"""{_SYSTEM_PROMPT}

Current state:
- site: {state.site!r}
- query: {state.query!r}
- num_pages: {state.num_pages!r}
- description: {state.description!r}
- turn: {state.turn}/3

User message: {user_message!r}

Important:
- Do NOT overwrite site with null if it is already {state.site!r}
- Do NOT overwrite query with null if it is already {state.query!r}
- If turn==3 (this is turn {state.turn}), set ready=true and follow_up_question=null
Output JSON:"""

    data: dict = {}
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=f"models/{settings.GEMINI_MODEL}")
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )
        raw = response.text.strip()
        # Extract JSON even if there's surrounding text
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(json_match.group() if json_match else raw)
    except Exception:
        pass  # use empty data → fallback logic below

    # Merge: only fill None fields (never overwrite with None)
    if data.get("site") and not state.site:
        state.site = str(data["site"])
    if data.get("query") and not state.query:
        state.query = str(data["query"])
    if data.get("num_pages") and not state.num_pages:
        try:
            state.num_pages = int(data["num_pages"])
        except (TypeError, ValueError):
            pass

    if data.get("location") and not state.location:
        state.location = str(data["location"])

    # Accumulate description across turns
    new_desc = data.get("description")
    if new_desc:
        state.description = (
            f"{state.description}, {new_desc}" if state.description else str(new_desc)
        )

    # Ready when site + query both known, or forced on turn 3
    ready = bool(state.site and state.query) or state.turn >= 3

    if ready:
        if not state.num_pages:
            state.num_pages = 1
        return state, None

    # Build a sensible follow-up question
    follow_up = data.get("follow_up_question")
    if not follow_up:
        follow_up = (
            "Which website would you like to scrape?"
            if not state.site
            else "What would you like to search for or scrape on that site?"
        )
    return state, str(follow_up)
