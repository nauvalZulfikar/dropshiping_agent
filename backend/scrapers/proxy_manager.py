"""
Proxy rotation manager.
Loads proxies from PROXY_LIST env var (comma-separated host:port:user:pass).
Falls back to direct connection if no proxies configured.
"""
import time
import threading
import logging
from collections import deque
from typing import Optional

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_FAILED_COOLDOWN_SECONDS = 600  # 10 minutes


class ProxyManager:
    """
    Round-robin proxy rotation with failure tracking.
    Thread-safe via a lock.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._proxies: deque[dict] = deque()
        self._failed: dict[str, float] = {}  # proxy_key → failed_at timestamp

        raw_proxies = settings.proxy_list_parsed
        for p in raw_proxies:
            self._proxies.append(p)

        if self._proxies:
            logger.info(f"ProxyManager initialized with {len(self._proxies)} proxies")
        else:
            logger.info("ProxyManager: no proxies configured, using direct connection")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_proxy(self) -> Optional[dict]:
        """
        Return next available proxy in round-robin order.
        Skips proxies that are in the failed/cooldown list.
        Returns None if no proxies configured (use direct connection).
        """
        if not self._proxies:
            return None

        with self._lock:
            # Try each proxy once
            for _ in range(len(self._proxies)):
                proxy = self._proxies[0]
                self._proxies.rotate(-1)  # move to end (round-robin)
                key = self._proxy_key(proxy)
                if self._is_available(key):
                    return proxy
            # All proxies are in cooldown — return first one anyway
            logger.warning("All proxies in cooldown, using first proxy anyway")
            return self._proxies[0]

    def mark_failed(self, proxy: dict):
        """Mark a proxy as failed; it will be skipped for _FAILED_COOLDOWN_SECONDS."""
        key = self._proxy_key(proxy)
        with self._lock:
            self._failed[key] = time.monotonic()
            logger.warning(f"Proxy marked failed: {proxy['host']}:{proxy['port']}")

    def mark_success(self, proxy: dict):
        """Clear a proxy from the failed list after a successful request."""
        key = self._proxy_key(proxy)
        with self._lock:
            self._failed.pop(key, None)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _proxy_key(self, proxy: dict) -> str:
        return f"{proxy['host']}:{proxy['port']}"

    def _is_available(self, key: str) -> bool:
        failed_at = self._failed.get(key)
        if failed_at is None:
            return True
        elapsed = time.monotonic() - failed_at
        if elapsed >= _FAILED_COOLDOWN_SECONDS:
            del self._failed[key]
            return True
        return False
