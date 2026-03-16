import os
import time
from src.utils import _build_agent_context

NODE3_TOOL = {
    "name": "submit_phase_a_reaction",
    "description": "Submit gut reaction.",
    "input_schema": {
        "type": "object",
        "properties": {
            "gut_reaction": {"type": "string"},
            "emotional_temperature": {"type": "integer"},
            "dominant_emotion": {"type": "string"},
            "personal_relevance_score": {"type": "integer"},
            "intent_signal": {"type": "string"}
        },
        "required": ["gut_reaction", "emotional_temperature", "dominant_emotion", "personal_relevance_score", "intent_signal"]
    }
}

NODE3_SYSTEM = "You are PANTHEON Phase A Engine..."

def node3_mass_session(dynamic_agent: dict, campaign_brief: str) -> dict:
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    dna = dynamic_agent["immutable_dna"]
    snap = dynamic_agent["runtime_snapshot"]
    ctx = _build_agent_context(dna)
    prompt = f"{ctx}\n\nSnapshot: {snap}\n\nBrief: {campaign_brief}\n\nSimulate gut reaction."
    
    reaction = None
    status = "error"
    error = None
    for _attempt in range(1, 4):
        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=NODE3_SYSTEM,
                tools=[NODE3_TOOL],
                tool_choice={"type": "tool", "name": "submit_phase_a_reaction"},
                messages=[{"role": "user", "content": prompt}]
            )
            block = next((b for b in resp.content if b.type == "tool_use"), None)
            if not block: raise ValueError("No tool_use block")
            reaction = block.input
            status = "ok"
            break
        except _anthropic.RateLimitError as e:
            time.sleep(65)
            error = str(e)
        except Exception as e:
            error = str(e)
            time.sleep(5)
            
    return {
        "agent_id": dna.get("id"),
        "age": dna.get("age"),
        "demographic": dna.get("target_demographic"),
        "agent_context": ctx,
        "runtime_snapshot": snap,
        "phase_a": reaction,
        "status": status,
        "error": error,
    }
