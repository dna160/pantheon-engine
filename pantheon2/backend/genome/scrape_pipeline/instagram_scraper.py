"""
Module: instagram_scraper.py
Zone: 1 (Pre-session — called by genome_resolver scrape path)
Input: prospect_id str
Output: dict with recent_posts, bio, avg_engagement_rate
LLM calls: 0
Side effects: Network requests to Instagram (Playwright)
Latency tolerance: 30–120 seconds

Playwright stub — same pattern as linkedin_scraper.py.
"""

from __future__ import annotations

import structlog
from typing import Any

logger = structlog.get_logger(__name__)


class InstagramScraper:
    """
    Scrapes an Instagram profile for recent posts and paralinguistic signals.
    Visual content signals (image type, caption tone) included when available.
    """

    async def scrape(self, prospect_id: str) -> dict[str, Any]:
        """Full profile scrape — last 30 days."""
        logger.info("instagram_scraper.scrape.start", prospect_id=prospect_id)
        try:
            return await self._scrape_impl(prospect_id, since="30_days_ago")
        except Exception as e:
            logger.warning("instagram_scraper.scrape.failed", prospect_id=prospect_id, error=str(e))
            return {}

    async def scrape_delta(self, prospect_id: str, since: str) -> dict[str, Any]:
        """Delta scrape: only posts newer than `since`."""
        logger.info("instagram_scraper.delta.start", prospect_id=prospect_id, since=since)
        try:
            return await self._scrape_impl(prospect_id, since=since)
        except Exception as e:
            logger.warning("instagram_scraper.delta.failed", prospect_id=prospect_id, error=str(e))
            return {"recent_posts": []}

    async def _scrape_impl(self, prospect_id: str, since: str) -> dict[str, Any]:
        """
        Playwright stub.

        Expected output shape:
        {
            "prospect_id": str,
            "bio": str,
            "recent_posts": [{"caption": str, "timestamp": str, "likes": int, "comments": int}, ...],
            "avg_engagement_rate": float,
        }
        """
        logger.warning(
            "instagram_scraper.stub_mode",
            prospect_id=prospect_id,
            note="Playwright not configured. Returning empty data.",
        )
        return {
            "prospect_id": prospect_id,
            "bio": "",
            "recent_posts": [],
            "avg_engagement_rate": 0.0,
        }
