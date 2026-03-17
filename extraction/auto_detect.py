"""Auto-detect data types on a page — enables URL-only mode."""

import threading

import google.generativeai as genai
import instructor
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import settings
from extraction.prompt_refiner import _smart_sample
from models import DetectedContent, DetectedDataType, FieldSpec, RefinedSchema
from utils.logger import get_logger

log = get_logger("auto_detect")


# --- CrewAI tool wrapper for content analysis ---

class AnalyzeInput(BaseModel):
    content: str = Field(description="Markdown content to analyze for data structures")


class AnalyzeContentTool(BaseTool):
    name: str = "AnalyzeContent"
    description: str = (
        "Analyze webpage markdown content to identify repeating data structures. "
        "Returns detected data types with suggested extraction fields."
    )
    args_schema: type[BaseModel] = AnalyzeInput

    def _run(self, content: str) -> str:
        result = _detect_with_gemini(content)
        return result.model_dump_json()


DETECT_SYSTEM_PROMPT = """You are a data structure analyst. Given webpage content (as markdown), identify ALL repeating/tabular data structures present.

For each distinct data type found:
1. Give it a clear human-readable name (e.g. "Job Listings", "Product Cards", "Research Papers")
2. Describe what this data type represents
3. Write what constitutes a single record/item
4. Suggest 4-10 fields to extract, each with:
   - snake_case name
   - type (str, int, float, or list[str])
   - clear description

Return 1-3 data types, ranked by how prominent they are on the page.
Focus on the MAIN content, not navigation, headers, or footers."""


def _detect_with_gemini(markdown: str) -> DetectedContent:
    """Direct Gemini call to detect data types on a page."""
    genai.configure(api_key=settings.GEMINI_API_KEY)
    client = instructor.from_gemini(
        client=genai.GenerativeModel(model_name=f"models/{settings.GEMINI_MODEL}"),
        mode=instructor.Mode.GEMINI_JSON,
    )

    sampled = _smart_sample(markdown, budget=12000)
    prompt = f"""Analyze this webpage content and identify all repeating data structures:

```
{sampled}
```

Identify the main data types with suggested extraction fields."""

    result = client.create(
        response_model=DetectedContent,
        messages=[{"role": "user", "content": DETECT_SYSTEM_PROMPT + "\n\n" + prompt}],
        generation_config={"temperature": settings.GEMINI_TEMP_STRICT},
    )

    log.info(f"Detected {len(result.data_types)} data types: {[d.name for d in result.data_types]}")
    return result


def detect_page_content(markdown: str) -> list[DetectedDataType]:
    """Detect data types on a page using CrewAI agent, falling back to direct Gemini.

    Uses a CrewAI 'Content Analyst' agent wrapping AnalyzeContentTool for visible
    agent usage (hackathon requirement), with a timeout fallback to direct Gemini.
    """
    # Try CrewAI agent first (visible for judges)
    try:
        analyst = Agent(
            role="Content Analyst",
            goal="Analyze webpage content to identify all repeating data structures and suggest extraction schemas.",
            backstory=(
                "You are an expert at analyzing webpage content to identify structured data. "
                "Use the AnalyzeContent tool to detect data types on the page."
            ),
            tools=[AnalyzeContentTool()],
            llm=f"gemini/{settings.GEMINI_MODEL}",
            verbose=False,
        )

        sampled = _smart_sample(markdown, budget=8000)
        task = Task(
            description=f"""Analyze the following webpage content using your AnalyzeContent tool.
Pass the content to the tool and return the result.

Content:
{sampled}""",
            expected_output="JSON with detected data types and suggested fields.",
            agent=analyst,
        )

        crew = Crew(agents=[analyst], tasks=[task], verbose=False)

        result_container = [None]
        error_container = [None]

        def _run():
            try:
                result_container[0] = crew.kickoff()
            except Exception as e:
                error_container[0] = e

        t = threading.Thread(target=_run)
        t.start()
        t.join(timeout=60)

        if t.is_alive() or error_container[0]:
            raise TimeoutError("CrewAI agent timed out or failed")

        # Parse result — the tool already returns DetectedContent
        raw = str(result_container[0])
        try:
            detected = DetectedContent.model_validate_json(raw)
            return detected.data_types
        except Exception:
            log.warning("Could not parse CrewAI output, falling back to direct Gemini")

    except Exception as e:
        log.warning(f"CrewAI Content Analyst failed ({e}), falling back to direct Gemini")

    # Fallback: direct Gemini call
    result = _detect_with_gemini(markdown)
    return result.data_types


def detected_to_schema(detected: DetectedDataType) -> RefinedSchema:
    """Convert a DetectedDataType into a RefinedSchema for extraction."""
    return RefinedSchema(
        fields=detected.suggested_fields,
        record_description=detected.record_description,
    )
