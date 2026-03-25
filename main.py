"""
main.py — PANTHEON Execution Engine (Modal Orchestrator)
"""
import os
import re
import json
import random
import modal
from pathlib import Path
from typing import Any

from src.utils import DIVIDER, _save_report
from src.genesis import dynamic_seed_agents
from src.semantic_router import evaluate_demographics
from src.nodes.node2 import node2_generate_snapshot, get_image, SECRETS
from src.nodes.node3 import node3_mass_session
from src.nodes.node4 import node4_breakout_room
from src.nodes.node5 import node5_synthesis
from src.presentation import _save_presentation
from src.whisperer import _run_client_whisperer

image = get_image()
job_results = modal.Dict.from_name("pantheon-job-results", create_if_missing=True)
app = modal.App(name="pantheon-engine")

@app.function(image=image, secrets=SECRETS, timeout=120)
def modal_node2(agent: dict) -> dict:
    return node2_generate_snapshot(agent)

@app.function(image=image, secrets=SECRETS, timeout=120)
def modal_node3(dynamic_agent: dict, campaign_brief: str, brief_images: list[str] = []) -> dict:
    return node3_mass_session(dynamic_agent, campaign_brief, brief_images)

@app.function(image=image, secrets=SECRETS, timeout=600)
def modal_node4(group_reactions: list[dict], campaign_brief: str, brief_images: list[str] = []) -> dict:
    return node4_breakout_room(group_reactions, campaign_brief, brief_images)

@app.function(image=image, secrets=SECRETS, timeout=1200)
def modal_node5(mass_reactions: list[dict], breakout_transcripts: list[dict], campaign_brief: str) -> str:
    return node5_synthesis(mass_reactions, breakout_transcripts, campaign_brief)

@app.function(image=image, secrets=SECRETS, timeout=3600)
def run_pipeline_job(job_id: str, target: str, brief: str, client: str = "", limit: int = 10, group_size: int = 5, brief_images: list[str] = []):
    import traceback
    try:
        result = run_pipeline_core(target, brief, client=client, limit=limit, group_size=group_size, brief_images=brief_images)
        job_results[job_id] = result
    except Exception as e:
        job_results[job_id] = {"status": "error", "error": str(e), "trace": traceback.format_exc()}

@app.function(image=image, secrets=SECRETS, timeout=3600)
@modal.asgi_app()
def fastapi_app():
    from fastapi import FastAPI, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    
    web_app = FastAPI(title="PANTHEON API")
    web_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    
    class PipelineRequest(BaseModel):
        target: str
        brief: str
        client: str = ""
        limit: int = 10
        group_size: int = 5
        brief_images: list[str] = []

    class SeedRequest(BaseModel):
        demographic: str
        count: int = 10
        age_min: int = 25
        age_max: int = 45

    @web_app.post("/run_pipeline")
    def api_run_pipeline(req: PipelineRequest):
        import uuid as _uuid
        job_id = str(_uuid.uuid4())
        job_results[job_id] = {"status": "running"}
        run_pipeline_job.spawn(job_id, req.target, req.brief, req.client, req.limit, req.group_size, req.brief_images)
        return {"job_id": job_id}

    @web_app.get("/job/{job_id}")
    def api_job_status(job_id: str):
        try:
            result = job_results.get(job_id)
            if result is None:
                return {"status": "not_found"}
            return result
        except Exception:
            return {"status": "not_found"}

    @web_app.post("/seed")
    def api_seed(req: SeedRequest):
        from supabase import create_client
        import anthropic as _anthropic
        import traceback
        try:
            sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
            ac = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            agents = dynamic_seed_agents(req.demographic, req.count, sb, ac, age_min=req.age_min, age_max=req.age_max)
            return {"seeded": len(agents), "demographic": req.demographic, "agents": agents}
        except Exception as e:
            return {"error": str(e), "trace": traceback.format_exc()}

    @web_app.post("/extract-brief")
    async def api_extract_brief(file: UploadFile):
        import traceback
        from fastapi import UploadFile as _UploadFile
        from src.multimodal import extract_multimodal_brief
        try:
            file_bytes = await file.read()
            ext = (file.filename or "").rsplit(".", 1)[-1].lower()
            result = extract_multimodal_brief(file_bytes, ext)
            return result
        except Exception as e:
            return {"error": str(e), "trace": traceback.format_exc(), "text": "", "images": [], "slide_count": 0}

    @web_app.get("/agents")
    def api_agents(demographic: str = "", limit: int = 50):
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
        q = sb.table("agent_genomes").select(
            "id,target_demographic,age,ethnicity,current_religion,religiosity,"
            "openness,conscientiousness,extraversion,agreeableness,neuroticism,"
            "communication_style,decision_making,identity_fusion,chronesthesia_capacity,"
            "tom_self_awareness,tom_social_modeling,executive_flexibility,"
            "cumulative_cultural_capacity,persona_narrative,"
            "cultural_primary,cultural_secondary,partner_culture,"
            "origin_layer,created_at",
            count="exact"
        )
        if demographic:
            q = q.ilike("target_demographic", f"%{demographic}%")
        result = q.order("created_at", desc=True).limit(limit).execute()
        return {"total": result.count, "agents": result.data}

    return web_app

