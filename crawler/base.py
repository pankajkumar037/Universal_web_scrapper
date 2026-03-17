"""CrawlResult dataclass and CrawlerStrategy ABC."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CrawlResult:
    url: str
    markdown: str = ""
    success: bool = False
    layer: int = 0
    error: str = ""
    word_count: int = 0
    metadata: dict = field(default_factory=dict)
    links: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.markdown:
            self.word_count = len(self.markdown.split())


class CrawlerStrategy(ABC):
    """Abstract base for all crawler layers."""

    layer: int = 0
    name: str = "base"

    @abstractmethod
    async def crawl(self, url: str, paginated: bool = False) -> CrawlResult:
        ...
