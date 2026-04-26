"""
Module: delta_scraper.py
Zone: 1 (Pre-session — runs alongside genome resolution)
Input: prospect_id, last_scrape_timestamp
Output: dict[str, list[dict]] — {linkedin_posts: [...], instagram_posts: [...]}
LLM calls: 0
Side effects: Calls LinkedIn/Instagram scrapers (network, read-only)
Latency tolerance: 30–60 seconds max. Empty list on failure — delta is always optional.

Lightweight delta scrape: fetches only posts newer than last_scrape_timestamp.
Part of the Signal Delta pipeline. Imported by delta_pipeline.py facade.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


class DeltaScraper:
    """
    Lightweight scrape of new social posts since last_scrape_timestamp.
    Runs in parallel with genome load — 30–60 seconds max.
    Returns empty list on failure — signal delta is always optional.
    """

    async def scrape_since(
        self,
        prospect_id: str,
        last_scrape_timestamp: datetime | None,
    ) -> dict[str, list[dict]]:
        """
        Returns {linkedin_posts: [...], instagram_posts: [...]}
        Only posts newer than last_scrape_timestamp.
        If last_scrape_timestamp is None, scrapes last 30 days.
        """
        from backend.genome.scrape_pipeline.linkedin_scraper import LinkedInScraper
        from backend.genome.scrape_pipeline.instagram_scraper import InstagramScraper

        since_str = (
            last_scrape_timestamp.isoformat()
            if last_scrape_timestamp
            else "30_days_ago"
        )

        li_scraper = LinkedInScraper()
        ig_scraper = InstagramScraper()

        li_delta, ig_delta = await asyncio.gather(
            li_scraper.scrape_delta(prospect_id, since_str),
            ig_scraper.scrape_delta(prospect_id, since_str),
            return_exceptions=True,
        )

        return {
            "linkedin_posts": (
                li_delta.get("recent_posts", [])
                if not isinstance(li_delta, Exception) else []
            ),
            "instagram_posts": (
                ig_delta.get("recent_posts", [])
                if not isinstance(ig_delta, Exception) else []
            ),
        }
