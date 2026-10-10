"""Bounded, per-client admin login throttle.

This in-memory guard is a defense-in-depth layer for one API process, not a
distributed/global rate limiter. Add a shared datastore if more workers start.
Do not key on a password, store credentials or trust X-Forwarded-For here.
"""
from collections import deque
from threading import Lock
from time import monotonic


class AdminLoginThrottle:
    def __init__(self, max_failures: int = 8, window_seconds: int = 300, max_peers: int = 2048):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.max_peers = max_peers
        self._attempts = {}
        self._lock = Lock()

    def _clean(self, values, now):
        while values and values[0] <= now - self.window_seconds:
            values.popleft()

    def _prune(self, now):
        for key in list(self._attempts):
            values = self._attempts[key]
            self._clean(values, now)
            if not values:
                del self._attempts[key]
        if len(self._attempts) >= self.max_peers:
            # When overloaded, evict oldest recent client rather than
            # allowing unbounded memory growth from spoofed source addresses.
            oldest = min(self._attempts, key=lambda k: self._attempts[k][-1])
            del self._attempts[oldest]

    def blocked(self, peer: str, now: float | None = None) -> bool:
        moment = monotonic() if now is None else now
        key = str(peer or "unknown")[:128]
        with self._lock:
            attempts = self._attempts.get(key)
            if not attempts:
                return False
            self._clean(attempts, moment)
            if not attempts:
                self._attempts.pop(key, None)
                return False
            return len(attempts) >= self.max_failures

    def fail(self, peer: str, now: float | None = None) -> None:
        moment = monotonic() if now is None else now
        key = str(peer or "unknown")[:128]
        with self._lock:
            if key not in self._attempts:
                if len(self._attempts) >= self.max_peers:
                    self._prune(moment)
                self._attempts[key] = deque()
            values = self._attempts[key]
            self._clean(values, moment)
            values.append(moment)

    def success(self, peer: str) -> None:
        with self._lock:
            self._attempts.pop(str(peer or "unknown")[:128], None)


owner_login_guard = AdminLoginThrottle()
