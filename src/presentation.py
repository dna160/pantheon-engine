import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

_DECK_CONTENT_TOOL = {
    "name": "extract_deck_content",
    "description": "Extract deck content.",
    "input_schema": { "type": "object", "properties": { "title": {"type": "string"} }, "required": ["title"] }
}

_PPTXGENJS_TEMPLATE = r"""
const pptxgen = require('pptxgenjs');
// ... (rest of the template)
"""

def _extract_deck_content(anthropic_client, md_content: str, target: str, brief: str, client: str) -> dict | None:
    system = "Expert MBB strategist..."
    user_msg = f"Extract deck content...\n\n{md_content[:12000]}"
    try:
        resp = anthropic_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=system,
            tools=[_DECK_CONTENT_TOOL],
            tool_choice={"type": "tool", "name": "extract_deck_content"},
            messages=[{"role": "user", "content": user_msg}],
        )
        block = next((b for b in resp.content if b.type == "tool_use"), None)
        return block.input if block else None
    except Exception: return None

def _save_presentation(md_path: Path, base_name: str, target: str, brief: str, client: str = "") -> None:
    import anthropic as _anthropic
    from dotenv import load_dotenv
    load_dotenv(md_path.parent.parent / "pantheon.env", override=True)
    ac = _anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    md_content = md_path.read_text(encoding="utf-8")
    deck_data = _extract_deck_content(ac, md_content, target, brief, client)
    if not deck_data: return
    
    deck_data.update({"target": target, "date": datetime.now().strftime("%B %Y")})
    out_dir = md_path.parent
    json_path = out_dir / f"{base_name}_deck_data.json"
    js_path = out_dir / f"{base_name}_gen.js"
    pptx_path = out_dir / f"{base_name}.pptx"
    
    json_path.write_text(json.dumps(deck_data, ensure_ascii=False, indent=2), encoding="utf-8")
    js_path.write_text(_PPTXGENJS_TEMPLATE, encoding="utf-8")
    
    try:
        result = subprocess.run(["node", str(js_path), str(json_path), str(pptx_path)], capture_output=True, text=True, timeout=90, cwd=str(out_dir))
        if result.returncode == 0:
            print(f"Deck saved → {pptx_path}")
    except Exception as e: print(f"Node 6 error: {e}")
    finally:
        for tmp in [json_path, js_path]: tmp.unlink(missing_ok=True)
