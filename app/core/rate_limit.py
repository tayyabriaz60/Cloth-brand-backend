import time
from collections import deque
from threading import Lock

MAX_LOGIN_FAILURES = 5
LOGIN_WINDOW_SECONDS = 15 * 60


class LoginAttemptLimiter:
    """In-memory failed-login counter.

    Serverless limitation: each Vercel instance has its own memory and instances
    are recycled, so this only slows down brute force on one warm instance. A
    shared store (a DB table) is needed for a real limit across instances.
    """

    def __init__(self, max_failures: int, window_seconds: int) -> None:
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._failures.setdefault(key, deque())
        while attempts and now - attempts[0] > self._window_seconds:
            attempts.popleft()
        return attempts

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.monotonic())) >= self._max_failures

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._prune(key, time.monotonic()).append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = LoginAttemptLimiter(MAX_LOGIN_FAILURES, LOGIN_WINDOW_SECONDS)
