"""Fuzzy content fingerprinting for same-page detection."""

import hashlib
import re


def content_fingerprint(markdown: str) -> str:
    """Compute a fuzzy fingerprint of page content.

    Strips digits (timestamps, ad IDs, prices) and collapses whitespace
    so that the same page served under different URLs — differing only
    in dynamic elements — produces the same fingerprint.
    """
    if not markdown:
        return ""
    # Remove all digits — these change between page loads (timestamps, IDs, counters)
    text = re.sub(r'\d+', '', markdown)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Use a middle section to avoid header/footer/nav noise
    if len(text) > 4000:
        mid = len(text) // 2
        text = text[mid - 2000:mid + 2000]
    return hashlib.md5(text.encode()).hexdigest()
