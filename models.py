"""Static Pydantic models used across the project."""

from pydantic import BaseModel, Field


class FieldSpec(BaseModel):
    """Specification for a single data field."""
    name: str = Field(description="Snake_case field name")
    field_type: str = Field(default="str", description="Python type: str, int, float, list[str]")
    description: str = Field(description="What this field captures")


class RefinedSchema(BaseModel):
    """Output of the prompt refiner — a list of fields to extract."""
    fields: list[FieldSpec] = Field(description="List of fields to extract from each record")
    record_description: str = Field(description="What constitutes one record/item on the page")


class PaginationResult(BaseModel):
    """Result of pagination detection."""
    urls: list[str] = Field(description="List of page URLs to scrape")
    pattern: str = Field(default="", description="Detected pagination pattern")
    method: str = Field(default="heuristic", description="Detection method used")


class DetectedDataType(BaseModel):
    """A single data type detected on a page (e.g. 'Job Listings')."""
    name: str = Field(description="Human-readable name like 'Job Listings'")
    description: str = Field(description="What this data type represents on the page")
    record_description: str = Field(description="What constitutes a single record/item")
    suggested_fields: list[FieldSpec] = Field(description="Suggested fields to extract")


class DetectedContent(BaseModel):
    """Top 1-3 data types detected on a page."""
    data_types: list[DetectedDataType] = Field(description="Detected repeating data structures")
