"""Schema caching by domain."""

import json
import os
from urllib.parse import urlparse

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".schema_cache")


def _domain_key(url: str) -> str:
    return urlparse(url).netloc.replace(".", "_")


def save_schema(url: str, schema: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{_domain_key(url)}.json")
    with open(path, "w") as f:
        json.dump(schema, f, indent=2)


def load_schema(url: str) -> dict | None:
    path = os.path.join(CACHE_DIR, f"{_domain_key(url)}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None
