"""
Very small in-memory brute-force limiter.

Counts FAILED attempts per key (for example "ip|email"). After too many
failures the key is locked for a while. It is per-process memory, which is
fine for a single development server. A production deployment with several
workers should use a shared store (for example Redis).
"""

import threading
import time

_lock = threading.Lock()
_failures = {}  # key -> list of failure timestamps


def _prune(key, window_seconds, now):
    recent = [t for t in _failures.get(key, []) if now - t < window_seconds]
    if recent:
        _failures[key] = recent
    else:
        _failures.pop(key, None)
    return recent


def is_locked(key, max_failures, window_minutes):
    now = time.time()
    with _lock:
        recent = _prune(key, window_minutes * 60, now)
        return len(recent) >= max_failures


def record_failure(key, window_minutes):
    now = time.time()
    with _lock:
        _prune(key, window_minutes * 60, now)
        _failures.setdefault(key, []).append(now)


def clear(key):
    with _lock:
        _failures.pop(key, None)


def reset_all():
    """Used by tests."""
    with _lock:
        _failures.clear()
