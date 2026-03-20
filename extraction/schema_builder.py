"""Dynamic Pydantic model builder via create_model().

Critical workaround: Gemini doesn't support Optional types in Instructor,
so we use str with default="NOT_FOUND" for all fields, then post-process to None.
"""

import json
import re
from typing import Any
from pydantic import BaseModel, Field, create_model
from models import RefinedSchema
from utils.logger import get_logger

log = get_logger("schema_builder")

def build_dynamic_model(schema: RefinedSchema) -> type[BaseModel]:
    """Build a Pydantic model dynamically from a RefinedSchema.

    All fields are str with default='NOT_FOUND' to work around
    Gemini's lack of Optional support in Instructor.
    """
    field_definitions = {}
    for field_spec in schema.fields:
        # Use Any for list fields so Gemini can return either a JSON array or a string
        py_type = Any if field_spec.field_type == "list[str]" else str
        field_definitions[field_spec.name] = (
            py_type,
            Field(default="NOT_FOUND", description=field_spec.description),
        )

    model = create_model("DynamicRecord", **field_definitions)
    log.info(f"Built model with fields: {list(field_definitions.keys())}")
    return model


def build_list_model(record_model: type[BaseModel]) -> type[BaseModel]:
    """Wrap a record model in a list container for batch extraction."""
    return create_model(
        "RecordList",
        records=(list[record_model], Field(default_factory=list, description="List of extracted records")),
    )


def _convert_value(value: str, field_type: str):
    """Convert a string value to the target type, returning as-is on failure."""
    if field_type == "int":
        try:
            # Strip non-numeric chars: "$1,234", "~100", "95%" -> numeric
            cleaned = re.sub(r'[^\d.\-]', '', value)
            return int(float(cleaned))
        except (ValueError, TypeError):
            log.warning(f"Could not convert '{value}' to int")
            return value
    elif field_type == "float":
        try:
            cleaned = re.sub(r'[^\d.\-]', '', value)
            return float(cleaned)
        except (ValueError, TypeError):
            log.warning(f"Could not convert '{value}' to float")
            return value
    elif field_type == "list[str]":
        # Try JSON array first
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
        # Prefer semicolons as delimiter
        if ";" in value:
            return [item.strip() for item in value.split(";") if item.strip()]
        # Comma-split, but skip if it looks like "Last, First" name pattern
        if "," in value:
            parts = [item.strip() for item in value.split(",") if item.strip()]
            # If only 2 parts and second starts lowercase or is short, likely a name
            if len(parts) == 2 and (parts[1][0:1].islower() or len(parts[1]) <= 3):
                return [value.strip()]
            return parts
        return [value] if value else []
    # str or unknown type — keep as-is
    return value


def post_process_records(records: list[dict], schema: RefinedSchema = None) -> list[dict]:
    """Convert NOT_FOUND values to None and parse typed fields."""
    # Build a type lookup from schema if provided
    type_map = {}
    if schema:
        for field_spec in schema.fields:
            type_map[field_spec.name] = field_spec.field_type

    processed = []
    for record in records:
        clean = {}
        for key, value in record.items():
            if value == "NOT_FOUND" or value == "" or value is None:
                clean[key] = None
            elif type_map.get(key) and type_map[key] != "str" and isinstance(value, str):
                clean[key] = _convert_value(value, type_map[key])
            else:
                clean[key] = value
        processed.append(clean)

    # Filter out records with too few populated fields (minimum 25% fill ratio)
    filtered = []
    for record in processed:
        total = len(record)
        populated = sum(1 for v in record.values() if v is not None)
        if total == 0 or populated / total >= 0.25:
            filtered.append(record)
        else:
            log.info(f"Dropped record: {populated}/{total} fields populated")
    return filtered
