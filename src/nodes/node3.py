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

NODE3_SYSTEM_BASE = "You are PANTHEON Phase A Engine. Simulate a real human's first gut reaction to a campaign stimulus. Stay completely in character — respond as this specific person, not as an AI assistant."

NODE3_VISION_ADDENDUM = (
    "\n\nYou are evaluating a campaign. You have been provided the raw text AND the actual "
    "visual slides of the campaign. React to the visual design, the model choices, and the "
    "layout — not just the copy. Notice colors, imagery, typography, and emotional tone of "
    "the visuals. Your gut reaction must reference what you SEE, not just what you read."
)


def _build_content(prompt: str, brief_images: list[str]) -> list[dict] | str:
    """Return multimodal content array if images present, else plain string."""
    if not brief_images:
        return prompt
    content: list[dict] = [{"type": "text", "text": prompt}]
    for b64 in brief_images[:6]:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64,
            }
        })
    return content


def node3_mass_session(dynamic_agent: dict, campaign_brief: str, brief_images: list[str] = []) -> dict:
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    dna = dynamic_agent["immutable_dna"]
    snap = dynamic_agent["runtime_snapshot"]
    ctx = _build_agent_context(dna)

    system = NODE3_SYSTEM_BASE + (NODE3_VISION_ADDENDUM if brief_images else "")

    prompt = (
        f"{ctx}\n\nSnapshot: {snap}\n\nBrief: {campaign_brief}\n\n"
        + ("You are also looking at the actual campaign visuals attached below. " if brief_images else "")
        + "Simulate gut reaction."
    )
    content = _build_content(prompt, brief_images)

    reaction = None
    status = "error"
    error = None
    for _attempt in range(1, 4):
        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=system,
                tools=[NODE3_TOOL],
                tool_choice={"type": "tool", "name": "submit_phase_a_reaction"},
                messages=[{"role": "user", "content": content}]
            )
            block = next((b for b in resp.content if b.type == "tool_use"), None)
            if not block:
                raise ValueError("No tool_use block")
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
