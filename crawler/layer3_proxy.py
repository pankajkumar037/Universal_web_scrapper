"""Layer 3: ScraperAPI residential proxy + html2text conversion."""

import requests
import html2text
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
from crawler.base import CrawlerStrategy, CrawlResult
from utils.logger import get_logger

log = get_logger("layer3")


class ProxyCrawler(CrawlerStrategy):
    layer = 3
    name = "proxy"

    def _check_credits(self) -> bool:
        """Check if ScraperAPI has enough credits remaining."""
        if not settings.SCRAPERAPI_KEY:
            return False
        try:
            resp = requests.get(
                "https://api.scraperapi.com/account",
                params={"api_key": settings.SCRAPERAPI_KEY},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                remaining = data.get("requestLimit", 0) - data.get("requestCount", 0)
                log.info(f"ScraperAPI credits remaining: {remaining}")
                return remaining >= settings.SCRAPERAPI_MIN_CREDITS
        except Exception as e:
            log.warning(f"Credit check failed: {e}")
        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=2, max=15),
        reraise=True,
    )
    def _fetch_with_retry(self, url: str) -> requests.Response:
        """Fetch URL via ScraperAPI with retry logic."""
        resp = requests.get(
            "https://api.scraperapi.com",
            params={
                "api_key": settings.SCRAPERAPI_KEY,
                "url": url,
                "render": "true",
                "country_code": "us",
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp

    async def crawl(self, url: str) -> CrawlResult:
        log.info(f"Layer 3 (proxy) crawling: {url}")

        if not settings.SCRAPERAPI_KEY:
            return CrawlResult(
                url=url, success=False, layer=self.layer,
                error="No SCRAPERAPI_KEY configured",
            )

        if not self._check_credits():
            return CrawlResult(
                url=url, success=False, layer=self.layer,
                error="ScraperAPI credits too low, skipping to Layer 4",
            )

        try:
            resp = self._fetch_with_retry(url)

            converter = html2text.HTML2Text()
            converter.ignore_links = False
            converter.ignore_images = True
            converter.body_width = 0
            markdown = converter.handle(resp.text)

            return CrawlResult(
                url=url,
                markdown=markdown,
                success=True,
                layer=self.layer,
            )

        except Exception as e:
            log.error(f"Layer 3 failed: {e}")
            return CrawlResult(url=url, success=False, layer=self.layer, error=str(e))