def _parse_age_range(demographic: str) -> tuple | None:
    """Extract (age_min, age_max) from a demographic string, or return None if not found."""
    m = re.search(r"(\d{1,3})\s*[-\u2013]\s*(\d{1,3})", demographic)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if 5 <= lo < hi <= 100:
            return lo, hi
    # Keyword fallbacks
    s = demographic.lower()
    if any(k in s for k in ("teen", "adolescen", "secondary school")):
        return 13, 19
    if any(k in s for k in ("gen z", "zoomer", "young adult")):
        return 18, 27
    if any(k in s for k in ("children", "kids", "pre-teen")):
        return 8, 12
    return None


def node1_intake_and_query(target_demographic: str, limit: int = 10) -> list[dict]:
    from dotenv import load_dotenv
    from supabase import create_client
    import anthropic as _anthropic

    load_dotenv(".env", override=True)
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    ac = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    parts = [d.strip() for d in target_demographic.split("|") if d.strip()]
    ptm = parts[0] if parts else target_demographic
    stm = parts[1] if len(parts) >= 2 else ""

    # Honour explicit age range from PTM string throughout the pipeline
    age_bounds = _parse_age_range(ptm)
    age_min, age_max = age_bounds if age_bounds else (None, None)

    unique_result = sb.table("agent_genomes").select("target_demographic").execute()
    available_demos = sorted(set(
        row["target_demographic"] for row in unique_result.data
        if row["target_demographic"] is not None
    ))

    approved_demos = evaluate_demographics(ptm, stm, available_demos, ac)
    for d in (ptm, stm):
        if d and d not in approved_demos: approved_demos.append(d)

    # Count agents matching BOTH demographic AND age range
    count_q = sb.table("agent_genomes").select("id", count="exact").in_("target_demographic", approved_demos)
    if age_min is not None:
        count_q = count_q.gte("age", age_min).lte("age", age_max)
    existing_count = (count_q.execute().count) or 0

    deficit = limit - existing_count
    if deficit > 0:
        # Seed with the correct age range so new agents match the request
        dynamic_seed_agents(ptm, deficit, sb, ac, age_min=age_min, age_max=age_max)

    # Pull pool filtered by age range when one is specified
    pool_q = sb.table("agent_genomes").select("*").in_("target_demographic", approved_demos)
    if age_min is not None:
        pool_q = pool_q.gte("age", age_min).lte("age", age_max)
    pool_result = pool_q.limit(500).execute()
    selected = random.sample(pool_result.data, min(limit, len(pool_result.data)))
    return selected

def run_pipeline_core(target: str, brief: str, client: str = "", limit: int = 10, group_size: int = 5, brief_images: list[str] = []):
    print(f"\n{DIVIDER}\n  PANTHEON Orchestrator\n{DIVIDER}")
    if brief_images:
        print(f"  Multimodal: {len(brief_images)} slide image(s) attached")

    agents = node1_intake_and_query(target, limit)
    if not agents: return {"error": "No agents found"}

    dynamic_agents = list(modal_node2.map(agents))
    # Guard: Modal starmap can leak string error objects on individual call failures
    dynamic_agents = [da for da in dynamic_agents if isinstance(da, dict)]

    mass_reactions = list(modal_node3.starmap([(da, brief, brief_images) for da in dynamic_agents]))
    mass_reactions = [r for r in mass_reactions if isinstance(r, dict)]
    if not mass_reactions:
        return {"error": "All Node 3 agent reactions failed — no valid mass reaction data"}

    groups = [mass_reactions[i:i+group_size] for i in range(0, len(mass_reactions), group_size)]
    transcripts = list(modal_node4.starmap([(g, brief, brief_images) for g in groups]))
    transcripts = [t for t in transcripts if isinstance(t, dict)]

    report = modal_node5.remote(mass_reactions, transcripts, brief)

    md_path, base_name = _save_report(report, target, brief, client)
    _save_presentation(md_path, base_name, target, brief, client)
    _run_client_whisperer(md_path, base_name, target, brief, client)

    return {"status": "success", "report": report}

@app.local_entrypoint()
def main(target: str = "Medanese Upper Middle Class, 25-45", brief: str = "Buy-Now-Pay-Later app for rent"):
    run_pipeline_core(target, brief)
