import os
import re
import time
from datetime import datetime
from pathlib import Path

def _run_client_whisperer(md_path: Path, base_name: str, target: str, brief: str, client: str = "") -> None:
    import anthropic as _anthropic
    from dotenv import load_dotenv
    load_dotenv(md_path.parent.parent / "pantheon.env", override=True)
    ac = _anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    md_content = md_path.read_text(encoding="utf-8")
    
    system_prompt = "You are the Client Whisperer — Storytellers' most important front-facing intelligence..."
    user_msg = f"Generate Meeting Prep Document...\n\n{md_content[:40000]}"
    
    whisperer_md = ""
    try:
        resp = ac.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        whisperer_md = resp.content[0].text
    except Exception as e: print(f"Node 7 error: {e}"); return
    
    whisperer_md = re.sub(r"^```(?:markdown)?\n", "", whisperer_md, flags=re.IGNORECASE).strip()
    whisperer_md = re.sub(r"\n```$", "", whisperer_md).strip()
    
    client_safe = re.sub(r"[^\w]+", "", client) if client else "UntitledClient"
    docx_file_name = f"{base_name}_ClientWhisperer_{client_safe}_{datetime.now().strftime('%Y%m%d')}.docx"
    docx_path = md_path.parent / docx_file_name
    
    try:
        from docx import Document
        doc = Document()
        for raw_line in whisperer_md.splitlines():
            line = raw_line.rstrip()
            if not line.strip(): doc.add_paragraph(); continue
            if line.startswith("# "): doc.add_heading(line[2:].strip(), level=1); continue
            if line.startswith("## "): doc.add_heading(line[3:].strip(), level=2); continue
            # ... (more simple markdown parsing)
            para = doc.add_paragraph()
            segments = re.split(r"(\*\*[^*]+\*\*)", line)
            for seg in segments:
                if seg.startswith("**") and seg.endswith("**"):
                    run = para.add_run(seg[2:-2]); run.bold = True
                else: para.add_run(seg)
        doc.save(str(docx_path))
        print(f"Meeting Prep saved → {docx_path}")
    except Exception as e:
        print(f"Failed to save docx: {e}")
        (md_path.parent / (docx_file_name + ".md")).write_text(whisperer_md, encoding="utf-8")
