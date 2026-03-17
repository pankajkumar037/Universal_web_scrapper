"""Layer 1: Crawl4AI with magic mode (stealth)."""

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from config import settings
from crawler.base import CrawlerStrategy, CrawlResult
from utils.logger import get_logger

log = get_logger("layer1")


class StealthCrawler(CrawlerStrategy):
    layer = 1
    name = "stealth"

    async def crawl(self, url: str, paginated: bool = False) -> CrawlResult:
        log.info(f"Layer 1 (stealth) crawling: {url}")
        try:
            browser_cfg = BrowserConfig(
                headless=True,
                java_script_enabled=True,
            )
            run_cfg = CrawlerRunConfig(
                magic=True,
                wait_until="networkidle" if paginated else "domcontentloaded",
                page_timeout=settings.CRAWL_PAGE_TIMEOUT,
                delay_before_return_html=settings.CRAWL_DELAY_PAGINATED if paginated else settings.CRAWL_DELAY_NORMAL,
            )
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)

                if result.success and result.markdown:
                    return CrawlResult(
                        url=url,
                        markdown=result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else str(result.markdown),
                        success=True,
                        layer=self.layer,
                        links=getattr(result, 'links', {}) or {},
                    )
                return CrawlResult(
                    url=url,
                    success=False,
                    layer=self.layer,
                    error=f"Crawl4AI returned empty content",
                )
        except Exception as e:
            log.error(f"Layer 1 failed: {e}")
            return CrawlResult(url=url, success=False, layer=self.layer, error=str(e))
