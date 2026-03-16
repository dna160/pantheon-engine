"""
pantheon_ui.py — PANTHEON Visual Execution Component
Generates a self-contained HTML/CSS/JS visualization for embedding in Streamlit
via st.components.v1.html().

Replaces the terminal log view during pipeline execution with an animated
canvas showing agent nodes, breakout rooms, data flow lines, and system logs.
"""


def build_pantheon_html(
    step: int = 1,
    agents: list[dict] | None = None,
    logs: list[str] | None = None,
    selected_node: str | None = None,
    breakout_transcripts: list[dict] | None = None,
    mass_reactions: list[dict] | None = None,
    pipeline_status_text: str = "",
    expected_agent_count: int = 10,
    expected_group_size: int = 5,
) -> str:
    """
    Build the full HTML string for the PANTHEON UI component.

    Args:
        step: Current pipeline phase (1-7).
        agents: List of agent dicts from the pipeline (id, age, demographic, etc.).
        logs: System log lines to display.
        selected_node: Not used for initial render (modals handled in JS).
        breakout_transcripts: Phase B transcript dicts for the spy modal.
        mass_reactions: Phase A reaction dicts for agent inspector modal.
        pipeline_status_text: Current status label for the bottom bar.
    """
    import json as _json

    if agents is None:
        agents = []
    if logs is None:
        logs = []
    if breakout_transcripts is None:
        breakout_transcripts = []
    if mass_reactions is None:
        mass_reactions = []

    # Build compact agent data for JS
    js_agents = []
    for i, a in enumerate(agents):
        age = a.get("age", "?")
        demo = a.get("target_demographic", "Unknown")
        region = a.get("region", "")
        # Short label
        label = f"A{i+1}: {age}{'' if not region else ' ' + region[:12]}"
        # Genome traits for inspector
        genome = {
            "openness": a.get("openness", 50),
            "conscientiousness": a.get("conscientiousness", 50),
            "extraversion": a.get("extraversion", 50),
            "agreeableness": a.get("agreeableness", 50),
            "neuroticism": a.get("neuroticism", 50),
            "literacy": a.get("literacy_and_articulation", 50),
            "ses_friction": a.get("socioeconomic_friction", 50),
            "influence": a.get("influence_susceptibility", 50),
        }
        js_agents.append({
            "id": f"a{i+1}",
            "label": label,
            "age": age,
            "demo": demo,
            "region": region or "N/A",
            "genome": genome,
        })

    # Pad to min 10 or expected_agent_count for layout
    pad_count = max(10, expected_agent_count)
    while len(js_agents) < pad_count:
        idx = len(js_agents) + 1
        js_agents.append({
            "id": f"a{idx}",
            "label": f"A{idx}: Awaiting...",
            "age": "?",
            "demo": "Pending",
            "region": "N/A",
            "genome": {
                "openness": 50, "conscientiousness": 50, "extraversion": 50,
                "agreeableness": 50, "neuroticism": 50, "literacy": 50,
                "ses_friction": 50, "influence": 50,
            },
        })

    # Build reactions lookup for JS
    js_reactions = []
    for r in mass_reactions:
        if r.get("status") != "ok" or not r.get("phase_a"):
            continue
        pa = r["phase_a"]
        js_reactions.append({
            "age": r.get("age", "?"),
            "demo": r.get("demographic", "Unknown"),
            "gut": pa.get("gut_reaction", ""),
            "emotion": pa.get("dominant_emotion", ""),
            "temp": pa.get("emotional_temperature", 0),
            "relevance": pa.get("personal_relevance_score", 0),
            "intent": pa.get("intent_signal", ""),
        })

    # Build breakout transcript data for JS
    js_transcripts = []
    for i, tb in enumerate(breakout_transcripts):
        js_transcripts.append({
            "room": i + 1,
            "ages": tb.get("participant_ages", []),
            "transcript": (tb.get("transcript") or "Transcript not yet available.")[:3000],
            "status": tb.get("status", "pending"),
        })

    # Escape for JS injection
    agents_json = _json.dumps(js_agents, ensure_ascii=False)
    logs_json = _json.dumps(logs[-60:] if len(logs) > 60 else logs, ensure_ascii=False)
    reactions_json = _json.dumps(js_reactions, ensure_ascii=False)
    transcripts_json = _json.dumps(js_transcripts, ensure_ascii=False)
    status_json = _json.dumps(pipeline_status_text)
    group_size_json = _json.dumps(expected_group_size)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a0f; color:#cbd5e1; font-family:'Inter','Segoe UI',system-ui,sans-serif; overflow:hidden; }}

  .pantheon-root {{ display:flex; height:100vh; width:100vw; }}

  /* ── Left Canvas ── */
  .canvas {{ flex:1; position:relative; overflow:hidden; border-right:1px solid #1e293b; }}
  .canvas-grid {{
    position:absolute; inset:0;
    background-image:
      linear-gradient(to right, #1e293b44 1px, transparent 1px),
      linear-gradient(to bottom, #1e293b44 1px, transparent 1px);
    background-size: 4rem 4rem;
    opacity:0.3;
  }}

  /* ── Header bar ── */
  .canvas-header {{
    position:absolute; top:0; left:0; right:0; z-index:30;
    padding:12px 16px; display:flex; justify-content:space-between; align-items:center;
    background: linear-gradient(to bottom, #0a0a0f, transparent);
  }}
  .logo {{ display:flex; align-items:center; gap:8px; }}
  .logo svg {{ color:#3b82f6; }}
  .logo h1 {{ font-size:18px; font-weight:800; letter-spacing:3px; color:#f1f5f9; }}
  .logo h1 span {{ color:#3b82f6; font-size:12px; margin-left:2px; }}

  .step-bar {{ display:flex; gap:4px; background:#0f172a; padding:4px; border-radius:8px; border:1px solid #1e293b; }}
  .step-btn {{
    padding:6px 14px; font-size:12px; font-weight:600; border:none; border-radius:6px;
    cursor:default; transition:all 0.2s;
    color:#64748b; background:transparent;
  }}
  .step-btn.active {{ background:#2563eb; color:#fff; }}
  .step-btn.done {{ color:#10b981; }}

  /* ── Nodes ── */
  .node {{
    position:absolute; width:140px; transform:translate(-50%, -50%);
    transition: left 1s ease, top 1s ease, opacity 0.8s ease;
    z-index:20; cursor:pointer;
  }}
  .node-inner {{
    padding:10px 8px; border-radius:10px; border:1px solid #3b82f6;
    background:#0f172a; box-shadow:0 4px 20px rgba(0,0,0,0.5);
    display:flex; flex-direction:column; align-items:center; gap:6px;
    transition:all 0.3s;
  }}
  .node-inner:hover {{ background:#172554; transform:scale(1.05); }}
  .node-inner.special {{ border-color:#10b981; }}
  .node-inner.special:hover {{ background:#052e16; }}
  .node-icon {{ width:22px; height:22px; }}
  .node-icon.blue {{ color:#60a5fa; }}
  .node-icon.green {{ color:#34d399; }}
  .node-title {{ font-size:11px; font-weight:700; color:#e2e8f0; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:120px; }}
  .node-badge {{
    font-size:10px; padding:2px 8px; border-radius:10px; display:inline-block;
    background:rgba(59,130,246,0.15); color:#93c5fd;
  }}
  .node-inner.special .node-badge {{ background:rgba(16,185,129,0.15); color:#6ee7b7; }}
  .node-badge.debating {{ background:rgba(168,85,247,0.15); color:#c084fc; }}

  /* ── Breakout Rooms ── */
  .breakout-room {{
    position:absolute; z-index:10;
    border:2px dashed rgba(99,102,241,0.3); border-radius:24px;
    display:flex; flex-direction:column; align-items:center; padding-top:20px;
    cursor:pointer; transition:all 0.6s;
  }}
  .breakout-room:hover {{ border-color:rgba(129,140,248,0.5); }}
  .breakout-room.room1 {{ background:rgba(59,130,246,0.05); }}
  .breakout-room.room1:hover {{ background:rgba(59,130,246,0.1); }}
  .breakout-room.room2 {{ background:rgba(168,85,247,0.05); }}
  .breakout-room.room2:hover {{ background:rgba(168,85,247,0.1); }}

  .room-label {{
    padding:4px 14px; border-radius:20px; font-size:11px; font-weight:700;
    letter-spacing:2px; text-transform:uppercase; display:flex; align-items:center; gap:6px;
    background:#0f172a;
  }}
  .room1 .room-label {{ border:1px solid rgba(59,130,246,0.5); color:#60a5fa; }}
  .room2 .room-label {{ border:1px solid rgba(168,85,247,0.5); color:#c084fc; }}

  /* ── Bottom Context Bar ── */
  .context-bar {{
    position:absolute; bottom:16px; left:50%; transform:translateX(-50%); z-index:30;
    background:rgba(15,23,42,0.85); backdrop-filter:blur(8px);
    border:1px solid #334155; padding:10px 24px; border-radius:20px;
    font-size:13px; font-weight:500; color:#94a3b8; box-shadow:0 8px 32px rgba(0,0,0,0.4);
    pointer-events:none; white-space:nowrap;
  }}

  /* ── Right Console ── */
  .console {{
    width:300px; background:#0f172a; border-left:1px solid #1e293b;
    display:flex; flex-direction:column; z-index:30;
    box-shadow:-10px 0 30px -15px rgba(0,0,0,0.5);
  }}
  .console-header {{
    padding:12px 16px; border-bottom:1px solid #1e293b;
    display:flex; align-items:center; gap:8px;
  }}
  .console-header svg {{ color:#10b981; width:16px; height:16px; }}
  .console-header h2 {{ font-size:12px; font-weight:700; letter-spacing:2px; color:#e2e8f0; }}
  .console-body {{ flex:1; padding:12px 14px; overflow-y:auto; font-family:'JetBrains Mono','Fira Code',monospace; font-size:11px; display:flex; flex-direction:column; gap:8px; }}
  .log-line {{ padding-bottom:6px; border-bottom:1px solid rgba(30,41,59,0.5); line-height:1.5; word-break:break-all; }}
  .log-line .ts {{ opacity:0.35; margin-right:6px; }}
  .log-system {{ color:#64748b; }}
  .log-moderator {{ color:#60a5fa; }}
  .log-node {{ color:#f59e0b; }}
  .log-agents {{ color:#fbbf24; }}

  /* ── SVG Lines ── */
  .flow-svg {{ position:absolute; inset:0; width:100%; height:100%; pointer-events:none; z-index:10; }}
  @keyframes flow {{ to {{ stroke-dashoffset:-16; }} }}
  .flow-line {{ animation:flow 0.5s linear infinite; }}

  /* ── Modal ── */
  .modal-overlay {{
    position:fixed; inset:0; z-index:50;
    display:flex; align-items:center; justify-content:center;
    background:rgba(10,10,15,0.7); backdrop-filter:blur(4px);
  }}
  .modal-overlay.hidden {{ display:none; }}
  .modal {{
    background:#0f172a; border:1px solid #334155; width:520px; max-width:92vw;
    border-radius:14px; box-shadow:0 25px 50px rgba(0,0,0,0.5); overflow:hidden;
    display:flex; flex-direction:column;
    animation: modalIn 0.2s ease;
  }}
  @keyframes modalIn {{ from {{ opacity:0; transform:scale(0.95); }} to {{ opacity:1; transform:scale(1); }} }}
  .modal-header {{
    padding:14px 18px; border-bottom:1px solid #1e293b; display:flex;
    justify-content:space-between; align-items:center; background:rgba(30,41,59,0.4);
  }}
  .modal-header-left {{ display:flex; align-items:center; gap:8px; }}
  .modal-header h3 {{ font-weight:700; font-size:14px; color:#f1f5f9; }}
  .modal-close {{ background:none; border:none; color:#64748b; cursor:pointer; font-size:18px; padding:4px; }}
  .modal-close:hover {{ color:#fff; }}
  .modal-body {{ padding:18px; display:flex; flex-direction:column; gap:14px; font-size:13px; color:#94a3b8; max-height:420px; overflow-y:auto; }}

  /* ── Genome bar ── */
  .genome-row {{ display:flex; align-items:center; gap:8px; margin:3px 0; }}
  .genome-label {{ min-width:100px; font-size:11px; color:#64748b; }}
  .genome-track {{ flex:1; background:#1e293b; border-radius:4px; height:8px; }}
  .genome-fill {{ height:8px; border-radius:4px; transition:width 0.3s; }}
  .genome-val {{ min-width:24px; font-size:11px; text-align:right; color:#cbd5e1; font-weight:600; }}

  /* ── Transcript modal ── */
  .transcript-box {{
    background:#020617; border:1px solid #1e293b; border-radius:10px;
    padding:14px; max-height:320px; overflow-y:auto; font-size:12px; line-height:1.7;
  }}
  .transcript-box .spoken {{ color:#60a5fa; }}
  .transcript-box .inner {{ color:#c084fc; border-left:2px solid #7c3aed; padding-left:10px; background:rgba(124,58,237,0.06); margin:4px 0; padding:4px 10px; border-radius:4px; }}
  .transcript-box .speaker {{ font-weight:700; display:block; margin-bottom:2px; }}
  .transcript-box .alert {{ font-size:10px; color:#475569; text-align:center; text-transform:uppercase; letter-spacing:2px; border-top:1px solid #1e293b; padding-top:8px; margin-top:8px; }}

  /* ── Reaction card ── */
  .reaction-card {{
    background:#020617; border:1px solid #1e293b; border-radius:10px; padding:14px; position:relative; overflow:hidden;
  }}
  .reaction-badge {{
    position:absolute; top:0; right:0; background:#2563eb; color:#fff;
    font-size:9px; font-weight:700; padding:4px 10px; text-transform:uppercase;
    letter-spacing:1px; border-bottom-left-radius:8px;
  }}
  .reaction-metrics {{ display:flex; gap:8px; margin-top:12px; border-top:1px solid #1e293b; padding-top:10px; }}
  .metric-pill {{
    background:#0f172a; border:1px solid #1e293b; padding:4px 10px;
    border-radius:6px; font-size:11px;
  }}
  .metric-pill .val {{ font-weight:700; }}
  .metric-pill .val.hot {{ color:#ef4444; }}
  .metric-pill .val.blue {{ color:#3b82f6; }}
</style>
</head>
<body>
<div class="pantheon-root" id="root">

  <!-- LEFT CANVAS -->
  <div class="canvas" id="canvas" onclick="closeModal()">
    <div class="canvas-grid"></div>

    <!-- Header -->
    <div class="canvas-header" onclick="event.stopPropagation()">
      <div class="logo">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M15 13a4.5 4.5 0 0 1-3 4 4.5 4.5 0 0 1-3-4"/><path d="M12 18v4"/><path d="M8.5 4.5l3.5 3.5 3.5-3.5"/></svg>
        <h1>PANTHEON<span>UI</span></h1>
      </div>
      <div class="step-bar" id="stepBar"></div>
    </div>

    <!-- SVG layer for flow lines -->
    <svg class="flow-svg" id="svgLayer"></svg>

    <!-- Breakout room overlays (hidden until step 4) -->
    <div id="roomsContainer"></div>

    <!-- Agent & special nodes injected by JS -->
    <div id="nodesContainer"></div>

    <!-- Bottom context -->
    <div class="context-bar" id="contextBar"></div>
  </div>

  <!-- RIGHT CONSOLE -->
  <div class="console">
    <div class="console-header">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      <h2>SYSTEM LOGS</h2>
    </div>
    <div class="console-body" id="logContainer"></div>
  </div>

</div>

<!-- MODAL -->
<div class="modal-overlay hidden" id="modalOverlay" onclick="closeModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-header">
      <div class="modal-header-left">
        <span id="modalIcon">🔬</span>
        <h3 id="modalTitle">Inspector</h3>
      </div>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body" id="modalBody"></div>
  </div>
</div>

<script>
// ── DATA from Python ────────────────────────────────────────────────────────
const AGENTS = {agents_json};
const LOGS = {logs_json};
const REACTIONS = {reactions_json};
const TRANSCRIPTS = {transcripts_json};
const PIPELINE_STATUS = {status_json};
const GROUP_SIZE = {group_size_json};
let currentStep = {step};

// ── SVG Icons (inline) ─────────────────────────────────────────────────────
const ICON = {{
  brain: '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M15 13a4.5 4.5 0 0 1-3 4 4.5 4.5 0 0 1-3-4"/><path d="M12 18v4"/><path d="M8.5 4.5l3.5 3.5 3.5-3.5"/></svg>',
  user: '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  doc: '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>',
  users: '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  msg: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>',
}};

// ── Step Labels ─────────────────────────────────────────────────────────────
const STEP_LABELS = [
  "Boot Sequence",
  "Swarm Assembly",
  "Mass Session",
  "Breakout Rooms",
  "Synthesis",
  "Slide Deck",
  "Client Whisperer",
];
const CONTEXT_LABELS = [
  "Phase 1: Booting PANTHEON Core — Connecting to Modal...",
  "Phase 2: Swarm Assembly — Querying Supabase for agents (Click agents for Genomes)",
  "Phase 3: The Mass Session — Broadcasting Campaign Brief to Grid",
  "Phase 4: Breakout Rooms — Focus group debates in progress (Click rooms to spy)",
  "Phase 5: Final Synthesis — Claude Sonnet writing PANTHEON Report",
  "Phase 6: Presentation Architect — Building slide deck",
  "Phase 7: Client Whisperer — Drafting meeting prep document",
];

// ── Position Calculator ─────────────────────────────────────────────────────
function getPositions(step, agentCount) {{
  const n = Math.max(agentCount, 10);
  const pos = {{
    mod: {{ x:50, y:50, opacity:1, label:"Booting..." }},
    arch: {{ x:50, y:50, opacity:0, label:"" }},
    whisp: {{ x:50, y:50, opacity:0, label:"" }},
  }};
  for (let i = 0; i < n; i++) {{
    pos['a'+(i+1)] = {{ x:50, y:50, opacity:0, label:"" }};
  }}

  if (step === 1) {{
    pos.mod = {{ x:50, y:50, opacity:1, label:"Booting..." }};
  }} else if (step === 2 || step === 3) {{
    pos.mod = {{ x:50, y:15, opacity:1, label: step === 2 ? "Querying DB" : "Broadcasting Brief" }};
    const cols = n > 15 ? 7 : (n > 10 ? 6 : Math.min(n, 5));
    const rows = Math.ceil(n / cols);
    for (let i = 0; i < n; i++) {{
      const col = i % cols;
      const row = Math.floor(i / cols);
      const xSpacing = 80 / (cols + 1);
      const yStart = 40;
      const ySpacing = Math.min(22, 50 / (rows + 1));
      pos['a'+(i+1)] = {{
        x: 10 + (col+1) * xSpacing,
        y: yStart + row * ySpacing,
        opacity: 1,
        label: step === 2 ? "Spawned" : "Ingesting..."
      }};
    }}
  }} else if (step === 4) {{
    pos.mod = {{ x:50, y:12, opacity:1, label:"Monitoring Audio" }};
    const numRooms = Math.ceil(n / GROUP_SIZE) || 1;
    for (let i = 0; i < n; i++) {{
      const roomIdx = Math.floor(i / GROUP_SIZE);
      const inRoom = i % GROUP_SIZE;
      const thisRoomSize = Math.min(GROUP_SIZE, n - roomIdx * GROUP_SIZE);
      
      let cx, cy;
      if (numRooms <= 3) {{
          const roomSpanX = 90 / numRooms;
          cx = 5 + (roomIdx + 0.5) * roomSpanX;
          cy = 58;
      }} else {{
          const cols = Math.ceil(numRooms / 2);
          const roomCol = roomIdx % cols;
          const roomRow = Math.floor(roomIdx / cols);
          const roomSpanX = 90 / cols;
          cx = 5 + (roomCol + 0.5) * roomSpanX;
          cy = roomRow === 0 ? 42 : 74;
      }}

      const angle = (inRoom / thisRoomSize) * Math.PI * 2 - Math.PI / 2;
      const rx = Math.max(8, Math.min(12, 60 / thisRoomSize));
      const ry = Math.max(10, Math.min(16, 80 / thisRoomSize));
      pos['a'+(i+1)] = {{
        x: cx + rx * Math.cos(angle),
        y: cy + ry * Math.sin(angle),
        opacity: 1,
        label: "Debating"
      }};
    }}
  }} else if (step >= 5) {{
    pos.mod = {{ x:50, y:20, opacity:1, label: step === 5 ? "Synthesizing" : (step === 6 ? "Formatting" : "Whispering") }};
    pos.arch = {{ x:30, y:58, opacity: step >= 5 ? 1 : 0, label: step === 6 ? "Building Deck" : "Report Done" }};
    pos.whisp = {{ x:70, y:58, opacity: step >= 7 ? 1 : (step >= 5 ? 0.4 : 0), label: step === 7 ? "Drafting Prep" : "Standby" }};
    for (let i = 0; i < n; i++) {{
      pos['a'+(i+1)] = {{ x:50, y:120, opacity:0, label:"Dismissed" }};
    }}
  }}
  return pos;
}}

// ── Render ───────────────────────────────────────────────────────────────────
function render() {{
  const count = AGENTS.length;
  const positions = getPositions(currentStep, count);

  // Step bar
  const stepBar = document.getElementById('stepBar');
  stepBar.innerHTML = '';
  for (let s = 1; s <= 7; s++) {{
    const btn = document.createElement('div');
    btn.className = 'step-btn' + (s === currentStep ? ' active' : '') + (s < currentStep ? ' done' : '');
    btn.textContent = 'N' + s;
    btn.title = STEP_LABELS[s-1] || '';
    stepBar.appendChild(btn);
  }}

  // Context bar
  const ctxIdx = Math.min(currentStep - 1, CONTEXT_LABELS.length - 1);
  document.getElementById('contextBar').textContent = PIPELINE_STATUS || CONTEXT_LABELS[ctxIdx];

  // Nodes container
  const container = document.getElementById('nodesContainer');
  container.innerHTML = '';

  // Special nodes: Moderator, Architect, Whisperer
  const specials = [
    {{ id:'mod', icon:ICON.brain, title:'PANTHEON Mod', role:'Core', pos:positions.mod }},
    {{ id:'arch', icon:ICON.doc, title:'Presentation Architect', role:'Synthesis', pos:positions.arch }},
    {{ id:'whisp', icon:ICON.users, title:'Client Whisperer', role:'Synthesis', pos:positions.whisp }},
  ];
  specials.forEach(sp => {{
    if (sp.pos.opacity <= 0) return;
    const el = createNode(sp.id, sp.icon, sp.title, sp.pos.label || sp.role, sp.pos, true);
    container.appendChild(el);
  }});

  // Agent nodes
  for (let i = 0; i < count; i++) {{
    const a = AGENTS[i];
    const p = positions[a.id];
    if (!p || p.opacity <= 0) continue;
    const el = createNode(a.id, ICON.user, a.label, p.label || 'Agent', p, false);
    el.onclick = (e) => {{ e.stopPropagation(); openAgentModal(i); }};
    container.appendChild(el);
  }}

  // Breakout rooms
  const roomsContainer = document.getElementById('roomsContainer');
  roomsContainer.innerHTML = '';
  if (currentStep === 4) {{
    const numRooms = Math.ceil(count / GROUP_SIZE) || 1;
    for (let r = 0; r < numRooms; r++) {{
      let cx, cy, width, height;
      if (numRooms <= 3) {{
          const roomSpanX = 100 / numRooms;
          cx = roomSpanX * r; 
          cy = 30;
          width = roomSpanX - 4;
          height = 55;
      }} else {{
          const cols = Math.ceil(numRooms / 2);
          const roomCol = r % cols;
          const roomRow = Math.floor(r / cols);
          const roomSpanX = 100 / cols;
          cx = roomSpanX * roomCol;
          cy = roomRow === 0 ? 25 : 56;
          width = roomSpanX - 4;
          height = 30;
      }}
      
      const el = document.createElement('div');
      el.className = 'breakout-room room' + ((r % 2) + 1); 
      el.style.display = 'flex';
      el.style.left = (cx + 2) + '%';
      el.style.top = cy + '%';
      el.style.width = width + '%';
      el.style.height = height + '%';
      el.innerHTML = '<div class="room-label">' + ICON.msg + ' Spy on Room ' + (r+1) + '</div>';
      el.onclick = (e) => {{ e.stopPropagation(); openRoomModal(r); }};
      roomsContainer.appendChild(el);
    }}
  }}

  // SVG flow lines
  renderLines(positions, count);

  // Logs
  renderLogs();
}}

function createNode(id, iconSvg, title, badge, pos, isSpecial) {{
  const el = document.createElement('div');
  el.className = 'node';
  el.style.left = pos.x + '%';
  el.style.top = pos.y + '%';
  el.style.opacity = pos.opacity;
  if (pos.opacity <= 0) el.style.pointerEvents = 'none';

  const badgeClass = (currentStep === 4 && !isSpecial) ? 'node-badge debating' : 'node-badge';

  el.innerHTML = `
    <div class="node-inner ${{isSpecial ? 'special' : ''}}">
      <div class="node-icon ${{isSpecial ? 'green' : 'blue'}}">${{iconSvg}}</div>
      <div class="node-title">${{title}}</div>
      <div class="${{badgeClass}}">${{badge}}</div>
    </div>
  `;
  return el;
}}

function renderLines(positions, count) {{
  const svg = document.getElementById('svgLayer');
  svg.innerHTML = '';
  if (currentStep === 3) {{
    for (let i = 0; i < count; i++) {{
      const a = positions['a'+(i+1)];
      if (!a || a.opacity <= 0) continue;
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', positions.mod.x + '%');
      line.setAttribute('y1', positions.mod.y + '%');
      line.setAttribute('x2', a.x + '%');
      line.setAttribute('y2', a.y + '%');
      line.setAttribute('stroke', '#3b82f6');
      line.setAttribute('stroke-width', '1.5');
      line.setAttribute('stroke-dasharray', '8 8');
      line.setAttribute('class', 'flow-line');
      svg.appendChild(line);
    }}
  }} else if (currentStep >= 5) {{
    if (positions.arch.opacity > 0) {{
      const l1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      l1.setAttribute('x1', positions.mod.x + '%'); l1.setAttribute('y1', positions.mod.y + '%');
      l1.setAttribute('x2', positions.arch.x + '%'); l1.setAttribute('y2', positions.arch.y + '%');
      l1.setAttribute('stroke', '#10b981'); l1.setAttribute('stroke-width', '2');
      svg.appendChild(l1);
    }}
    if (positions.whisp.opacity > 0.3) {{
      const l2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      l2.setAttribute('x1', positions.mod.x + '%'); l2.setAttribute('y1', positions.mod.y + '%');
      l2.setAttribute('x2', positions.whisp.x + '%'); l2.setAttribute('y2', positions.whisp.y + '%');
      l2.setAttribute('stroke', '#10b981'); l2.setAttribute('stroke-width', '2');
      l2.setAttribute('stroke-dasharray', currentStep < 7 ? '6 6' : 'none');
      svg.appendChild(l2);
    }}
  }}
}}

function renderLogs() {{
  const logEl = document.getElementById('logContainer');
  logEl.innerHTML = '';
  LOGS.forEach((log, i) => {{
    const div = document.createElement('div');
    let cls = 'log-line log-system';
    if (log.includes('[MODERATOR]') || log.includes('Moderator') || log.includes('Node 1')) cls = 'log-line log-moderator';
    else if (log.includes('[AGENTS]') || log.includes('agent')) cls = 'log-line log-agents';
    else if (log.includes('Node ')) cls = 'log-line log-node';
    div.className = cls;
    const ts = String(Math.floor(i * 1.2)).padStart(2, '0') + ':' + String((i * 7) % 60).padStart(2, '0');
    div.innerHTML = '<span class="ts">' + ts + '</span>' + escapeHtml(log);
    logEl.appendChild(div);
  }});
  logEl.scrollTop = logEl.scrollHeight;
}}

// ── Modals ───────────────────────────────────────────────────────────────────
function openAgentModal(idx) {{
  const a = AGENTS[idx];
  const overlay = document.getElementById('modalOverlay');
  const title = document.getElementById('modalTitle');
  const body = document.getElementById('modalBody');
  const icon = document.getElementById('modalIcon');

  icon.textContent = '🧬';
  title.textContent = a.label + ' — ' + a.demo;

  // Check if we have a reaction for this agent
  const reaction = REACTIONS[idx] || null;

  if (currentStep <= 2 || !reaction) {{
    // Genome view
    body.innerHTML = genomeHTML(a);
  }} else {{
    // Reaction view
    body.innerHTML = reactionHTML(a, reaction);
  }}

  overlay.classList.remove('hidden');
}}

function openRoomModal(roomIdx) {{
  const overlay = document.getElementById('modalOverlay');
  const title = document.getElementById('modalTitle');
  const body = document.getElementById('modalBody');
  const icon = document.getElementById('modalIcon');

  icon.textContent = '🔊';
  const roomNum = roomIdx + 1;
  title.textContent = 'Room ' + roomNum + ': Live Transcript';

  const tb = TRANSCRIPTS[roomIdx];
  if (tb && tb.status === 'ok' && tb.transcript) {{
    body.innerHTML = formatTranscript(tb.transcript);
  }} else {{
    body.innerHTML = '<div style="color:#475569; text-align:center; padding:40px 0;">Transcript is being generated... Check back when Phase B completes.</div>';
  }}

  overlay.classList.remove('hidden');
}}

function closeModal() {{
  document.getElementById('modalOverlay').classList.add('hidden');
}}

// ── HTML Builders ────────────────────────────────────────────────────────────
function genomeHTML(agent) {{
  const g = agent.genome;
  const traits = [
    ['Openness', g.openness], ['Conscientiousness', g.conscientiousness],
    ['Extraversion', g.extraversion], ['Agreeableness', g.agreeableness],
    ['Neuroticism', g.neuroticism], ['Literacy', g.literacy],
    ['SES Friction', g.ses_friction], ['Influence', g.influence],
  ];
  let html = '<div style="background:#020617; border:1px solid #1e293b; border-radius:10px; padding:14px;">';
  html += '<div style="font-size:11px; color:#7c3aed; font-weight:700; letter-spacing:2px; margin-bottom:10px;">PERSONALITY GENOME</div>';
  traits.forEach(([label, val]) => {{
    const v = Math.max(0, Math.min(100, val || 50));
    const color = v < 35 ? '#ef4444' : (v < 65 ? '#f59e0b' : '#10b981');
    html += '<div class="genome-row">';
    html += '<div class="genome-label">' + label + '</div>';
    html += '<div class="genome-track"><div class="genome-fill" style="width:' + v + '%; background:' + color + '"></div></div>';
    html += '<div class="genome-val">' + v + '</div>';
    html += '</div>';
  }});
  html += '</div>';
  html += '<div style="margin-top:10px; font-size:11px; color:#475569;">';
  html += '<strong>Demographic:</strong> ' + escapeHtml(agent.demo) + '<br>';
  html += '<strong>Age:</strong> ' + agent.age + ' · <strong>Region:</strong> ' + escapeHtml(agent.region);
  html += '</div>';
  return html;
}}

function reactionHTML(agent, reaction) {{
  let html = '<div class="reaction-card">';
  html += '<div class="reaction-badge">Gut Reaction</div>';
  html += '<div style="font-size:11px; color:#475569; font-weight:700; letter-spacing:2px; margin-bottom:10px;">INITIAL CAMPAIGN ASSESSMENT</div>';
  html += '<p style="font-style:italic; color:#cbd5e1;">"' + escapeHtml(reaction.gut) + '"</p>';
  html += '<div class="reaction-metrics">';
  html += '<div class="metric-pill">Temp: <span class="val hot">' + reaction.temp + '/10</span></div>';
  html += '<div class="metric-pill">Emotion: <span class="val blue">' + escapeHtml(reaction.emotion) + '</span></div>';
  html += '<div class="metric-pill">Intent: <span class="val blue">' + escapeHtml(reaction.intent) + '</span></div>';
  html += '</div>';
  html += '</div>';

  // Also show genome below
  html += '<div style="margin-top:6px;">' + genomeHTML(agent) + '</div>';
  return html;
}}

function formatTranscript(text) {{
  // Parse transcript into spoken / inner thought blocks
  let html = '<div class="transcript-box">';
  const lines = text.split('\\n');
  let currentBlock = '';
  lines.forEach(line => {{
    const trimmed = line.trim();
    if (!trimmed) return;
    if (trimmed.match(/\\(Inner (Thought|Monologue)\\)/i)) {{
      html += '<div class="inner"><span class="speaker" style="color:#c084fc;">' + escapeHtml(trimmed.split(':')[0]) + ':</span>' + escapeHtml(trimmed.split(':').slice(1).join(':')) + '</div>';
    }} else if (trimmed.match(/\\(Spoken\\)/i)) {{
      html += '<div class="spoken"><span class="speaker" style="color:#60a5fa;">' + escapeHtml(trimmed.split(':')[0]) + ':</span>' + escapeHtml(trimmed.split(':').slice(1).join(':')) + '</div>';
    }} else if (trimmed.match(/^\\[/)) {{
      html += '<div><span class="speaker" style="color:#60a5fa;">' + escapeHtml(trimmed.split(':')[0]) + ':</span>' + escapeHtml(trimmed.split(':').slice(1).join(':')) + '</div>';
    }} else {{
      html += '<div style="margin:4px 0; color:#94a3b8;">' + escapeHtml(trimmed) + '</div>';
    }}
  }});
  html += '</div>';
  return html;
}}

function escapeHtml(str) {{
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// ── Init ─────────────────────────────────────────────────────────────────────
render();
</script>
</body>
</html>"""
    return html
