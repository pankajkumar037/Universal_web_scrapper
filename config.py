"""Central configuration loaded from .env with sensible defaults."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    SCRAPERAPI_KEY: str = os.getenv("SCRAPERAPI_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    # Gemini
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_TEMP_STRICT: float = 0.0
    GEMINI_MAX_TOKENS: int = 8192

    # Crawler validation
    MIN_WORDS: int = 150
    BLOCK_PHRASES: list[str] = [
        "access denied",
        "enable javascript",
        "captcha",
        "unusual traffic",
        "verify you are human",
        "blocked",
        "403 forbidden",
        "just a moment",
        "checking your browser",
        "please complete the security check",
    ]
    CONTENT_DENSITY_THRESHOLD: float = 0.3

    # Rate limiting
    RATE_LIMIT_BASE: float = 6.0  # seconds
    RATE_LIMIT_CAPTCHA_INCREMENT: float = 2.0
    RATE_LIMIT_MAX: float = 20.0
    RATE_LIMIT_DECAY: float = 0.5  # decrease on success

    # Crawler timing
    CRAWL_DELAY_NORMAL: float = 3.0       # seconds, non-paginated pages
    CRAWL_DELAY_PAGINATED: float = 6.0    # seconds, paginated/AJAX pages
    CRAWL_PAGE_TIMEOUT: int = 60000       # ms, max wait for page load

    # ScraperAPI
    SCRAPERAPI_MIN_CREDITS: int = 50  # skip layer 3 if below

    # Pagination
    MAX_PAGES: int = 10




settings = Settings()
