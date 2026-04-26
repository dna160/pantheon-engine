"""
Module: genome_resolver.py
Zone: 1 (Pre-session)
Input: ProspectID (str), HarnessConfig
Output: GenomeBundle (genome: Genome, confidence: ConfidenceLevel)
LLM calls: 0 (this module does not call LLMs — it calls the scrape pipeline)
Side effects: May write to Supabase if fresh scrape completes
Latency tolerance: 3–8 minutes (scrape path), <2s (Supabase hit)

Priority chain:
  PRIORITY 1: Existing genome in Supabase (HIGH confidence)
    → Use if genome age < 90 days AND mutation_log has ≥1 entry
  PRIORITY 2: Fresh scrape (LinkedIn + Instagram) (MEDIUM confidence)
    → Run if no existing genome OR genome age > 90 days
  PRIORITY 3: Manual intake form (LOW confidence)
    → If scrape fails or all profiles are private
"""

from __future__ import annotations

import structlog

from backend.genome.parameter_definitions import Genome, GenomeBundle, ConfidenceLevel
from backend.genome.confidence_scorer import score_confidence, GENOME_STALE_DAYS
from backend.genome.genome_builder import GenomeBuilder
from backend.db.genome_repo import GenomeRepo

logger = structlog.get_logger(__name__)


class GenomeResolver:
    """
    Resolves a genome for a prospect following the priority chain.
    Returns GenomeBundle with resolver_path set to indicate which path was taken.
    """

    def __init__(self) -> None:
        self._db = GenomeRepo()
        self._builder = GenomeBuilder()

    async def resolve(self, prospect_id: str) -> GenomeBundle:
        """
        Runs the priority chain and returns the best available GenomeBundle.
        Never raises — falls back to intake_form path if all else fails.
        """
        # --- Priority 1: Supabase ---
        genome = self._db.get_by_prospect_id(prospect_id)
        if genome is not None:
            age_days = self._db.genome_age_days(prospect_id)
            mutation_count = len(self._db.get_mutation_log(prospect_id))
            confidence = score_confidence(
                resolver_path="supabase",
                mutation_log_count=mutation_count,
                genome_age_days=age_days,
            )
            if age_days is not None and age_days < GENOME_STALE_DAYS:
                logger.info(
                    "genome_resolver.supabase_hit",
                    prospect_id=prospect_id,
                    age_days=age_days,
                    confidence=confidence.value,
                )
                return GenomeBundle(
                    genome=genome,
                    confidence=confidence,
                    resolver_path="supabase",
                )
            else:
                logger.info(
                    "genome_resolver.supabase_stale",
                    prospect_id=prospect_id,
                    age_days=age_days,
                )

        # --- Priority 2: Fresh scrape ---
        try:
            scraped = await self._run_scrape(prospect_id)
            if scraped is not None:
                self._db.upsert_genome(scraped)
                logger.info(
                    "genome_resolver.scrape_success",
                    prospect_id=prospect_id,
                )
                return GenomeBundle(
                    genome=scraped,
                    confidence=ConfidenceLevel.MEDIUM,
                    resolver_path="fresh_scrape",
                )
        except Exception as e:
            logger.warning("genome_resolver.scrape_failed", prospect_id=prospect_id, error=str(e))

        # --- Priority 3: Intake form (stub — returns neutral genome) ---
        logger.warning(
            "genome_resolver.intake_form_fallback",
            prospect_id=prospect_id,
        )
        intake_genome = self._builder.build_from_intake(
            prospect_id=prospect_id,
            intake_answers={},  # Empty = all neutral scores (50)
            confidence=ConfidenceLevel.LOW,
        )
        return GenomeBundle(
            genome=intake_genome,
            confidence=ConfidenceLevel.LOW,
            resolver_path="intake_form",
        )

    async def _run_scrape(self, prospect_id: str) -> Genome | None:
        """
        Runs the full scrape pipeline for a prospect.
        Returns None if scraping fails or profiles are private.
        """
        from backend.genome.scrape_pipeline.linkedin_scraper import LinkedInScraper
        from backend.genome.scrape_pipeline.instagram_scraper import InstagramScraper
        from backend.genome.scrape_pipeline.signal_extractor import SignalExtractor

        li_scraper = LinkedInScraper()
        ig_scraper = InstagramScraper()
        extractor = SignalExtractor()

        import asyncio
        li_data, ig_data = await asyncio.gather(
            li_scraper.scrape(prospect_id),
            ig_scraper.scrape(prospect_id),
            return_exceptions=True,
        )

        if isinstance(li_data, Exception):
            li_data = {}
        if isinstance(ig_data, Exception):
            ig_data = {}

        if not li_data and not ig_data:
            return None

        signals = extractor.extract(
            linkedin_data=li_data,
            instagram_data=ig_data,
        )

        return self._builder.build_from_scrape(
            prospect_id=prospect_id,
            signals={"extracted_signals": signals},
            confidence=ConfidenceLevel.MEDIUM,
        )
