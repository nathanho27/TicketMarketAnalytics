"""Shared helpers for calling APIs politely and logging safely.

Used by collect_ticketmaster.py, geocode_venues.py and collect_census.py.
"""
import json
import logging
import sys
import time

import requests

import config

MAX_RETRIES = 3
# Request parameters that hold API keys. Their values never reach logs or saved files.
SECRET_PARAMS = {"apikey", "key", "client_id", "client_secret"}
USER_AGENT = "TicketMarketAnalytics-class-project/1.0 (github.com/nathanho27/TicketMarketAnalytics)"

log = logging.getLogger("collect")


def setup_logging(name):
    """Log to the console and to logs/<name>.log. Returns the log file path."""
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = config.LOG_DIR / f"{name}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        force=True,
    )
    return log_file


def redact(params):
    """Copy of the request params with API keys hidden, safe to log or save."""
    return {k: ("<redacted>" if k in SECRET_PARAMS else v) for k, v in params.items()}


def mask_secrets(text, params):
    """Replace any key value that appears inside text (e.g. an echoed error body)."""
    for k, v in params.items():
        if k in SECRET_PARAMS and v:
            text = text.replace(str(v), "<redacted>")
    return text


class PoliteClient:
    """requests wrapper that spaces out calls and retries 429s, 5xx errors and timeouts."""

    def __init__(self, source, min_interval, timeout=60):
        self.source = source
        self.min_interval = min_interval
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.last_headers = {}
        self._last_call = 0.0

    def get(self, url, params, quiet=False):
        """Return (http_status, parsed_json_or_None). Never raises on HTTP errors.

        quiet=True skips the per-request INFO line (errors are still logged).
        """
        safe = redact(params)
        for attempt in range(1, MAX_RETRIES + 1):
            wait = self.min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                log.error("%s request failed (attempt %d): %s params=%s",
                          self.source, attempt, mask_secrets(str(exc), params), safe)
                time.sleep(2 ** attempt)
                continue

            self.last_headers = resp.headers
            if not quiet or resp.status_code != 200:
                log.info("%s GET %s -> HTTP %d params=%s", self.source, url, resp.status_code, safe)

            if resp.status_code == 429 or resp.status_code >= 500:
                retry_after = resp.headers.get("Retry-After")
                delay = int(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
                log.warning("%s HTTP %d, retrying in %ds", self.source, resp.status_code, delay)
                time.sleep(delay)
                continue

            try:
                body = resp.json()
            except ValueError:
                log.error("%s returned non-JSON body (HTTP %d): %.200s",
                          self.source, resp.status_code, mask_secrets(resp.text, params))
                return resp.status_code, None

            if resp.status_code != 200:
                log.error("%s HTTP %d error body: %.500s",
                          self.source, resp.status_code, mask_secrets(json.dumps(body), params))
            return resp.status_code, body

        log.error("%s giving up after %d attempts params=%s", self.source, MAX_RETRIES, safe)
        return None, None
