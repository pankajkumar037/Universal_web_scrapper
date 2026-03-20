"""Turn vague English descriptions into precise field specifications via Gemini."""

import google.generativeai as genai
import instructor
from config import settings
from models import RefinedSchema, FieldSpec
from utils.logger import get_logger

log = get_logger("prompt_refiner")


def _smart_sample(content: str, budget: int = 10000) -> str:
    """Sample beginning, middle, and end of content to avoid nav-heavy headers."""
    if len(content) <= budget:
        return content
    chunk = budget // 3
    beginning = content[:chunk]
    mid_start = max(chunk, len(content) // 2 - chunk // 2)
    middle = content[mid_start:mid_start + chunk]
    end = content[-chunk:]
    return beginning + "\n\n[... content omitted ...]\n\n" + middle + "\n\n[... content omitted ...]\n\n" + end


REFINER_SYSTEM_PROMPT = """You are a data extraction schema designer. Given a vague user description of what they want to scrape from a webpage, produce a precise list of fields to extract.

Rules:
1. Generate 4-10 fields that cover the user's intent comprehensively
2. Field names must be snake_case
3. Each field needs a clear description
4. field_type should be one of: str, int, float, list[str]
5. Include obvious fields the user might have forgotten (e.g., if scraping jobs, include location even if not mentioned)
6. The record_description should explain what constitutes ONE item/record on the page

Example: For "get job listings info" you might produce:
- job_title (str): Title of the job position
- company_name (str): Name of the hiring company
- location (str): Job location or "Remote"
- salary_info (str): Salary or pay range if shown on the card (e.g., "$50,000 - $80,000 a year", "₹6L - ₹12L a year"); use NOT_FOUND if not displayed
- experience_required (str): Required years or level of experience
- skills (list[str]): Skills listed IN THE JOB CARD — note: often absent on search result listing pages; use NOT_FOUND if not shown
- posted_date (str): When the job was posted — look for patterns like "Posted 2 days ago", "Just posted", "Active today", "1 hour ago", "30+ days ago"
- job_type (str): Full-time, Part-time, Contract, Internship, etc.
"""


def refine_prompt(user_description: str, sample_content: str = "") -> RefinedSchema:
    """Refine a vague user description into a structured schema specification."""

    genai.configure(api_key=settings.GEMINI_API_KEY)
    client = instructor.from_gemini(
        client=genai.GenerativeModel(model_name=f"models/{settings.GEMINI_MODEL}"),
        mode=instructor.Mode.GEMINI_JSON,
    )

    context = ""
    if sample_content:
        # Give the LLM a peek at the actual content for better field inference
        sampled = _smart_sample(sample_content)
        context = f"\n\nHere's a sample of the page content to help you understand the data:\n```\n{sampled}\n```"

    prompt = f"""User wants to scrape: "{user_description}"{context}

Generate a precise extraction schema with field specifications."""

    log.info(f"Refining prompt: '{user_description[:80]}...'")

    result = client.create(
        response_model=RefinedSchema,
        messages=[
            {"role": "user", "content": REFINER_SYSTEM_PROMPT + "\n\n" + prompt},
        ],
        generation_config={"temperature": settings.GEMINI_TEMP_STRICT},
    )

    log.info(f"Refined to {len(result.fields)} fields: {[f.name for f in result.fields]}")
    return result
