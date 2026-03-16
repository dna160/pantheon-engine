import os
import modal
from src.utils import _build_agent_context

def get_image():
    return (
        modal.Image.debian_slim(python_version="3.11")
        .pip_install(
            "supabase>=2.0.0",
            "anthropic>=0.50.0",
            "fastapi[standard]>=0.115.0",
            "pydantic>=2.4.0",
        )
    )

SECRETS = [modal.Secret.from_name("pantheon-secrets")]

NODE2_TOOL = {
    "name": "submit_snapshot",
    "description": "Submit current runtime state.",
    "input_schema": {
        "type": "object",
        "properties": {
            "current_emotional_state": {"type": "string"},
            "current_mental_bandwidth": {"type": "string"},
            "current_financial_pressure": {"type": "string"}
        },
        "required": ["current_emotional_state", "current_mental_bandwidth", "current_financial_pressure"]
    }
}

NODE2_SYSTEM = "You are PANTHEON's Runtime State Engine..."

def node2_generate_snapshot(agent: dict) -> dict:
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    ctx = _build_agent_context(agent)
    prompt = f"{ctx}\n\nDescribe their mental/emotional state RIGHT NOW."
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=NODE2_SYSTEM,
            tools=[NODE2_TOOL],
            tool_choice={"type": "tool", "name": "submit_snapshot"},
            messages=[{"role": "user", "content": prompt}]
        )
        block = next((b for b in resp.content if b.type == "tool_use"), None)
        snapshot = block.input if block else {"current_emotional_state": "Unknown", "current_mental_bandwidth": "Unknown", "current_financial_pressure": "Unknown"}
    except Exception:
        snapshot = {"current_emotional_state": "Error", "current_mental_bandwidth": "Unknown", "current_financial_pressure": "Unknown"}
    return {"immutable_dna": agent, "runtime_snapshot": snapshot}
