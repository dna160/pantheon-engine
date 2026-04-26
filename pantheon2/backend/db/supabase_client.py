"""
Module: supabase_client.py
Zone: Foundation (db layer)
Input: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY env vars
Output: supabase.Client singleton
LLM calls: 0
Side effects: Opens Supabase connection on first call
Latency tolerance: N/A (import-time singleton)
"""

from __future__ import annotations

import os
from functools import lru_cache

import structlog
from supabase import create_client, Client

logger = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set. "
            "Copy .env.example → .env and fill in values."
        )
    logger.info("supabase.client.initializing", url=url[:40] + "...")
    return create_client(url, key)
