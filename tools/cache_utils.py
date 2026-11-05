"""
Shared caching layer for SemiBot's tool functions.
Caches fetched factor data (not LLM scores) per unique call signature,
with a configurable TTL. This makes repeat analyses of the same ticker
within the TTL window reproducible and fast, while still refreshing
naturally once the cache expires.
"""

import sqlite3
import os
import time
import hashlib
import functools


def _get_cache_db_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'factor_cache.db')


def _init_cache_table():
    conn = sqlite3.connect(_get_cache_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factor_cache (
            cache_key TEXT PRIMARY KEY,
            value TEXT,
            cached_at REAL
        )
    """)
    conn.commit()
    conn.close()


_init_cache_table()


# Strings that indicate a failed fetch — we skip caching these so a transient
# rate limit or API hiccup doesn't poison the cache for 24 hours.
_ERROR_MARKERS = (
    "Data unavailable",
    "Data temporarily unavailable",
    "Too Many Requests",
    "Rate limited",
    "Try after a while",
    "Cannot specify",
    "out-of-bounds",
    "all sources failed",
    "N/A for ",
    "No recent transactions found",  # insider_selling placeholder — not a bearish signal
    "mean score: N/A",  # analyst_ratings placeholder
)

# Short TTL used when we DO cache something that looks slightly suspect
# (e.g. mixed "N/A" fields). Keeps us fresh without hammering APIs.
_SHORT_TTL = 300  # 5 minutes


def _looks_like_error(value: str) -> bool:
    """True if the string looks like a failed fetch / missing-data placeholder
    rather than a real signal. Used both for cache-skip and for the scoring
    guardrail so the LLM never scores an error string as bullish/bearish."""
    if not isinstance(value, str) or not value.strip():
        return True
    if any(m in value for m in _ERROR_MARKERS):
        return True
    # Require OVERWHELMINGLY placeholders before flagging as error, so a
    # mega-cap value like "Market Cap: $1T (ADR N/A)" or a text-heavy
    # geopolitics summary with one 'N/A' sub-metric is not misclassified.
    na_count = value.count("N/A") + value.count("n/a")
    digit_count = sum(c.isdigit() for c in value)
    if na_count >= 3 and digit_count < 2:
        return True
    return False


def cached_tool(ttl_seconds):
    """
    Decorator for caching a tool function's return value.
    Apply UNDER @tool (i.e. @tool goes on top, @cached_tool goes below),
    so the raw function is cached first, then wrapped as a LangChain tool.

    Each call opens and closes its own SQLite connection (not shared across
    threads), so this is safe to use inside a ThreadPoolExecutor.

    Error responses are NOT cached (previously a single rate-limit error
    poisoned the cache for 24h and users kept seeing the same stale error).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key_raw = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_raw.encode()).hexdigest()

            conn = sqlite3.connect(_get_cache_db_path())
            cursor = conn.execute(
                "SELECT value, cached_at FROM factor_cache WHERE cache_key = ?",
                (cache_key,)
            )
            row = cursor.fetchone()
            now = time.time()

            # Serve from cache ONLY if the cached value doesn't look like an
            # error — this lets fresh retries happen after transient failures.
            if row and (now - row[1]) < ttl_seconds and not _looks_like_error(row[0]):
                conn.close()
                return row[0]

            result = func(*args, **kwargs)

            if _looks_like_error(result):
                # Delete any stale error row so the next caller also retries.
                conn.execute("DELETE FROM factor_cache WHERE cache_key = ?", (cache_key,))
                conn.commit()
                conn.close()
                return result

            conn.execute(
                "INSERT OR REPLACE INTO factor_cache (cache_key, value, cached_at) VALUES (?, ?, ?)",
                (cache_key, result, now)
            )
            conn.commit()
            conn.close()
            return result

        return wrapper
    return decorator


def purge_error_cache():
    """One-shot helper to wipe any cached error rows left over from before
    the error-skipping behaviour was added. Safe to call at any time."""
    try:
        conn = sqlite3.connect(_get_cache_db_path())
        cursor = conn.execute("SELECT cache_key, value FROM factor_cache")
        bad = [row[0] for row in cursor.fetchall() if _looks_like_error(row[1])]
        for key in bad:
            conn.execute("DELETE FROM factor_cache WHERE cache_key = ?", (key,))
        conn.commit()
        conn.close()
        return len(bad)
    except Exception:
        return 0


# Standard TTLs used across SemiBot's tools
TTL_SLOW = 86400   # 24 hours - macro, fundamental, and market data (Category 1 + 2)
TTL_FAST = 900      # 15 minutes - live search-based factors (Category 3)
