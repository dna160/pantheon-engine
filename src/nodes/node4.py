import os

NODE4_SYSTEM = "You are a qualitative research director facilitating focus groups..."

def node4_breakout_room(group_reactions: list[dict], campaign_brief: str) -> dict:
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    parts = []
    for r in group_reactions:
        pa = r.get("phase_a") or {}
        snap = r.get("runtime_snapshot") or {}
        parts.append(f"PARTICIPANT (Age {r.get('age')}, {r.get('demographic')}): {pa.get('gut_reaction')}")
    
    group_ctx = "\n\n".join(parts)
    agent_ages = [str(r.get("age")) for r in group_reactions]
    
    prompt = f"BRIEF: {campaign_brief}\n\nPARTICIPANTS: {group_ctx}\n\nWrite 15-turn debate."
    
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2500,
            system=NODE4_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        transcript = resp.content[0].text
        status = "ok"
    except Exception as e:
        transcript = None
        status = "error"
        error = str(e)
        
    return {
        "participant_ages": agent_ages,
        "transcript": transcript,
        "status": status,
        "error": error if 'error' in locals() else None,
    }
