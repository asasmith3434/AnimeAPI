"""Rate-limited HTTP client for SEC EDGAR.

SEC fair-access rules: max 10 requests/second and a User-Agent header
identifying the requester. https://www.sec.gov/os/accessing-edgar-data
"""

import time

import requests

from .. import config


class EdgarClient:
    def __init__(self, user_agent: str | None = None, min_interval: float | None = None):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent or config.SEC_USER_AGENT
        self.min_interval = (
            min_interval if min_interval is not None else config.SEC_MIN_REQUEST_INTERVAL_SECONDS
        )
        self._last_request_at = 0.0

    def _throttle(self) -> None:
        wait = self._last_request_at + self.min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def get(self, url: str) -> requests.Response:
        self._throttle()
        response = self.session.get(url, timeout=30)
        if response.status_code == 429:
            time.sleep(5)
            self._throttle()
            response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response

    def get_text(self, url: str) -> str:
        return self.get(url).text

    def get_json(self, url: str) -> dict:
        return self.get(url).json()
