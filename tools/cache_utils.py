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


def cached_tool(ttl_seconds):
    """
    Decorator for caching a tool function's return value.
    Apply UNDER @tool (i.e. @tool goes on top, @cached_tool goes below),
    so the raw function is cached first, then wrapped as a LangChain tool.

    Each call opens and closes its own SQLite connection (not shared across
    threads), so this is safe to use inside a ThreadPoolExecutor.
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

            if row and (now - row[1]) < ttl_seconds:
                conn.close()
                return row[0]

            result = func(*args, **kwargs)

            conn.execute(
                "INSERT OR REPLACE INTO factor_cache (cache_key, value, cached_at) VALUES (?, ?, ?)",
                (cache_key, result, now)
            )
            conn.commit()
            conn.close()
            return result

        return wrapper
    return decorator


# Standard TTLs used across SemiBot's tools
TTL_SLOW = 86400   # 24 hours - macro, fundamental, and market data (Category 1 + 2)
TTL_FAST = 900      # 15 minutes - live search-based factors (Category 3)
