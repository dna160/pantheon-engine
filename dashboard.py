"""
dashboard.py — PANTHEON Market Research Intelligence Dashboard
Run with:  streamlit run dashboard.py
"""
import io
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page config — must be FIRST Streamlit call
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PANTHEON — Market Research Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS — dark mode premium aesthetic
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
[data-testid="stAppViewContainer"] {
    background: #0a0a0f;
    color: #e8e8f0;
}
[data-testid="stSidebar"] {
    background: #0f0f18 !important;
    border-right: 1px solid #1e1e30;
}
[data-testid="stSidebar"] * { color: #c8c8d8 !important; }

/* ── Typography ── */
h1, h2, h3 { color: #ffffff !important; }
p, li, label { color: #b0b0c8 !important; }

/* ── Inputs ── */
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input {
    background: #13131f !important;
    border: 1px solid #2a2a42 !important;
    color: #e8e8f0 !important;
    border-radius: 8px !important;
}
[data-testid="stTextArea"] textarea:focus,
[data-testid="stTextInput"] input:focus {
    border-color: #7b61ff !important;
    box-shadow: 0 0 0 2px rgba(123,97,255,0.25) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #13131f !important;
    border: 1px dashed #2a2a42 !important;
    border-radius: 10px !important;
    padding: 12px !important;
}

/* ── Sliders ── */
[data-testid="stSlider"] .st-bq { background: #7b61ff !important; }

/* ── Primary button ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7b61ff 0%, #4f3bcc 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 14px 36px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 20px rgba(123,97,255,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(123,97,255,0.55) !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 14px 36px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    width: 100% !important;
    box-shadow: 0 4px 20px rgba(16,185,129,0.35) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #13131f !important;
    border: 1px solid #1e1e30 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
}
[data-testid="stMetricLabel"] { color: #7878a0 !important; font-size: 12px !important; }
[data-testid="stMetricValue"] { color: #ffffff !important; font-size: 28px !important; font-weight: 700 !important; }

/* ── Log / code area ── */
[data-testid="stCode"] {
    background: #0d0d15 !important;
    border: 1px solid #1e1e30 !important;
    border-radius: 8px !important;
}

/* ── Cards ── */
.pantheon-card {
    background: #13131f;
    border: 1px solid #1e1e30;
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 16px;
}
.pantheon-card:hover { border-color: #3a3a58; }

/* ── Divider ── */
hr { border-color: #1e1e30 !important; }

/* ── Status badge ── */
.status-ok {
    display: inline-block;
    background: rgba(16,185,129,0.15);
    color: #10b981;
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 13px;
    font-weight: 600;
}
.status-running {
    display: inline-block;
    background: rgba(123,97,255,0.15);
    color: #7b61ff;
    border: 1px solid rgba(123,97,255,0.3);
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 13px;
    font-weight: 600;
}

/* ── Kill button ── */
div[data-testid="stButton"]:has(button[kind="secondary"]) button {
    background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 20px rgba(220,38,38,0.35) !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stButton"]:has(button[kind="secondary"]) button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 24px rgba(220,38,38,0.55) !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — file text extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p.strip() for p in pages if p.strip())
    except ImportError:
        return "[PyPDF2 not installed — pip install PyPDF2]"
    except Exception as e:
        return f"[PDF extraction error: {e}]"


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return "[python-docx not installed — pip install python-docx]"
    except Exception as e:
        return f"[DOCX extraction error: {e}]"


def extract_text_from_file(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(raw)
    elif name.endswith(".docx"):
        return extract_text_from_docx(raw)
    elif name.endswith(".doc"):
        # .doc (legacy binary) — best-effort via python-docx; usually fails
        text = extract_text_from_docx(raw)
        if text.startswith("["):
            return "[Legacy .doc format not fully supported — please convert to .docx or paste text manually]"
        return text
    elif name.endswith(".txt"):
        return raw.decode("utf-8", errors="replace")
    return "[Unsupported file type]"


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline runner — calls `modal run main.py` as a subprocess, streams stdout
# ─────────────────────────────────────────────────────────────────────────────

MAIN_PY = Path(__file__).parent / "main.py"
VENV_PYTHON = Path("D:/Pantheon/venv/Scripts/python.exe")
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

REPORTS_DIR = MAIN_PY.parent / "reports"
CAMPAIGN_LOG = REPORTS_DIR / "campaign_log.json"


def load_campaign_log() -> list[dict]:
    """Load the persistent campaign log from disk."""
    if CAMPAIGN_LOG.exists():
        try:
            return json.loads(CAMPAIGN_LOG.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_campaign_log(entries: list[dict]) -> None:
    """Persist the campaign log to disk."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CAMPAIGN_LOG.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def append_to_campaign_log(entry: dict) -> None:
    """Prepend a new campaign entry (newest-first) and save."""
    entries = load_campaign_log()
    entries.insert(0, entry)
    save_campaign_log(entries)


def run_pipeline(brief: str, target: str, limit: int, group_size: int, log_box):
    """
    Spawn `modal run main.py` with injected parameters.
    Streams each stdout line into log_box (st.empty()).
    Returns (success: bool, docx_path: Path | None, elapsed: float).
    """
    cmd = [
        PYTHON, "-m", "modal", "run", str(MAIN_PY),
        "--brief", brief,
        "--target", target,
        "--limit", str(limit),
        "--group-size", str(group_size),
    ]

    env = {"PYTHONIOENCODING": "utf-8", "PATH": str(Path(PYTHON).parent)}
    import os
    env.update(os.environ)  # inherit existing env (credentials, PATH etc.)

    lines: list[str] = []
    start = time.time()

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(MAIN_PY.parent),
        )

        for raw in proc.stdout:
            line = raw.rstrip()
            lines.append(line)
            # Show last 40 lines in the live log box
            log_box.code("\n".join(lines[-40:]), language=None)

        proc.wait()
        elapsed = time.time() - start
        success = proc.returncode == 0

    except Exception as e:
        lines.append(f"[SUBPROCESS ERROR] {e}")
        log_box.code("\n".join(lines), language=None)
        return False, None, time.time() - start

    # Locate the output .docx (main.py writes it to same dir as main.py)
    slug = re.sub(r"[^\w]+", "_", target).strip("_")
    docx_path = MAIN_PY.parent / "reports" / f"PANTHEON_Report_{slug}.docx"
    return success, (docx_path if docx_path.exists() else None), elapsed


# ─────────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────────────────────

for key, default in {
    "brief_text": "",
    "run_result": None,   # dict when completed
    "running": False,
    "agent_sample": None,  # list[dict] — up to 3 agents for the inspector
    "proc_pid": None,         # PID of the running pipeline subprocess
    "kill_requested": False,  # flag to kill the subprocess on next rerun
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — configuration
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 20px 0 12px;">
        <div style="font-size:32px;">⚡</div>
        <div style="font-size:18px; font-weight:800; color:#ffffff; letter-spacing:2px;">PANTHEON</div>
        <div style="font-size:11px; color:#5a5a80; letter-spacing:3px; margin-top:2px;">INTELLIGENCE ENGINE</div>
    </div>
    <hr/>
    """, unsafe_allow_html=True)

    st.markdown("### ⚙️ Run Configuration")

    st.markdown(
        '<div style="font-size:11px; letter-spacing:2px; color:#10b981; font-weight:600; '
        'margin-bottom:4px;">CLIENT NAME</div>',
        unsafe_allow_html=True,
    )
    client_name = st.text_input(
        "Client Name",
        value="",
        placeholder="e.g. Yakun (Optional)",
        help="If provided, report is named PANTHEON_REPORT_<ClientName>_v<Version>.",
        label_visibility="collapsed",
        key="client_input",
    )

    st.markdown(
        '<div style="font-size:11px; letter-spacing:2px; color:#7b61ff; font-weight:600; '
        'margin-top:10px; margin-bottom:4px;">PRIMARY TARGET MARKET (PTM)</div>',
        unsafe_allow_html=True,
    )
    ptm_demographic = st.text_input(
        "PTM",
        value="Medanese Upper Middle Class, 25-45",
        help="Primary demographic — must match a value in the agent_genomes table.",
        label_visibility="collapsed",
        key="ptm_input",
    )

    st.markdown(
        '<div style="font-size:11px; letter-spacing:2px; color:#f59e0b; font-weight:600; '
        'margin:10px 0 4px;">SECONDARY TARGET MARKET (STM)</div>',
        unsafe_allow_html=True,
    )
    stm_demographic = st.text_input(
        "STM",
        value="",
        placeholder="Optional — leave blank to skip",
        help="Secondary demographic. Leave blank to run PTM only.",
        label_visibility="collapsed",
        key="stm_input",
    )

    # Build the combined target string passed to --target
    # main.py's node1 splits on "|" and uses .in_() to pull both demographics
    if stm_demographic.strip():
        combined_target = f"{ptm_demographic.strip()}|{stm_demographic.strip()}"
    else:
        combined_target = ptm_demographic.strip()

    # Visual confirmation pill
    ptm_pill = (
        f'<span style="background:rgba(123,97,255,0.15); color:#7b61ff; border:1px solid '
        f'rgba(123,97,255,0.35); border-radius:5px; padding:2px 8px; font-size:11px; '
        f'font-weight:600;">PTM</span> {ptm_demographic or "—"}'
    )
    stm_pill = (
        f'<span style="background:rgba(245,158,11,0.15); color:#f59e0b; border:1px solid '
        f'rgba(245,158,11,0.35); border-radius:5px; padding:2px 8px; font-size:11px; '
        f'font-weight:600;">STM</span> {stm_demographic if stm_demographic.strip() else "(none)"}'
    )
    st.markdown(
        f'<div style="margin-top:10px; font-size:12px; line-height:1.9; color:#8888a8;">'
        f'{ptm_pill}<br/>{stm_pill}</div>',
        unsafe_allow_html=True,
    )

    agent_limit = st.slider(
        "Agents to Simulate",
        min_value=5,
        max_value=100,
        value=10,
        step=5,
        help="Total agents pulled across PTM + STM.",
    )

    group_size = st.slider(
        "Breakout Room Size",
        min_value=3,
        max_value=10,
        value=5,
        step=1,
        help="Number of agents per Phase B focus group debate.",
    )

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("### 📊 Est. Runtime")

    # Rough estimate: Node2+3 parallel (~30s) + Node4 (~60s/group) + Node5 (~45s)
    n_groups = max(1, agent_limit // group_size)
    est_min = round((30 + n_groups * 60 + 45) / 60, 1)
    st.info(f"~{est_min} min for {agent_limit} agents, {n_groups} breakout rooms.")

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.caption("PANTHEON v1.0 — Powered by [Anthropic Claude](https://anthropic.com) + [Modal](https://modal.com)")



# ─────────────────────────────────────────────────────────────────────────────
# MAIN — header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="padding: 40px 0 24px;">
    <div style="font-size: 13px; letter-spacing: 4px; color: #7b61ff; font-weight: 600; margin-bottom: 8px;">
        MARKET RESEARCH INTELLIGENCE
    </div>
    <h1 style="font-size: 42px; font-weight: 900; margin: 0; line-height: 1.1;">
        PANTHEON
    </h1>
    <p style="color: #5a5a80; margin-top: 8px; font-size: 15px;">
        Synthetic focus groups · Parallel LLM agents · Actionable research reports
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# BRIEF INPUT SECTION
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("### 📋 Campaign Brief")
st.caption("Paste your brief directly or upload a document — text will be auto-extracted.")

tab_paste, tab_upload = st.tabs(["✏️  Paste Text", "📎  Upload File"])

with tab_paste:
    pasted = st.text_area(
        "Campaign Brief",
        value=st.session_state.brief_text,
        height=180,
        placeholder=(
            "Describe the creative stimulus, product, audience, and market context.\n\n"
            "Example: A fintech app displays an iPhone advertisement for a Buy-Now-Pay-Later app "
            "that lets users split rent payments into 4 installments in Indonesia."
        ),
        label_visibility="collapsed",
        key="paste_area",
    )
    if pasted:
        st.session_state.brief_text = pasted

with tab_upload:
    uploaded = st.file_uploader(
        "Drop your brief document here",
        type=["pdf", "docx", "doc", "txt"],
        label_visibility="collapsed",
    )
    if uploaded is not None:
        with st.spinner("Extracting text..."):
            extracted = extract_text_from_file(uploaded)
        if extracted and not extracted.startswith("["):
            st.session_state.brief_text = extracted
            st.success(f"Extracted {len(extracted):,} characters from **{uploaded.name}**")
            with st.expander("Preview extracted text"):
                st.text(extracted[:1200] + ("…" if len(extracted) > 1200 else ""))
        else:
            st.error(extracted)

# Live character count
brief = st.session_state.brief_text
char_count = len(brief)
col_count, col_status = st.columns([3, 1])
with col_count:
    st.caption(f"{char_count:,} characters")
with col_status:
    if char_count > 50:
        st.markdown('<span class="status-ok">✓ Brief ready</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#5a5a80; font-size:13px;">Awaiting brief…</span>', unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# KILL HANDLER — if a kill was requested on a previous rerun, terminate now
# ─────────────────────────────────────────────────────────────────────────────

def _kill_pipeline_process():
    """Terminate the pipeline subprocess tree by stored PID."""
    pid = st.session_state.get("proc_pid")
    if pid is None:
        return
    import os, signal
    try:
        if sys.platform == "win32":
            # Kill entire process tree on Windows (modal spawns children)
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, timeout=10,
            )
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception:
        # Process may have already exited
        pass
    st.session_state.proc_pid = None
    st.session_state.running = False
    st.session_state.kill_requested = False


if st.session_state.kill_requested:
    _kill_pipeline_process()
    st.warning("🛑 Pipeline process killed by user.")


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION TRIGGER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("### 🚀 Execute Pipeline")

col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
    ready = char_count > 50 and not st.session_state.running
    execute = st.button(
        "⚡  Execute Genesis Protocol",
        type="primary",
        disabled=not ready,
        use_container_width=True,
    )
with col_right:
    if st.session_state.running and st.session_state.proc_pid:
        def _on_kill_click():
            st.session_state.kill_requested = True
        st.button(
            "🛑 Kill Process",
            type="secondary",
            on_click=_on_kill_click,
            use_container_width=True,
            key="kill_btn",
        )

if char_count <= 50 and not st.session_state.running:
    st.caption(
        "<div style='text-align:center; color:#5a5a80;'>Enter a campaign brief (>50 chars) to activate.</div>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# RUN — when button clicked
# ─────────────────────────────────────────────────────────────────────────────

if execute and ready:
    st.session_state.running = True
    st.session_state.run_result = None

    st.markdown("---")
    st.markdown("### 🔄 Pipeline Execution")

    # Import the visual component builder
    from pantheon_ui import build_pantheon_html
    import streamlit.components.v1 as stc

    # ── Placeholder for the PANTHEON UI visual canvas ─────────────────────────
    ui_placeholder = st.empty()
    status_text_placeholder = st.empty()

    # ── Render initial boot state ─────────────────────────────────────────────
    ui_step = 1
    ui_agents: list[dict] = []
    ui_logs: list[str] = ["[SYSTEM] Booting PANTHEON Core...", "[MODERATOR] Waking up. Awaiting target demographics."]
    ui_reactions: list[dict] = []
    ui_transcripts: list[dict] = []
    ui_status = "Phase 1: Booting PANTHEON Core — Connecting to Modal..."

    def _render_ui():
        html = build_pantheon_html(
            step=ui_step,
            agents=ui_agents,
            logs=ui_logs,
            breakout_transcripts=ui_transcripts,
            mass_reactions=ui_reactions,
            pipeline_status_text=ui_status,
            expected_agent_count=agent_limit,
            expected_group_size=group_size,
        )
        with ui_placeholder.container():
            stc.html(html, height=620, scrolling=False)


    _render_ui()
    
    import tempfile
    import os
    # Write brief to a temporary file to bypass Windows command-length limits
    fd, temp_brief_path = tempfile.mkstemp(suffix=".txt", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(brief)

    cmd = [
        PYTHON, "-m", "modal", "run", str(MAIN_PY),
        "--brief-file", temp_brief_path,
        "--target", combined_target,
        "--limit", str(agent_limit),
        "--group-size", str(group_size),
    ]
    if client_name.strip():
        cmd.extend(["--client", client_name.strip()])
    import os
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"

    lines: list[str] = []
    start_time = time.time()
    current_node = 0
    output_base_name = None
    pptx_base_name = None
    whisperer_file_name = None
    # Client folder: computed same way as main.py's _save_report()
    client_folder_name = (
        re.sub(r"[^\w]+", "_", client_name.strip()).strip("_")
        if client_name.strip() else "Unnamed"
    )
    node_keywords = [
        ("Node 1", 0), ("Node 2", 1), ("Node 3", 2), ("Node 4", 3), ("Node 5", 4),
        ("Node 6", 5), ("Node 7", 6),
    ]
    completed_nodes: set[int] = set()
    prev_ui_step = ui_step  # Track when step changes to re-render

    # ── Phase-to-UI-step mapping ──────────────────────────────────────────────
    # Node 0 (1) = Boot/Query → UI step 1-2
    # Node 1 (2) = Snapshots  → UI step 2
    # Node 2 (3) = Phase A    → UI step 3
    # Node 3 (4) = Phase B    → UI step 4
    # Node 4 (5) = Synthesis  → UI step 5
    # Node 5 (6) = Deck       → UI step 6
    # Node 6 (7) = Whisperer  → UI step 7
    node_to_ui_step = {0: 2, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7}

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(MAIN_PY.parent),
    )
    # Store PID so the kill handler can terminate it on a rerun
    st.session_state.proc_pid = proc.pid

    for raw in proc.stdout:
        line = raw.rstrip()

        # ── Intercept agent sample sentinel (never shown in log) ──────────
        if line.startswith("PANTHEON_AGENT_SAMPLE::"):
            try:
                agent_sample_data = json.loads(
                    line[len("PANTHEON_AGENT_SAMPLE::"):]
                )
                st.session_state.agent_sample = agent_sample_data
                # Feed agent data into the visual component
                ui_agents = agent_sample_data
                ui_logs.append("[SYSTEM] Agent genomes loaded into Grid Array.")
            except Exception:
                pass
            continue

        # ── Intercept client folder ───────────────────────────────────────
        if line.startswith("PANTHEON_CLIENT_FOLDER::"):
            client_folder_name = line[len("PANTHEON_CLIENT_FOLDER::"):].strip()
            continue

        # ── Intercept output filename ─────────────────────────────────────
        if line.startswith("PANTHEON_OUTPUT_FILE::"):
            output_base_name = line[len("PANTHEON_OUTPUT_FILE::"):].strip()
            continue

        # ── Intercept PPTX deck filename ─────────────────────────────────
        if line.startswith("PANTHEON_PPTX_FILE::"):
            pptx_base_name = line[len("PANTHEON_PPTX_FILE::"):].strip()
            continue
            
        # ── Intercept Whisperer filename ─────────────────────────────────
        if line.startswith("PANTHEON_WHISPERER_FILE::"):
            whisperer_file_name = line[len("PANTHEON_WHISPERER_FILE::"):].strip()
            continue

        lines.append(line)

        # ── Node card transitions & UI step mapping ───────────────────────
        for keyword, node_idx in node_keywords:
            if keyword in line:
                if node_idx > current_node:
                    current_node = node_idx
                new_step = node_to_ui_step.get(node_idx, ui_step)
                if new_step > ui_step:
                    ui_step = new_step
                break

        # ── Feed meaningful events into the UI logs ───────────────────────
        if "Node 1: Querying" in line or "Node 1:" in line:
            ui_logs.append("[MODERATOR] Querying Supabase for target demographics...")
            ui_status = "Phase 1: Querying agent database..."

        elif "returning" in line and "agent" in line and "pipeline" in line:
            m = re.search(r"returning (\d+) agent", line)
            n = m.group(1) if m else "?"
            ui_logs.append(f"[SYSTEM] {n} Agents successfully spawned into Grid Array.")
            ui_status = f"Phase 2: {n} agents assembled — generating runtime snapshots..."

        elif "Deficit" in line and "Genesis Protocol" in line:
            d = re.search(r"Deficit\s*=\s*(\d+)", line)
            n = d.group(1) if d else "?"
            ui_logs.append(f"[SYSTEM] Deficit detected: {n} agent(s). Genesis Protocol activated.")
            ui_status = f"Genesis Protocol: Generating {n} new agents..."

        elif "Genesis complete" in line:
            ui_logs.append("[SYSTEM] Genesis Protocol complete. New agents seeded.")

        elif "Pool sufficient" in line:
            ui_logs.append("[SYSTEM] Agent pool sufficient — no genesis needed.")

        elif "Node 2" in line and "snapshot" in line.lower():
            ui_logs.append("[MODERATOR] Generating runtime emotional snapshots in parallel...")
            ui_status = "Phase 2: Swarm Assembly — Generating agent snapshots..."

        elif "snapshots complete" in line.lower():
            ui_logs.append("[SYSTEM] All runtime snapshots generated.")

        elif "Node 3" in line and "Phase A" in line:
            ui_logs.append("[MODERATOR] Broadcasting Campaign Brief to Grid.")
            ui_logs.append("[SYSTEM] Streaming data packets to agents. Awaiting reactions...")
            ui_status = "Phase 3: Mass Session — Agents reacting to brief..."

        elif "Phase A reactions collected" in line:
            m = re.search(r"(\d+)/(\d+)", line)
            if m:
                ui_logs.append(f"[SYSTEM] {m.group(1)}/{m.group(2)} gut reactions captured.")

        elif "Node 4" in line and "breakout" in line.lower():
            ui_logs.append("[SYSTEM] Grid dissolved. Initiating Breakout Rooms.")
            ui_logs.append("[MODERATOR] Rooms isolated. Simulating focus group conflict.")
            ui_status = "Phase 4: Breakout Rooms — Focus group debates in progress..."

        elif "Node 4 ✓" in line:
            ui_logs.append("[SYSTEM] Breakout room transcript captured.")

        elif "Node 5" in line and "synthesis" in line.lower():
            ui_logs.append("[SYSTEM] Breakout sessions complete.")
            ui_logs.append("[MODERATOR] Summoning synthesis engine. Compiling final report...")
            ui_status = "Phase 5: Synthesis — Claude Sonnet writing PANTHEON Report..."

        elif "Markdown saved" in line:
            ui_logs.append("[SYSTEM] PANTHEON Report saved.")
            ui_status = "Report saved — starting Presentation Architect..."

        elif "Node 6" in line and "Presentation Architect" in line:
            ui_logs.append("[MODERATOR] Presentation Architect activated. Building slide deck...")
            ui_status = "Phase 6: Presentation Architect — Building slide deck..."

        elif "Deck saved" in line:
            ui_logs.append("[SYSTEM] Slide deck generated.")
            ui_status = "Slide deck saved — starting Client Whisperer..."

        elif "Node 7" in line and "Client Whisperer" in line:
            ui_logs.append("[MODERATOR] Client Whisperer activated. Drafting meeting prep...")
            ui_status = "Phase 7: Client Whisperer — Drafting meeting prep document..."

        elif "Meeting Prep saved" in line:
            ui_logs.append("[SYSTEM] Meeting prep document generated.")
            ui_logs.append("[SYSTEM] ═══ PIPELINE COMPLETE ═══")
            ui_status = "✅ Pipeline complete — all documents generated!"

        # ── Re-render the visual component when step changes ──────────────
        if ui_step != prev_ui_step:
            _render_ui()
            prev_ui_step = ui_step

    proc.wait()
    elapsed = round(time.time() - start_time, 1)
    st.session_state.proc_pid = None  # Process exited normally, clear PID

    # Clean up the temporary file
    try:
        os.remove(temp_brief_path)
    except OSError:
        pass

    # ── Final render with all collected data ──────────────────────────────
    if proc.returncode == 0:
        ui_logs.append(f"[SYSTEM] Total runtime: {elapsed}s")
        ui_status = f"✅ Pipeline complete — {elapsed}s total runtime"
    else:
        ui_logs.append(f"[SYSTEM] ❌ Pipeline error (exit code {proc.returncode})")
        ui_status = "❌ Pipeline encountered an error — check logs"
    _render_ui()

    # ── Show the raw log in a collapsed expander for debugging ────────────
    with st.expander("📋 Raw Pipeline Log", expanded=False):
        st.code("\n".join(lines), language=None)

    # Locate output files — now inside reports/<client_folder>/
    client_dir = MAIN_PY.parent / "reports" / client_folder_name
    if output_base_name:
        docx_path = client_dir / f"{output_base_name}.docx"
        md_path   = client_dir / f"{output_base_name}.md"
        base_name_for_downloads = output_base_name
    else:
        slug = re.sub(r"[^\w]+", "_", combined_target).strip("_")
        docx_path = client_dir / f"PANTHEON_Report_{slug}.docx"
        md_path   = client_dir / f"PANTHEON_Report_{slug}.md"
        base_name_for_downloads = f"PANTHEON_Report_{slug}"

    # Locate PPTX deck (from Node 6)
    _pptx_base = pptx_base_name or output_base_name
    pptx_path = (client_dir / f"{_pptx_base}.pptx") if _pptx_base else None

    # Locate Whisperer document (from Node 7)
    whisperer_path = (client_dir / whisperer_file_name) if whisperer_file_name else None

    success = proc.returncode == 0 and docx_path.exists()

    _docx_str      = str(docx_path)      if docx_path.exists()                            else None
    _md_str        = str(md_path)        if md_path.exists()                              else None
    _pptx_str      = str(pptx_path)      if (pptx_path and pptx_path.exists())           else None
    _whisperer_str = str(whisperer_path) if (whisperer_path and whisperer_path.exists())  else None

    st.session_state.run_result = {
        "success": success,
        "elapsed": elapsed,
        "docx_path": _docx_str,
        "md_path": _md_str,
        "pptx_path": _pptx_str,
        "whisperer_path": _whisperer_str,
        "agent_limit": agent_limit,
        "n_groups": max(1, agent_limit // group_size),
        "target": combined_target,
        "ptm": ptm_demographic,
        "stm": stm_demographic if stm_demographic.strip() else None,
        "agent_sample": st.session_state.agent_sample,
        "output_base_name": base_name_for_downloads,
        "client_folder": client_folder_name,
        "client": client_name.strip() or "Unnamed",
    }

    # ── Persist to campaign log ──────────────────────────────────────────────
    append_to_campaign_log({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "client": client_name.strip() or "Unnamed",
        "client_folder": client_folder_name,
        "target": combined_target,
        "brief_snippet": brief[:300],
        "elapsed": elapsed,
        "success": success,
        "output_base_name": base_name_for_downloads,
        "files": {
            "docx":      _docx_str,
            "md":        _md_str,
            "pptx":      _pptx_str,
            "whisperer": _whisperer_str,
        },
    })

    st.session_state.running = False


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT — results section
# ─────────────────────────────────────────────────────────────────────────────

# ── helper: render one agent's mutation timeline ─────────────────────────────
_STAGE_EMOJI = {
    "Origin":       "🌱",
    "Formation":    "🏫",
    "Independence": "💼",
    "Maturity":     "🏡",
    "Legacy":       "🌿",
}
_TRAIT_LABELS = {
    "openness": "Openness", "conscientiousness": "Conscientiousness",
    "extraversion": "Extraversion", "agreeableness": "Agreeableness",
    "neuroticism": "Neuroticism", "communication_style": "Comm. Style",
    "decision_making": "Decision Making", "brand_relationship": "Brand Loyalty",
    "influence_susceptibility": "Influence", "emotional_expression": "Emotional Expr.",
    "conflict_behavior": "Conflict", "literacy_and_articulation": "Literacy",
    "socioeconomic_friction": "SES Friction",
}


def _render_genome_bar(label: str, value: int, max_val: int = 100) -> str:
    """Return a compact HTML progress bar for a genome integer."""
    pct = max(0, min(100, int(value or 0)))
    # Color: low=red, mid=amber, high=teal
    color = "#ef4444" if pct < 35 else ("#f59e0b" if pct < 65 else "#10b981")
    return (
        f'<div style="margin:3px 0; display:flex; align-items:center; gap:8px;">'
        f'<span style="min-width:130px; font-size:11px; color:#8888a8;">{label}</span>'
        f'<div style="flex:1; background:#1e1e30; border-radius:4px; height:8px;">'
        f'<div style="width:{pct}%; background:{color}; border-radius:4px; height:8px; '
        f'transition:width 0.3s;"></div></div>'
        f'<span style="min-width:28px; font-size:11px; color:#c8c8d8; text-align:right;">{pct}</span>'
        f'</div>'
    )


def render_agent_inspector(agents: list):
    st.subheader("🧬 Agent Population Sample")
    st.caption("3 randomly selected agents from the active pool — showing their final mutated genome.")

    for agent in agents:
        demo  = agent.get("target_demographic", "Unknown")
        age   = agent.get("age", "?")
        region = agent.get("region", "?")
        lit   = agent.get("literacy_and_articulation", 50)
        ses   = agent.get("socioeconomic_friction", 50)
        log   = agent.get("genome_mutation_log") or []
        vp    = agent.get("voice_print") or {}

        with st.expander(
            f"🧑 **{demo}** · Age {age} · {region}  "
            f"  *(Literacy {lit}/100 · SES Friction {ses}/100)*",
            expanded=False,
        ):
            col_genome, col_timeline = st.columns([1, 1], gap="large")

            # ── Left: genome bars ─────────────────────────────────────────────
            with col_genome:
                st.markdown(
                    '<div style="font-size:12px; letter-spacing:2px; color:#7b61ff; '
                    'font-weight:700; margin-bottom:8px;">FINAL GENOME</div>',
                    unsafe_allow_html=True,
                )
                bars_html = "".join(
                    _render_genome_bar(_TRAIT_LABELS.get(k, k), agent.get(k, 50))
                    for k in _TRAIT_LABELS
                )
                st.markdown(
                    f'<div style="background:#0d0d15; border-radius:10px; padding:14px 16px;">{bars_html}</div>',
                    unsafe_allow_html=True,
                )

                # Voice print
                if vp:
                    st.markdown(
                        '<div style="font-size:12px; letter-spacing:2px; color:#4f3bcc; '
                        'font-weight:700; margin:14px 0 6px;">VOICE PRINT</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"- **Vocab:** {vp.get('vocabulary_level', '—')}  \n"
                        f"- **Fillers:** {', '.join(vp.get('filler_words', []) or ['—'])}  \n"
                        f"- **Persuasion:** {', '.join(vp.get('persuasion_triggers', []) or ['—'])}  \n"
                        f"- **Conflict style:** {vp.get('conflict_style', '—')}"
                    )

            # ── Right: mutation timeline ──────────────────────────────────────
            with col_timeline:
                st.markdown(
                    '<div style="font-size:12px; letter-spacing:2px; color:#f59e0b; '
                    'font-weight:700; margin-bottom:8px;">MUTATION TIMELINE</div>',
                    unsafe_allow_html=True,
                )
                if not log:
                    st.markdown(
                        '<div style="color:#5a5a80; font-size:13px; padding:12px;">'
                        '∅ No mutation events — this agent had a stable, uneventful life.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    timeline_html = ""
                    for event in log:
                        stage = event.get("life_stage", "?")
                        emoji = _STAGE_EMOJI.get(stage, "📌")
                        desc  = event.get("event_description", "")
                        mods  = event.get("trait_modifiers") or {}
                        mod_strs = []
                        for trait, delta in mods.items():
                            sign  = "+" if int(delta) >= 0 else ""
                            color = "#10b981" if int(delta) >= 0 else "#ef4444"
                            label = _TRAIT_LABELS.get(trait, trait)
                            mod_strs.append(
                                f'<span style="color:{color}; font-size:11px; '
                                f'background:rgba(0,0,0,0.3); border-radius:4px; '
                                f'padding:1px 6px; margin:2px;">{label} {sign}{delta}</span>'
                            )
                        mods_block = " ".join(mod_strs) if mod_strs else ""
                        timeline_html += (
                            f'<div style="border-left:2px solid #2a2a42; margin-left:8px; '
                            f'padding:8px 0 8px 14px; position:relative;">'
                            f'<div style="position:absolute; left:-7px; top:10px; width:12px; '
                            f'height:12px; background:#7b61ff; border-radius:50%;"></div>'
                            f'<div style="font-size:11px; color:#7b61ff; font-weight:600; '
                            f'letter-spacing:1px;">{emoji} {stage.upper()}</div>'
                            f'<div style="font-size:13px; color:#d8d8e8; margin:3px 0;">{desc}</div>'
                            f'<div style="margin-top:4px;">{mods_block}</div>'
                            f'</div>'
                        )
                    st.markdown(
                        f'<div style="background:#0d0d15; border-radius:10px; '
                        f'padding:14px 16px;">{timeline_html}</div>',
                        unsafe_allow_html=True,
                    )


result = st.session_state.run_result
if result:
    st.markdown("---")
    st.markdown("### 📊 Results")

    if result["success"]:
        # Success metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("Status", "✓ Complete")
        with m2:
            st.metric("Runtime", f"{result['elapsed']}s")
        with m3:
            st.metric("Agents Simulated", result["agent_limit"])
        with m4:
            st.metric("Breakout Rooms", result["n_groups"])
        with m5:
            markets = "PTM + STM" if result.get("stm") else "PTM only"
            st.metric("Markets", markets)

        st.markdown("")

        # ── Agent Inspector ───────────────────────────────────────────────────
        agents = result.get("agent_sample") or []
        if agents:
            st.markdown("---")
            render_agent_inspector(agents)

        # ── In-App Report Viewer ──────────────────────────────────────────────
        if result["md_path"]:
            st.markdown("---")
            md_content = Path(result["md_path"]).read_text(encoding="utf-8")
            slug = re.sub(r"[^\w]+", "_", result["target"]).strip("_")

            with st.container():
                # Header row: title + download buttons side-by-side
                hdr_col, dl_col1, dl_col2, dl_col3, dl_col4 = st.columns([2, 1, 1, 1, 1], gap="small")
                with hdr_col:
                    st.subheader("📖 PANTHEON Synthesis Report")
                with dl_col1:
                    if result["docx_path"]:
                        st.download_button(
                            label="📄 .docx",
                            data=Path(result["docx_path"]).read_bytes(),
                            file_name=f"{result.get('output_base_name', 'PANTHEON_Report')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                        )
                with dl_col2:
                    st.download_button(
                        label="📝 .md",
                        data=md_content.encode("utf-8"),
                        file_name=f"{result.get('output_base_name', 'PANTHEON_Report')}.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                with dl_col3:
                    if result.get("pptx_path"):
                        st.download_button(
                            label="🎞️ .pptx",
                            data=Path(result["pptx_path"]).read_bytes(),
                            file_name=f"{result.get('output_base_name', 'PANTHEON_Report')}.pptx",
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            use_container_width=True,
                        )
                with dl_col4:
                    if result.get("whisperer_path"):
                        st.download_button(
                            label="🗣️ Whisperer",
                            data=Path(result["whisperer_path"]).read_bytes(),
                            file_name=Path(result["whisperer_path"]).name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                        )

                # Full report rendered inline
                st.markdown(
                    '<div style="background:#0d0d15; border:1px solid #1e1e30; '
                    'border-radius:14px; padding:32px 36px; margin-top:12px;">',
                    unsafe_allow_html=True,
                )
                st.markdown(md_content)
                st.markdown('</div>', unsafe_allow_html=True)

        elif result["docx_path"]:
            # Fallback: no .md, but .docx exists — just show download
            st.download_button(
                label="📄  Download Word Report (.docx)",
                data=Path(result["docx_path"]).read_bytes(),
                file_name=f"{result.get('output_base_name', 'PANTHEON_Report')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    else:
        st.error(
            "Pipeline did not complete successfully. "
            "Check the live log above for errors. "
            "Common causes: Modal auth, Supabase credentials, or Anthropic rate limits."
        )
        st.markdown(
            "**Troubleshooting checklist:**\n"
            "- Run `modal token new` to refresh your Modal session\n"
            "- Verify `pantheon-secrets` in Modal dashboard contains all 3 keys\n"
            "- Check your Anthropic API credit balance\n"
            "- Confirm agents exist in Supabase for the selected demographic"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PREVIOUS CAMPAIGNS — persistent log + redownload
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("### 📁 Previous Campaigns")

campaign_log = load_campaign_log()

if not campaign_log:
    st.markdown(
        '<div style="background:#13131f; border:1px solid #1e1e30; border-radius:12px; '
        'padding:24px 28px; color:#5a5a80; font-size:14px; text-align:center;">'
        'No campaigns logged yet. Run the pipeline above to start building your history.'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    st.caption(f"{len(campaign_log)} campaign(s) on record — newest first.")

    for idx, entry in enumerate(campaign_log):
        ts_raw     = entry.get("timestamp", "")
        client_lbl = entry.get("client", "Unnamed")
        folder_lbl = entry.get("client_folder", "Unnamed")
        target_lbl = entry.get("target", "—")
        elapsed    = entry.get("elapsed", 0)
        success    = entry.get("success", False)
        snippet    = entry.get("brief_snippet", "")
        base_name  = entry.get("output_base_name", "PANTHEON_Report")
        files      = entry.get("files", {})

        # Format timestamp nicely
        try:
            ts_dt  = datetime.fromisoformat(ts_raw)
            ts_fmt = ts_dt.strftime("%d %b %Y · %H:%M")
        except Exception:
            ts_fmt = ts_raw

        status_color  = "#10b981" if success else "#ef4444"
        status_icon   = "✓ Complete" if success else "✗ Failed"
        elapsed_fmt   = f"{round(elapsed)}s" if elapsed < 120 else f"{round(elapsed/60,1)}m"

        client_color  = "#7b61ff" if client_lbl != "Unnamed" else "#5a5a80"

        with st.expander(
            f"**{client_lbl}** · {ts_fmt}  |  {target_lbl[:60]}{'…' if len(target_lbl) > 60 else ''}",
            expanded=False,
        ):
            # ── Header row ────────────────────────────────────────────────────
            h1, h2, h3 = st.columns([2, 1, 1])
            with h1:
                st.markdown(
                    f'<span style="font-size:13px; color:{client_color}; font-weight:700; '
                    f'letter-spacing:1px;">📂 {folder_lbl}/</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<span style="font-size:12px; color:#8888a8;">{target_lbl}</span>',
                    unsafe_allow_html=True,
                )
            with h2:
                st.markdown(
                    f'<span style="background:rgba({("16,185,129" if success else "239,68,68")},0.12); '
                    f'color:{status_color}; border:1px solid {status_color}; border-radius:6px; '
                    f'padding:3px 10px; font-size:12px; font-weight:600;">{status_icon}</span>',
                    unsafe_allow_html=True,
                )
            with h3:
                st.markdown(
                    f'<span style="font-size:12px; color:#8888a8;">⏱ {elapsed_fmt}</span>',
                    unsafe_allow_html=True,
                )

            # ── Brief snippet ─────────────────────────────────────────────────
            if snippet:
                st.markdown(
                    f'<div style="margin:10px 0 6px; font-size:12px; color:#6868a0; '
                    f'font-style:italic; border-left:2px solid #2a2a42; padding-left:10px;">'
                    f'{snippet[:280]}{"…" if len(snippet) > 280 else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # ── Download buttons — only show files that still exist on disk ──
            available = {
                k: v for k, v in files.items() if v and Path(v).exists()
            }

            if available:
                dl_cols = st.columns(len(available))
                col_map = {
                    "docx":      ("📄 Report (.docx)", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                    "md":        ("📝 Report (.md)",   "text/markdown"),
                    "pptx":      ("🎞️ Deck (.pptx)",   "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
                    "whisperer": ("🗣️ Whisperer (.docx)", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                }
                for col, (file_key, file_path) in zip(dl_cols, available.items()):
                    label, mime = col_map.get(file_key, (file_key, "application/octet-stream"))
                    fname = Path(file_path).name
                    with col:
                        st.download_button(
                            label=label,
                            data=Path(file_path).read_bytes(),
                            file_name=fname,
                            mime=mime,
                            use_container_width=True,
                            key=f"dl_{idx}_{file_key}",
                        )
            else:
                st.markdown(
                    '<span style="font-size:12px; color:#5a5a80;">⚠ No files found on disk for this campaign.</span>',
                    unsafe_allow_html=True,
                )
