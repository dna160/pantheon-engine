import os
from src.utils import DIVIDER

NODE5_SYSTEM = "You are PANTHEON synthesize intelligence..."
REPORT_PROMPT = "Generate the PANTHEON Research Intelligence Report with 7 sections..."

def node5_synthesis(mass_reactions: list[dict], breakout_transcripts: list[dict], campaign_brief: str) -> str:
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    phase_a_lines = [f"Age {r.get('age')}: {r.get('phase_a', {}).get('gut_reaction')}" for r in mass_reactions if r.get("status") == "ok"]
    phase_b_lines = [t.get("transcript") for t in breakout_transcripts if t.get("status") == "ok"]
    
    payload = f"BRIEF: {campaign_brief}\n\nPHASE A:\n" + "\n".join(phase_a_lines) + f"\n\nPHASE B:\n" + "\n\n".join(phase_b_lines) + f"\n\n{REPORT_PROMPT}"
    
    messages = [{"role": "user", "content": payload}]
    final_report = ""
    while True:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            system=NODE5_SYSTEM,
            messages=messages,
            extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
        )
        chunk_text = resp.content[0].text
        final_report += chunk_text
        if resp.stop_reason != "max_tokens": break
        messages.append({"role": "assistant", "content": chunk_text})
        messages.append({"role": "user", "content": "Continue writing..."})
        
    return final_report
