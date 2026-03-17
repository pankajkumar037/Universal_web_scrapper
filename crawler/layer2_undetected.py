"""Layer 2: Crawl4AI with override_navigator + simulate_user."""

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawler.base import CrawlerStrategy, CrawlResult
from utils.logger import get_logger

log = get_logger("layer2")


class UndetectedCrawler(CrawlerStrategy):
    layer = 2
    name = "undetected"

    async def crawl(self, url: str) -> CrawlResult:
        log.info(f"Layer 2 (undetected) crawling: {url}")
        try:
            browser_cfg = BrowserConfig(
                headless=True,
                java_script_enabled=True,
                enable_stealth=True,
            )
            run_cfg = CrawlerRunConfig(
                magic=True,
                simulate_user=True,
                wait_until="domcontentloaded",
                page_timeout=60000,
                delay_before_return_html=3.0,
            )
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)

                if result.success and result.markdown:
                    return CrawlResult(
                        url=url,
                        markdown=result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else str(result.markdown),
                        success=True,
                        layer=self.layer,
                    )
                return CrawlResult(
                    url=url,
                    success=False,
                    layer=self.layer,
                    error="Crawl4AI undetected returned empty",
                )
        except Exception as e:
            log.error(f"Layer 2 failed: {e}")
            return CrawlResult(url=url, success=False, layer=self.layer, error=str(e))
