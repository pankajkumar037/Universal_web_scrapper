"""Adaptive rate limiter: 6s base, +2s on CAPTCHA, max 20s, slow decay on success."""

import asyncio
import time
from config import settings
from utils.logger import get_logger

log = get_logger("rate_limiter")


class RateLimiter:
    def __init__(self, callback=None):
        self.current_delay = settings.RATE_LIMIT_BASE
        self.last_request_time = 0.0
        self.captcha_count = 0
        self.callback = callback

    def _cb(self, step, data=None):
        if self.callback:
            self.callback(step, data or {})

    async def wait(self):
        """Wait the appropriate amount of time before next request."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.current_delay:
            wait_time = self.current_delay - elapsed
            self._cb("rate_limit_wait", {"wait_seconds": round(wait_time, 1), "current_delay": round(self.current_delay, 1)})
            log.info(f"Rate limiting: waiting {wait_time:.1f}s (current delay: {self.current_delay:.1f}s)")
            await asyncio.sleep(wait_time)
        self.last_request_time = time.time()

    def on_success(self):
        """Slowly decay the delay on successful requests."""
        if self.current_delay > settings.RATE_LIMIT_BASE:
            self.current_delay = max(
                settings.RATE_LIMIT_BASE,
                self.current_delay - settings.RATE_LIMIT_DECAY,
            )
            log.info(f"Success decay: delay now {self.current_delay:.1f}s")

    def on_captcha(self):
        """Increase delay on CAPTCHA detection."""
        self.captcha_count += 1
        self.current_delay = min(
            settings.RATE_LIMIT_MAX,
            self.current_delay + settings.RATE_LIMIT_CAPTCHA_INCREMENT,
        )
        self._cb("rate_limit_captcha", {"captcha_count": self.captcha_count, "new_delay": round(self.current_delay, 1)})
        log.warning(f"CAPTCHA detected (#{self.captcha_count}): delay now {self.current_delay:.1f}s")

    @property
    def stats(self) -> dict:
        return {
            "current_delay": self.current_delay,
            "captcha_count": self.captcha_count,
        }
