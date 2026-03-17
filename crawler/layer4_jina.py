"""Layer 4: Jina Reader fallback — GET https://r.jina.ai/{url}."""

import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from crawler.base import CrawlerStrategy, CrawlResult
from utils.logger import get_logger

log = get_logger("layer4")


class JinaCrawler(CrawlerStrategy):
    layer = 4
    name = "jina"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        reraise=True,
    )
    def _fetch_with_retry(self, url: str) -> requests.Response:
        """Fetch URL via Jina Reader with retry logic."""
        resp = requests.get(
            f"https://r.jina.ai/{url}",
            headers={
                "Accept": "text/markdown",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp

    async def crawl(self, url: str) -> CrawlResult:
        log.info(f"Layer 4 (Jina) crawling: {url}")
        try:
            resp = self._fetch_with_retry(url)

            if resp.text.strip():
                return CrawlResult(
                    url=url,
                    markdown=resp.text,
                    success=True,
                    layer=self.layer,
                )

            return CrawlResult(
                url=url, success=False, layer=self.layer,
                error="Jina returned empty content",
            )

        except Exception as e:
            log.error(f"Layer 4 failed: {e}")
            return CrawlResult(url=url, success=False, layer=self.layer, error=str(e))
