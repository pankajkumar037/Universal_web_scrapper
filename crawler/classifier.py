"""HEAD request classifier → LOW / MEDIUM / HIGH risk."""

import requests
from utils.logger import get_logger

log = get_logger("classifier")

# Known protection patterns
HIGH_RISK_DOMAINS = ["linkedin.com", "amazon.com", "zillow.com"]
MEDIUM_RISK_HEADERS = ["cf-ray", "cf-cache-status"]  # Cloudflare


def classify_risk(url: str) -> str:
    """Classify URL as LOW, MEDIUM, or HIGH risk based on HEAD request."""

    # Check domain
    for domain in HIGH_RISK_DOMAINS:
        if domain in url:
            log.info(f"[{url}] HIGH risk (known protected domain)")
            return "HIGH"

    try:
        resp = requests.head(url, timeout=10, allow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        # Check status
        if resp.status_code == 403:
            log.info(f"[{url}] HIGH risk (403 on HEAD)")
            return "HIGH"

        if resp.status_code == 503:
            log.info(f"[{url}] HIGH risk (503 challenge page)")
            return "HIGH"

        # Check for Cloudflare / bot protection headers
        headers_lower = {k.lower(): v for k, v in resp.headers.items()}
        for marker in MEDIUM_RISK_HEADERS:
            if marker in headers_lower:
                log.info(f"[{url}] MEDIUM risk (Cloudflare detected)")
                return "MEDIUM"

        # Check for large redirects (possible bot detection)
        if len(resp.history) > 2:
            log.info(f"[{url}] MEDIUM risk (multiple redirects)")
            return "MEDIUM"

        log.info(f"[{url}] LOW risk")
        return "LOW"

    except requests.RequestException as e:
        log.warning(f"[{url}] HEAD request failed: {e}, defaulting to MEDIUM")
        return "MEDIUM"
