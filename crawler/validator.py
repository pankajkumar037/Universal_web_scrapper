"""3-check content validator: word count, block phrase scan, content density."""

from config import settings
from utils.logger import get_logger

log = get_logger("validator")


def validate_content(markdown: str, url: str = "") -> tuple[bool, str]:
    """Validate crawled content. Returns (is_valid, reason)."""

    # Check 1: Word count
    word_count = len(markdown.split())
    if word_count < settings.MIN_WORDS:
        reason = f"Too few words: {word_count} < {settings.MIN_WORDS}"
        log.warning(f"[{url}] {reason}")
        return False, reason

    # Check 2: Block phrase scan
    lower = markdown.lower()
    # Only check first 500 chars for normal pages, full text only for very short pages
    check_region = lower[:500] if word_count >= 300 else lower
    for phrase in settings.BLOCK_PHRASES:
        if phrase in check_region:
            reason = f"Block phrase detected: '{phrase}'"
            log.warning(f"[{url}] {reason}")
            return False, reason

    # Check 3: Content density (ratio of non-whitespace to total)
    stripped = markdown.replace(" ", "").replace("\n", "").replace("\t", "")
    if len(markdown) > 0:
        density = len(stripped) / len(markdown)
        if density < settings.CONTENT_DENSITY_THRESHOLD:
            reason = f"Low content density: {density:.2f} < {settings.CONTENT_DENSITY_THRESHOLD}"
            log.warning(f"[{url}] {reason}")
            return False, reason

    log.info(f"[{url}] Content valid: {word_count} words")
    return True, "valid"
