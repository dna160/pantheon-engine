"""
main.py — Pantheon 2.0 FastAPI Backend Entry Point
Zone: API layer (wraps Zone 1 and Zone 3 harness calls)
Zone 2 runs entirely on-device in React Native — no FastAPI routes for live session.

Endpoints:
  POST /session/prepare       Zone 1: genome resolve → cache build → return SessionBundle
  POST /session/close         Zone 3: trigger post-session analysis
  GET  /session/{id}/analysis Zone 3: retrieve mutation candidates + mirror report
  POST /session/{id}/mutation/confirm  Gate-approved mutation write
  GET  /health                Health check
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import structlog
import uuid
from pathlib import Path

from backend.harness.harness_runner import HarnessRunner
from backend.harness.harness_config import load_harness_config
from backend.genome.genome_writer import validate_mutation_gate, apply_confirmed_mutation
from backend.genome.parameter_definitions import MutationCandidate, MutationStrength
from backend.db.genome_repo import GenomeRepo
from backend.db.session_repo import SessionRepo
from backend.session.session_models import SessionRecord, SessionOutcome
from backend.session.session_init import SessionInit

logger = structlog.get_logger(__name__)

# ================================================================== #
#  APP LIFECYCLE                                                       #
# ================================================================== #

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("pantheon2.backend.starting")
    config = load_harness_config()
    app.state.harness = HarnessRunner(config)
    app.state.genome_repo = GenomeRepo()
    app.state.session_repo = SessionRepo()
    yield
    logger.info("pantheon2.backend.shutdown")


app = FastAPI(
    title="Pantheon 2.0 Backend",
    version="2.0.0",
    lifespan=lifespan,
)


# ================================================================== #
#  REQUEST / RESPONSE MODELS                                          #
# ================================================================== #

class PrepareSessionRequest(BaseModel):
    prospect_id: str
    practitioner_id: str


# ── Rich pre-session response models ──────────────────────────────────────────

class PsychFlagResponse(BaseModel):
    flag_id: str
    severity: str
    flag_type: str
    message: str
    recommendation: str
    requires_acknowledgment: bool


class ConfidenceBadgeResponse(BaseModel):
    level: str
    label: str
    color: str          # "green" | "yellow" | "red" (never "amber")


class RWIResponse(BaseModel):
    score: int
    window_status: str
    components: dict
    prospect_id: str


class PrepareSessionResponse(BaseModel):
    session_id: str
    prospect_id: str
    prospect_name: str
    role: str
    company: str
    confidence_badge: ConfidenceBadgeResponse
    rwi: RWIResponse
    psych_flags: list[PsychFlagResponse]
    unacknowledged_flag_ids: list[str]
    can_start: bool
    cache_built: bool
    genome_validity_score: str
    ecological_validity_score: str
    summary: str


# ── Session lifecycle models ───────────────────────────────────────────────────

class CloseSessionRequest(BaseModel):
    session_id: str
    prospect_id: str
    practitioner_id: str
    outcome: str  # "close_yes" | "close_no" | "follow_up" | "incomplete"


class StartSessionRequest(BaseModel):
    prospect_id: str
    practitioner_id: str = ""


class EndSessionRequest(BaseModel):
    outcome: str = "follow_up"  # "close_yes" | "close_no" | "follow_up" | "incomplete"


class AcknowledgeFlagRequest(BaseModel):
    flag_id: str


class RespondMutationRequest(BaseModel):
    candidate_id: str
    decision: str   # "confirm" | "dismiss"


class ConfirmMutationRequest(BaseModel):
    session_id: str
    prospect_id: str
    practitioner_id: str
    trait_name: str
    suggested_delta: int
    evidence: list[str]
    observation_day_span: int
    context_count: int
    has_cold_context_signal: bool


# ================================================================== #
#  ROUTES                                                             #
# ================================================================== #

@app.get("/health")
async def health():
    return {"status": "ok", "service": "pantheon2-backend"}


@app.post("/session/prepare", response_model=PrepareSessionResponse)
async def prepare_session(req: PrepareSessionRequest):
    """
    Zone 1: Full pre-session pipeline.
    Genome resolve → signal delta → RWI → psych review → cache build.
    Returns rich PreSessionScreen payload including confidence badge,
    RWI object, psych flags, and GO-gate state.
    """
    session_id = str(uuid.uuid4())

    try:
        bundle = await app.state.harness.prepare_session(
            session_id=session_id,
            prospect_id=req.prospect_id,
            practitioner_id=req.practitioner_id,
        )

        # Open session record in DB
        session_record = SessionRecord(
            session_id=session_id,
            practitioner_id=req.practitioner_id,
            prospect_id=req.prospect_id,
            genome_confidence=bundle.genome_bundle.confidence.value,
            rwi_at_start=bundle.rwi.score,
        )
        app.state.session_repo.create_session(session_record)

        # Build rich screen payload via SessionInit
        screen_payload = SessionInit().build_screen_payload(bundle)

        # Extract psych review scores from psych_report
        psych_report = bundle.psych_report or {}
        genome_validity = psych_report.get("genome_validity_score", "PARTIAL")
        eco_validity = psych_report.get("ecological_validity_score", "PARTIAL")
        summary = psych_report.get("summary", "Adversarial review complete.")

        rwi = bundle.rwi
        rwi_components = getattr(rwi, "components", None)
        if rwi_components is not None:
            components_dict = {
                "validation_recency": getattr(rwi_components, "validation_recency", 0),
                "friction_saturation": getattr(rwi_components, "friction_saturation", 0),
                "decision_fatigue_estimate": getattr(rwi_components, "decision_fatigue_estimate", 0),
                "identity_momentum": getattr(rwi_components, "identity_momentum", 0),
            }
        else:
            components_dict = {}

        return PrepareSessionResponse(
            session_id=session_id,
            prospect_id=req.prospect_id,
            prospect_name=req.prospect_id,   # TODO: enrich from CRM / genome metadata
            role="",
            company="",
            confidence_badge=ConfidenceBadgeResponse(
                level=screen_payload.confidence_badge.level,
                label=screen_payload.confidence_badge.label,
                color=screen_payload.confidence_badge.color,
            ),
            rwi=RWIResponse(
                score=int(rwi.score),
                window_status=rwi.window_status,
                components=components_dict,
                prospect_id=req.prospect_id,
            ),
            psych_flags=[
                PsychFlagResponse(
                    flag_id=f.flag_id,
                    severity=f.severity,
                    flag_type=f.flag_type,
                    message=f.message,
                    recommendation=f.recommendation,
                    requires_acknowledgment=f.requires_acknowledgment,
                )
                for f in screen_payload.psych_flags
            ],
            unacknowledged_flag_ids=screen_payload.unacknowledged_flag_ids,
            can_start=not screen_payload.requires_acknowledgment,
            cache_built=not screen_payload.is_fallback_cache,
            genome_validity_score=genome_validity,
            ecological_validity_score=eco_validity,
            summary=summary,
        )

    except Exception as e:
        logger.error("api.prepare_session.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/close")
async def close_session(req: CloseSessionRequest):
    """
    Zone 3: Triggered when practitioner ends the session.
    Closes session record, triggers async post-session analysis.
    Analysis results retrieved separately via GET /session/{id}/analysis.
    """
    import asyncio

    try:
        outcome = SessionOutcome(req.outcome)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid outcome: {req.outcome}")

    app.state.session_repo.close_session(req.session_id, outcome)

    # Trigger Zone 3 analysis asynchronously — don't block the response
    asyncio.create_task(
        app.state.harness.analyze_session(
            session_id=req.session_id,
            prospect_id=req.prospect_id,
            practitioner_id=req.practitioner_id,
        )
    )

    return {"status": "session_closed", "session_id": req.session_id}


@app.get("/session/{session_id}/analysis")
async def get_session_analysis(session_id: str):
    """
    Returns Zone 3 analysis results: mutation candidates + mirror report.
    Called by mobile app to render MutationReviewScreen and MirrorReportScreen.
    """
    # Analysis is stored in local cache by harness_runner after completion
    import json
    from pathlib import Path

    cache_path = Path(f"./session_cache/{session_id}_analysis.json")
    if not cache_path.exists():
        return {"status": "pending", "message": "Analysis in progress"}

    with open(cache_path) as f:
        return json.load(f)


@app.post("/session/{session_id}/mutation/confirm")
async def confirm_mutation(session_id: str, req: ConfirmMutationRequest):
    """
    Gate-approved mutation write. Called after practitioner taps 'Confirm' in app.
    Validates gate conditions server-side before any genome write.
    """
    genome = app.state.genome_repo.get_by_prospect_id(req.prospect_id)
    if not genome:
        raise HTTPException(status_code=404, detail="Genome not found")

    candidate = MutationCandidate(
        prospect_id=req.prospect_id,
        trait_name=req.trait_name,
        current_score=getattr(genome, req.trait_name),
        suggested_delta=req.suggested_delta,
        suggested_new_score=max(1, min(100, getattr(genome, req.trait_name) + req.suggested_delta)),
        evidence=req.evidence,
        strength=MutationStrength.MODERATE,
    )

    from backend.genome.parameter_definitions import MutationDecision
    gate_result = validate_mutation_gate(
        candidate=candidate,
        existing_log=[],
        has_cold_context_signal=req.has_cold_context_signal,
        observation_day_span=req.observation_day_span,
        context_count=req.context_count,
    )

    if gate_result != MutationDecision.APPROVED:
        raise HTTPException(
            status_code=422,
            detail=f"Mutation gate rejected: {gate_result.value}. "
                   "Minimum: 3+ observations, 2+ contexts, 21+ day span, 1 cold-context signal.",
        )

    updated_genome, log_entry = apply_confirmed_mutation(
        genome=genome,
        candidate=candidate,
        practitioner_id=req.practitioner_id,
        observation_day_span=req.observation_day_span,
        context_count=req.context_count,
        has_cold_context_signal=req.has_cold_context_signal,
    )

    app.state.genome_repo.upsert_genome(updated_genome)
    app.state.genome_repo.append_mutation_log(log_entry)

    logger.info(
        "api.mutation.confirmed",
        trait=req.trait_name,
        delta=req.suggested_delta,
        practitioner=req.practitioner_id,
    )

    return {
        "status": "mutation_applied",
        "trait": req.trait_name,
        "old_score": candidate.current_score,
        "new_score": candidate.suggested_new_score,
    }


# ================================================================== #
#  B1 — SESSION START (Zone 1 → Zone 2 transition)                    #
# ================================================================== #

@app.post("/session/start")
async def start_session(req: StartSessionRequest):
    """
    Zone 1 → Zone 2 transition. Practitioner pressed GO.
    Validates a prepared session exists, returns session_id for WS connection.
    """
    session = app.state.session_repo.get_session_by_prospect_id(req.prospect_id)
    if session is None:
        # Fallback: some implementations store by prospect_id, others by session_id
        raise HTTPException(
            status_code=404,
            detail=f"No prepared session found for prospect '{req.prospect_id}'. "
                   "Call POST /session/prepare first.",
        )
    return {"session_id": session.session_id, "started": True}


# ================================================================== #
#  B2 — SESSION END (Zone 2 → Zone 3 transition)                      #
# ================================================================== #

@app.post("/session/{session_id}/end")
async def end_session(session_id: str, req: EndSessionRequest):
    """
    Zone 2 → Zone 3 transition. Practitioner tapped END.
    Closes session record and triggers async Zone 3 analysis.
    """
    try:
        outcome = SessionOutcome(req.outcome)
    except ValueError:
        outcome = SessionOutcome.FOLLOW_UP

    app.state.session_repo.close_session(session_id, outcome)

    # Retrieve session record for prospect/practitioner IDs
    session_rec = app.state.session_repo.get_session(session_id)
    if session_rec:
        asyncio.create_task(
            app.state.harness.analyze_session(
                session_id=session_id,
                prospect_id=session_rec.prospect_id,
                practitioner_id=session_rec.practitioner_id,
            )
        )

    return {"status": "session_ended", "session_id": session_id}


# ================================================================== #
#  B3 — ACKNOWLEDGE PSYCH FLAG                                         #
# ================================================================== #

@app.post("/session/acknowledge_flag")
async def acknowledge_flag(req: AcknowledgeFlagRequest):
    """
    Records practitioner acknowledgment of a HIGH severity psych flag.
    Non-blocking audit trail — GO-gate logic is enforced client-side.
    """
    logger.info("session.flag_acknowledged", flag_id=req.flag_id)
    return {"acknowledged": True, "flag_id": req.flag_id}


# ================================================================== #
#  B4 — MIRROR REPORT (Zone 3 — post-session only)                    #
# ================================================================== #

@app.get("/session/{session_id}/mirror_report")
async def get_mirror_report(session_id: str):
    """
    Returns the Mirror Report for a completed session.
    Only available after Zone 3 analysis writes the cache file.
    NEVER called during Zone 2 (Critical Constraint #6).
    """
    cache_path = Path(f"./session_cache/{session_id}_analysis.json")
    if not cache_path.exists():
        return {"status": "pending", "message": "Analysis not yet complete"}

    with open(cache_path) as f:
        analysis = json.load(f)

    mirror = analysis.get("mirror_report", {})
    profile_context = analysis.get("profile_context", {})
    outcome_log = analysis.get("outcome_log", {})

    return {
        "session_id": session_id,
        "practitioner_id": analysis.get("practitioner_id", ""),
        # Flat observation fields for MirrorReportScreen
        "what_worked": mirror.get("signature_strength", "Analysis unavailable."),
        "what_didnt": mirror.get("blind_spot", "Analysis unavailable."),
        "pattern_detected": mirror.get("instinct_ratio", "Analysis unavailable."),
        "next_session_focus": mirror.get("pressure_signature", "Analysis unavailable."),
        # Session stats
        "session_duration_min": outcome_log.get("duration_min", 0),
        "moment_count": outcome_log.get("moment_count", 0),
        "option_choices": outcome_log.get("option_choices", 0),
        "divergence_count": outcome_log.get("divergence_count", 0),
        # Practitioner profile excerpt
        "strengths": profile_context.get("strengths", []),
        "development_areas": profile_context.get("development_areas", []),
        # Nested structure preserved for compatibility
        "observations": mirror,
        "profile_context": profile_context,
        "is_fallback": analysis.get("is_fallback", False),
    }


# ================================================================== #
#  B5 — MUTATION RESPOND (replaces /mutation/confirm for mobile)      #
# ================================================================== #

@app.post("/session/{session_id}/mutation/respond")
async def respond_to_mutation(session_id: str, req: RespondMutationRequest):
    """
    Practitioner confirm or dismiss for a single mutation candidate.
    'confirm' triggers gate validation and genome write.
    'dismiss' is logged only — no genome change.
    """
    if req.decision == "dismiss":
        logger.info("mutation.dismissed", session_id=session_id, candidate_id=req.candidate_id)
        return {"status": "dismissed", "candidate_id": req.candidate_id}

    # confirm: load candidate from analysis cache
    cache_path = Path(f"./session_cache/{session_id}_analysis.json")
    if not cache_path.exists():
        raise HTTPException(status_code=404, detail="Analysis cache not found for this session")

    with open(cache_path) as f:
        analysis = json.load(f)

    candidates = analysis.get("mutation_candidates", [])
    candidate_data = next(
        (c for c in candidates if c.get("candidate_id") == req.candidate_id),
        None,
    )
    if not candidate_data:
        raise HTTPException(status_code=404, detail=f"Candidate '{req.candidate_id}' not found")

    genome = app.state.genome_repo.get_by_prospect_id(candidate_data["prospect_id"])
    if not genome:
        raise HTTPException(status_code=404, detail="Genome not found")

    candidate = MutationCandidate(
        prospect_id=candidate_data["prospect_id"],
        trait_name=candidate_data["trait_name"],
        current_score=candidate_data.get(
            "current_score", getattr(genome, candidate_data["trait_name"], 50)
        ),
        suggested_delta=candidate_data.get("suggested_delta", 0),
        suggested_new_score=candidate_data.get("suggested_new_score", 50),
        evidence=candidate_data.get("evidence", []),
        strength=MutationStrength(candidate_data.get("strength", "MODERATE")),
        is_coherence_tension=candidate_data.get("is_coherence_tension", False),
    )

    from backend.genome.parameter_definitions import MutationDecision
    gate_result = validate_mutation_gate(
        candidate=candidate,
        existing_log=[],
        has_cold_context_signal=candidate_data.get("has_cold_context_signal", False),
        observation_day_span=candidate_data.get("observation_day_span", 0),
        context_count=candidate_data.get("context_count", 1),
    )

    if gate_result != MutationDecision.APPROVED:
        logger.warning(
            "mutation.gate_rejected_after_confirm",
            candidate_id=req.candidate_id,
            gate_result=gate_result.value,
        )
        return {
            "status": "gate_rejected",
            "candidate_id": req.candidate_id,
            "gate_result": gate_result.value,
            "message": f"Gate condition not met: {gate_result.value}. Candidate archived.",
        }

    updated_genome, log_entry = apply_confirmed_mutation(
        genome=genome,
        candidate=candidate,
        practitioner_id=analysis.get("practitioner_id", "unknown"),
        observation_day_span=candidate_data.get("observation_day_span", 0),
        context_count=candidate_data.get("context_count", 1),
        has_cold_context_signal=candidate_data.get("has_cold_context_signal", False),
    )

    app.state.genome_repo.upsert_genome(updated_genome)
    app.state.genome_repo.append_mutation_log(log_entry)

    return {
        "status": "confirmed",
        "candidate_id": req.candidate_id,
        "trait": candidate.trait_name,
        "old_score": candidate.current_score,
        "new_score": candidate.suggested_new_score,
    }


# ================================================================== #
#  B6 — WEBSOCKET ENDPOINTS                                            #
# ================================================================== #

# In-memory connection registries (per session, Zone 2 lifetime only)
_hud_connections: dict[str, WebSocket] = {}
_audio_connections: dict[str, WebSocket] = {}


@app.websocket("/ws/hud/{session_id}")
async def hud_websocket(websocket: WebSocket, session_id: str):
    """
    Zone 2 HUD WebSocket — phone_driver pushes state here.
    React Native HUDStateManager subscribes to receive updates.
    Server → client only; client messages are ignored.
    """
    await websocket.accept()
    _hud_connections[session_id] = websocket
    logger.info("ws.hud.connected", session_id=session_id)
    try:
        while True:
            # Keep alive — data flows server → client only
            await websocket.receive_text()
    except WebSocketDisconnect:
        _hud_connections.pop(session_id, None)
        logger.info("ws.hud.disconnected", session_id=session_id)


@app.websocket("/ws/audio/{session_id}")
async def audio_websocket(websocket: WebSocket, session_id: str):
    """
    Zone 2 audio ingestion WebSocket.
    React Native AudioStreamer sends 50ms PCM16 chunks here.
    TODO Phase 6: wire to session_runner audio_bridge.receive_bytes(session_id, chunk)
    """
    await websocket.accept()
    _audio_connections[session_id] = websocket
    logger.info("ws.audio.connected", session_id=session_id)
    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            _ = audio_chunk   # Phase 6: route to audio bridge
    except WebSocketDisconnect:
        _audio_connections.pop(session_id, None)
        logger.info("ws.audio.disconnected", session_id=session_id)


async def send_hud_state(session_id: str, state: dict) -> None:
    """
    Called by phone_driver emitter to push HUD state to the connected React Native client.
    Non-blocking — silently drops on connection error.
    """
    ws = _hud_connections.get(session_id)
    if ws is not None:
        try:
            await ws.send_text(json.dumps(state))
        except Exception as e:
            logger.warning("ws.hud.send_error", session_id=session_id, error=str(e))
            _hud_connections.pop(session_id, None)
