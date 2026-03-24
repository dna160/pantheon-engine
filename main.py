"""
main.py — PANTHEON Execution Engine (Modal Orchestrator)
"""
import os
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
def modal_node3(dynamic_agent: dict, campaign_brief: str) -> dict:
    return node3_mass_session(dynamic_agent, campaign_brief)

@app.function(image=image, secrets=SECRETS, timeout=600)
def modal_node4(group_reactions: list[dict], campaign_brief: str) -> dict:
    return node4_breakout_room(group_reactions, campaign_brief)

@app.function(image=image, secrets=SECRETS, timeout=1200)
def modal_node5(mass_reactions: list[dict], breakout_transcripts: list[dict], campaign_brief: str) -> str:
    return node5_synthesis(mass_reactions, breakout_transcripts, campaign_brief)

@app.function(image=image, secrets=SECRETS, timeout=3600)
def run_pipeline_job(job_id: str, target: str, brief: str, client: str = "", limit: int = 10, group_size: int = 5):
    import traceback
    try:
        result = run_pipeline_core(target, brief, client=client, limit=limit, group_size=group_size)
        job_results[job_id] = result
    except Exception as e:
        job_results[job_id] = {"status": "error", "error": str(e), "trace": traceback.format_exc()}

@app.function(image=image, secrets=SECRETS, timeout=3600)
@modal.asgi_app()
def fastapi_app():
    from fastapi import FastAPI
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
        run_pipeline_job.spawn(job_id, req.target, req.brief, req.client, req.limit, req.group_size)
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
            agents = dynamic_seed_agents(req.demographic, req.count, sb, ac)
            return {"seeded": len(agents), "demographic": req.demographic, "agents": agents}
        except Exception as e:
            return {"error": str(e), "trace": traceback.format_exc()}

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

    unique_result = sb.table("agent_genomes").select("target_demographic").execute()
    available_demos = sorted(set(
        row["target_demographic"] for row in unique_result.data
        if row["target_demographic"] is not None
    ))
    
    approved_demos = evaluate_demographics(ptm, stm, available_demos, ac)
    for d in (ptm, stm):
        if d and d not in approved_demos: approved_demos.append(d)

    count_result = sb.table("agent_genomes").select("id", count="exact").in_("target_demographic", approved_demos).execute()
    existing_count = count_result.count or 0
    
    deficit = limit - existing_count
    if deficit > 0:
        dynamic_seed_agents(ptm, deficit, sb, ac)

    pool_result = sb.table("agent_genomes").select("*").in_("target_demographic", approved_demos).limit(500).execute()
    selected = random.sample(pool_result.data, min(limit, len(pool_result.data)))
    return selected

def run_pipeline_core(target: str, brief: str, client: str = "", limit: int = 10, group_size: int = 5):
    print(f"\n{DIVIDER}\n  PANTHEON Orchestrator\n{DIVIDER}")
    
    agents = node1_intake_and_query(target, limit)
    if not agents: return {"error": "No agents found"}

    dynamic_agents = list(modal_node2.map(agents))
    mass_reactions = list(modal_node3.starmap([(da, brief) for da in dynamic_agents]))
    
    groups = [mass_reactions[i:i+group_size] for i in range(0, len(mass_reactions), group_size)]
    transcripts = list(modal_node4.starmap([(g, brief) for g in groups]))
    
    report = modal_node5.remote(mass_reactions, transcripts, brief)
    
    md_path, base_name = _save_report(report, target, brief, client)
    _save_presentation(md_path, base_name, target, brief, client)
    _run_client_whisperer(md_path, base_name, target, brief, client)

    return {"status": "success", "report": report}

@app.local_entrypoint()
def main(target: str = "Medanese Upper Middle Class, 25-45", brief: str = "Buy-Now-Pay-Later app for rent"):
    run_pipeline_core(target, brief)
