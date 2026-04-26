"""
Module: session_repo.py
Zone: Foundation (db layer) — used in Zone 1, 2, and 3
Input: SessionRecord, SessionEvent, ParalinguisticSnapshot
Output: SessionRecord, list[SessionEvent], list[ParalinguisticSnapshot]
LLM calls: 0
Side effects: Reads/writes sessions, session_events, paralinguistic_snapshots tables
Latency tolerance: Zone 2 writes are fire-and-forget (non-blocking). Zone 1/3 reads are synchronous.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
import structlog

from backend.db.supabase_client import get_supabase_client
from backend.session.session_models import SessionRecord, SessionEvent, ParalinguisticSnapshot, SessionOutcome

logger = structlog.get_logger(__name__)

TABLE_SESSIONS = "sessions"
TABLE_EVENTS = "session_events"
TABLE_PARA = "paralinguistic_snapshots"


class SessionRepo:

    def __init__(self) -> None:
        self._client = None  # lazy — initialized on first use

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    # ------------------------------------------------------------------ #
    #  SESSION LIFECYCLE                                                   #
    # ------------------------------------------------------------------ #

    def create_session(self, record: SessionRecord) -> None:
        """Opens a session record at Zone 1 start."""
        try:
            self.client.table(TABLE_SESSIONS).insert(record.model_dump(exclude_none=True)).execute()
            logger.info("session_repo.create.ok", session_id=record.session_id)
        except Exception as e:
            logger.error("session_repo.create.error", session_id=record.session_id, error=str(e))
            raise

    def close_session(self, session_id: str, outcome: SessionOutcome) -> None:
        """Closes a session record at Zone 3 start."""
        try:
            self.client.table(TABLE_SESSIONS).update({
                "outcome": outcome.value,
                "closed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("session_id", session_id).execute()
            logger.info("session_repo.close.ok", session_id=session_id, outcome=outcome.value)
        except Exception as e:
            logger.error("session_repo.close.error", session_id=session_id, error=str(e))
            raise

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        try:
            resp = (
                self.client.table(TABLE_SESSIONS)
                .select("*")
                .eq("session_id", session_id)
                .limit(1)
                .execute()
            )
            if resp.data:
                return SessionRecord(**resp.data[0])
            return None
        except Exception as e:
            logger.error("session_repo.get.error", session_id=session_id, error=str(e))
            return None

    def get_session_by_prospect_id(self, prospect_id: str) -> Optional[SessionRecord]:
        """Returns the most recent open session for a prospect_id."""
        try:
            resp = (
                self.client.table(TABLE_SESSIONS)
                .select("*")
                .eq("prospect_id", prospect_id)
                .is_("closed_at", "null")   # only open sessions
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if resp.data:
                return SessionRecord(**resp.data[0])
            return None
        except Exception as e:
            logger.error("session_repo.get_by_prospect.error", prospect_id=prospect_id, error=str(e))
            return None

    # ------------------------------------------------------------------ #
    #  EVENTS (Zone 2 writes — fire and forget, never block)              #
    # ------------------------------------------------------------------ #

    def append_event(self, event: SessionEvent) -> None:
        """Appends a session event. Zone 2 calls this non-blocking."""
        try:
            self.client.table(TABLE_EVENTS).insert(event.model_dump(exclude_none=True)).execute()
        except Exception as e:
            logger.warning("session_repo.event.error", session_id=event.session_id, error=str(e))

    def get_session_events(self, session_id: str) -> list[SessionEvent]:
        """Returns all events for a session, ordered by timestamp."""
        try:
            resp = (
                self.client.table(TABLE_EVENTS)
                .select("*")
                .eq("session_id", session_id)
                .order("event_timestamp", desc=False)
                .execute()
            )
            return [SessionEvent(**row) for row in (resp.data or [])]
        except Exception as e:
            logger.error("session_repo.events.get.error", session_id=session_id, error=str(e))
            return []

    # ------------------------------------------------------------------ #
    #  PARALINGUISTIC SNAPSHOTS                                            #
    # ------------------------------------------------------------------ #

    def append_paralinguistic_snapshot(self, snapshot: ParalinguisticSnapshot) -> None:
        """Appends a 30s paralinguistic snapshot. Non-blocking in Zone 2."""
        try:
            self.client.table(TABLE_PARA).insert(snapshot.model_dump(exclude_none=True)).execute()
        except Exception as e:
            logger.warning("session_repo.para.error", session_id=snapshot.session_id, error=str(e))

    def get_paralinguistic_snapshots(self, session_id: str) -> list[ParalinguisticSnapshot]:
        """Returns all paralinguistic snapshots for a session."""
        try:
            resp = (
                self.client.table(TABLE_PARA)
                .select("*")
                .eq("session_id", session_id)
                .order("captured_at", desc=False)
                .execute()
            )
            return [ParalinguisticSnapshot(**row) for row in (resp.data or [])]
        except Exception as e:
            logger.error("session_repo.para.get.error", session_id=session_id, error=str(e))
            return []
