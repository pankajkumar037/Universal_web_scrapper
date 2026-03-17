"""Crawler engine — orchestrates 4 layers with escalation on validation failure."""

import asyncio
import sys
import threading
from concurrent.futures import Future

from crawler.base import CrawlResult
from crawler.validator import validate_content
from crawler.layer1_stealth import StealthCrawler
from crawler.layer2_undetected import UndetectedCrawler
from crawler.layer3_proxy import ProxyCrawler
from crawler.layer4_jina import JinaCrawler
from utils.logger import get_logger

log = get_logger("engine")

_NEED_PROACTOR = sys.platform == "win32"

# Layer order for escalation
LAYERS = [StealthCrawler, UndetectedCrawler, ProxyCrawler, JinaCrawler]


def _run_in_proactor(coro):
    """Run coroutine in a thread with ProactorEventLoop (Windows Playwright fix)."""
    result_future = Future()

    def _thread_target():
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            result_future.set_result(loop.run_until_complete(coro))
        except Exception as e:
            result_future.set_exception(e)
        finally:
            loop.close()

    t = threading.Thread(target=_thread_target)
    t.start()
    t.join()
    return result_future.result()


class CrawlerEngine:
    """Strategy pattern orchestrator — escalates layers on validation failure."""

    def __init__(self):
        self.layers = [cls() for cls in LAYERS]
        self.last_layer = 0
        self.escalation_history: list[dict] = []

    async def crawl(self, url: str, callback=None, paginated: bool = False) -> CrawlResult:
        """Crawl URL, escalating through layers until valid content is obtained."""

        if callback:
            callback("crawl_start", {"url": url, "start_layer": 1})

        for i in range(len(self.layers)):
            layer = self.layers[i]
            self.last_layer = layer.layer

            if callback:
                callback("layer_attempt", {"layer": layer.layer, "name": layer.name})

            if _NEED_PROACTOR and isinstance(layer, (StealthCrawler, UndetectedCrawler)):
                result = _run_in_proactor(layer.crawl(url, paginated=paginated))
            else:
                result = await layer.crawl(url, paginated=paginated)

            if not result.success:
                log.warning(f"Layer {layer.layer} ({layer.name}) failed: {result.error}")
                self.escalation_history.append({
                    "layer": layer.layer, "name": layer.name,
                    "result": "failed", "error": result.error,
                })
                if callback:
                    callback("layer_failed", {"layer": layer.layer, "error": result.error})
                continue

            # Validate content
            valid, reason = validate_content(result.markdown, url)
            if valid:
                log.info(f"Layer {layer.layer} ({layer.name}) succeeded with {result.word_count} words")
                self.escalation_history.append({
                    "layer": layer.layer, "name": layer.name,
                    "result": "success", "error": None,
                })
                if callback:
                    callback("crawl_success", {"layer": layer.layer, "words": result.word_count})
                return result

            log.warning(f"Layer {layer.layer} validation failed: {reason}")
            self.escalation_history.append({
                "layer": layer.layer, "name": layer.name,
                "result": "failed", "error": reason,
            })
            if callback:
                callback("layer_failed", {"layer": layer.layer, "error": reason})

        # All layers exhausted
        log.error(f"All layers failed for {url}")
        if callback:
            callback("crawl_failed", {"url": url})
        return CrawlResult(url=url, success=False, error="All crawler layers exhausted")
