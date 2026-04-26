"""
Module: genome_repo.py
Zone: Foundation (db layer)
Input: prospect_id, Genome, MutationLogEntry
Output: Genome | None, MutationLogEntry list
LLM calls: 0
Side effects: Reads/writes prospect_genomes and prospect_mutation_log tables
Latency tolerance: <2s (Zone 1 pre-session only)

Operates on prospect_genomes (v2 individual prospects), NOT agent_genomes (v1 archetypes).
The agent_genomes table from Pantheon v1 is left untouched.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import structlog

from backend.db.supabase_client import get_supabase_client
from backend.genome.parameter_definitions import Genome, ConfidenceLevel, MutationLogEntry

logger = structlog.get_logger(__name__)

TABLE_GENOMES = "prospect_genomes"
TABLE_MUTATIONS = "prospect_mutation_log"


class GenomeRepo:

    def __init__(self) -> None:
        self._client = None  # lazy — initialized on first use

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    # ------------------------------------------------------------------ #
    #  READ                                                                #
    # ------------------------------------------------------------------ #

    def get_by_prospect_id(self, prospect_id: str) -> Optional[Genome]:
        """Returns the most recent genome for a prospect, or None."""
        try:
            resp = (
                self.client.table(TABLE_GENOMES)
                .select("*")
                .eq("prospect_id", prospect_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if resp.data:
                return Genome(**resp.data[0])
            return None
        except Exception as e:
            logger.error("genome_repo.get.error", prospect_id=prospect_id, error=str(e))
            return None

    def get_last_scrape_timestamp(self, prospect_id: str) -> Optional[datetime]:
        """Returns last_scraped_at for the most recent genome row, or None."""
        try:
            resp = (
                self.client.table(TABLE_GENOMES)
                .select("last_scraped_at")
                .eq("prospect_id", prospect_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if resp.data and resp.data[0].get("last_scraped_at"):
                ts_str = resp.data[0]["last_scraped_at"]
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            return None
        except Exception as e:
            logger.error("genome_repo.last_scrape.error", prospect_id=prospect_id, error=str(e))
            return None

    def genome_age_days(self, prospect_id: str) -> Optional[int]:
        """Returns age of most recent genome in days, or None if no genome exists."""
        genome = self.get_by_prospect_id(prospect_id)
        if genome is None or genome.created_at is None:
            return None
        now = datetime.now(timezone.utc)
        created = genome.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return (now - created).days

    def get_mutation_log(self, prospect_id: str) -> list[MutationLogEntry]:
        """Returns all confirmed mutations for a prospect, oldest first."""
        try:
            resp = (
                self.client.table(TABLE_MUTATIONS)
                .select("*")
                .eq("prospect_id", prospect_id)
                .order("confirmed_at", desc=False)
                .execute()
            )
            return [MutationLogEntry(**row) for row in (resp.data or [])]
        except Exception as e:
            logger.error("genome_repo.mutation_log.error", prospect_id=prospect_id, error=str(e))
            return []

    # ------------------------------------------------------------------ #
    #  WRITE                                                               #
    # ------------------------------------------------------------------ #

    def upsert_genome(self, genome: Genome) -> None:
        """Inserts or updates a genome row. Called only from genome_writer after gate approval."""
        try:
            data = genome.model_dump(exclude_none=True)
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            if genome.genome_id:
                self.client.table(TABLE_GENOMES).update(data).eq("genome_id", genome.genome_id).execute()
            else:
                self.client.table(TABLE_GENOMES).insert(data).execute()
            logger.info("genome_repo.upsert.ok", prospect_id=genome.prospect_id)
        except Exception as e:
            logger.error("genome_repo.upsert.error", prospect_id=genome.prospect_id, error=str(e))
            raise

    def append_mutation_log(self, entry: MutationLogEntry) -> None:
        """Appends a confirmed mutation entry to the log table."""
        try:
            data = entry.model_dump(exclude_none=True)
            self.client.table(TABLE_MUTATIONS).insert(data).execute()
            logger.info(
                "genome_repo.mutation_log.appended",
                prospect_id=entry.prospect_id,
                trait=entry.trait_name,
                delta=entry.delta,
            )
        except Exception as e:
            logger.error("genome_repo.mutation_log.error", error=str(e))
            raise
