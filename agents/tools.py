"""CrewAI BaseTool wrappers for crawler, extractor, pagination."""

import asyncio
import json
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from crawler.engine import CrawlerEngine
from extraction.prompt_refiner import refine_prompt
from extraction.schema_builder import build_dynamic_model
from extraction.extractor import extract_records
from pagination.heuristic import detect_pagination
from pagination.ai_fallback import ai_detect_pagination


class CrawlInput(BaseModel):
    url: str = Field(description="URL to crawl")


class CrawlTool(BaseTool):
    name: str = "CrawlWebpage"
    description: str = "Crawl a webpage and return its content as markdown text. Automatically handles anti-bot measures with multi-layer escalation."
    args_schema: type[BaseModel] = CrawlInput

    def _run(self, url: str) -> str:
        engine = CrawlerEngine()
        result = asyncio.run(engine.crawl(url))
        if result.success:
            return json.dumps({
                "success": True,
                "word_count": result.word_count,
                "layer": result.layer,
                "preview": result.markdown[:500],
            })
        return json.dumps({"success": False, "error": result.error})


class RefineInput(BaseModel):
    description: str = Field(description="User's plain English description of what to extract")
    sample_content: str = Field(default="", description="Sample page content for better inference")


class RefinePromptTool(BaseTool):
    name: str = "RefinePrompt"
    description: str = "Turn a vague user description into precise field specifications for data extraction."
    args_schema: type[BaseModel] = RefineInput

    def _run(self, description: str, sample_content: str = "") -> str:
        schema = refine_prompt(description, sample_content)
        return schema.model_dump_json()


class ExtractInput(BaseModel):
    markdown: str = Field(description="Markdown content to extract data from")
    schema_json: str = Field(description="JSON schema from RefinePrompt tool")


class ExtractTool(BaseTool):
    name: str = "ExtractData"
    description: str = "Extract structured data from markdown content using a schema. Returns list of records as JSON."
    args_schema: type[BaseModel] = ExtractInput

    def _run(self, markdown: str, schema_json: str) -> str:
        from models import RefinedSchema
        schema = RefinedSchema.model_validate_json(schema_json)
        model = build_dynamic_model(schema)
        records = extract_records(markdown, model, schema.record_description, schema=schema)
        return json.dumps(records, indent=2)


class PaginationInput(BaseModel):
    url: str = Field(description="Base URL to detect pagination for")
    num_pages: int = Field(default=3, description="Number of pages to generate")
    markdown: str = Field(default="", description="Page content for AI detection")


class PaginationTool(BaseTool):
    name: str = "DetectPagination"
    description: str = "Detect pagination pattern and generate page URLs."
    args_schema: type[BaseModel] = PaginationInput

    def _run(self, url: str, num_pages: int = 3, markdown: str = "") -> str:
        result = detect_pagination(url, num_pages, markdown)
        if "speculative" in result.pattern and markdown:
            ai_result = ai_detect_pagination(url, markdown, num_pages)
            if len(ai_result.urls) > 1:
                result = ai_result
        return result.model_dump_json()
