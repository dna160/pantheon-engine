import os
import datetime
import textwrap
import re
import streamlit as st
from dotenv import load_dotenv

import sys
from pathlib import Path

# Ensure we can find 'client_whisperer' at the root
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv(".env", override=True)

def _clean_html(html_str):
    return re.sub(r'^[ \t]+', '', html_str, flags=re.MULTILINE)

st.set_page_config(
    page_title="Human Whisperer",
    page_icon="🕵️",
    layout="wide",
)


# ── Supabase helper ───────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        return create_client(url, key)
    return None


def _save_whisper_run(
    prospect_name, linkedin_url, instagram_url,
    product_details, genome_id, strategy_result, simulated_life,
):
    """Insert a row into whisper_runs. Silent on failure."""
    sb = _get_supabase()
    if not sb:
        return
    try:
        sb.table("whisper_runs").insert({
            "prospect_name":   prospect_name,
            "linkedin_url":    linkedin_url,
            "instagram_url":   instagram_url,
            "product_details": product_details,
            "genome_id":       genome_id,
            "strategy_result": strategy_result,
            "simulated_life":  simulated_life,
        }).execute()
    except Exception as e:
        st.warning(f"Run history save failed (non-fatal): {e}")


def _load_previous_runs(limit: int = 30):
    """Fetch the most recent whisper_runs rows."""
    sb = _get_supabase()
    if not sb:
        return []
    try:
        resp = (
            sb.table("whisper_runs")
            .select(
                "id, created_at, prospect_name, linkedin_url, "
                "instagram_url, strategy_result, simulated_life, product_details"
            )
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        st.warning(f"Could not load previous analyses: {e}")
        return []


def _build_docx(prospect_name, strategy, simulated_life, linkedin_url="", instagram_url=""):
    from client_whisperer.docx_builder import build_whisper_docx
    return build_whisper_docx(
        prospect_name=prospect_name,
        strategy=strategy,
        simulated_life=simulated_life,
        linkedin_url=linkedin_url,
        instagram_url=instagram_url,
    )


# ── Fit status helpers ────────────────────────────────────────────────────────
FIT_ICONS = {
    "TRUE_FIT":    ("🟢", "TRUE FIT"),
    "PARTIAL_FIT": ("🟡", "PARTIAL FIT"),
    "NO_FIT":      ("🔴", "NO FIT"),
    "VERIFY_FIT":  ("🔵", "VERIFY FIT"),
}

DEPTH_LABELS = {1: "Surface", 2: "Behavioral", 3: "Emotional", 4: "Identity"}

_QUICK_BRIEF_CSS = textwrap.dedent("""
    <style>
    .qb-wrapper { margin-bottom: 1.5rem; }
    .qb-header { font-size: 0.7rem; font-weight: 700; color: #64748b; text-transform: uppercase;
                 letter-spacing: 0.12em; margin-bottom: 0.75rem; }
    .qb-hook-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 1rem; }
    .qb-hook-cell { background: #0f172a; border-radius: 0.625rem; padding: 0.875rem 1rem;
                    border-left: 3px solid transparent; }
    .qb-hook-cell-hook  { border-color: #f59e0b; }
    .qb-hook-cell-stay  { border-color: #6366f1; }
    .qb-hook-cell-close { border-color: #10b981; }
    .qb-hook-label { font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
                     letter-spacing: 0.1em; margin-bottom: 0.375rem; }
    .qb-label-hook  { color: #f59e0b; }
    .qb-label-stay  { color: #818cf8; }
    .qb-label-close { color: #34d399; }
    .qb-hook-text { font-size: 0.8rem; color: #cbd5e1; line-height: 1.45; }
    .qb-tp-header { font-size: 0.7rem; font-weight: 700; color: #64748b; text-transform: uppercase;
                    letter-spacing: 0.12em; margin-bottom: 0.5rem; }
    .qb-tp-row { background: #0f172a; border: 1px solid #1e293b; border-radius: 0.5rem;
                 padding: 0.75rem 1rem; margin-bottom: 0.5rem; }
    .qb-tp-point { font-size: 0.85rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.25rem; }
    .qb-tp-badge { display: inline-block; font-size: 0.65rem; font-weight: 600; padding: 0.15rem 0.5rem;
                   border-radius: 20px; background: rgba(99,102,241,0.15); color: #818cf8;
                   margin-bottom: 0.4rem; }
    .qb-tp-why { font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.35rem; line-height: 1.4; }
    .qb-tp-example-label { font-size: 0.65rem; font-weight: 600; color: #475569;
                            text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.2rem; }
    .qb-tp-example { font-size: 0.78rem; color: #c7d2fe; font-style: italic; background: #020617;
                     border-left: 2px solid #334155; padding: 0.4rem 0.6rem; border-radius: 0.25rem;
                     line-height: 1.45; }
    </style>
""")


def _render_hook_card(quick_brief: dict, prospect_name: str):
    """Render only the HOOK / STAY / CLOSE engagement card."""
    if not quick_brief:
        return
    hook_card = quick_brief.get("engagement_hook_card", {})
    hook  = hook_card.get("hook",  "")
    stay  = hook_card.get("stay",  "")
    close = hook_card.get("close", "")
    st.markdown(_QUICK_BRIEF_CSS, unsafe_allow_html=True)
    st.markdown(_clean_html(f"""
    <div class="qb-wrapper">
      <div class="qb-header">⚡ Kartu Cepat — {prospect_name}</div>
      <div class="qb-hook-grid">
        <div class="qb-hook-cell qb-hook-cell-hook">
          <div class="qb-hook-label qb-label-hook">🎣 Hook</div>
          <div class="qb-hook-text">{hook}</div>
        </div>
        <div class="qb-hook-cell qb-hook-cell-stay">
          <div class="qb-hook-label qb-label-stay">🔗 Pertahankan</div>
          <div class="qb-hook-text">{stay}</div>
        </div>
        <div class="qb-hook-cell qb-hook-cell-close">
          <div class="qb-hook-label qb-label-close">🎯 Close</div>
          <div class="qb-hook-text">{close}</div>
        </div>
      </div>
    </div>
    """), unsafe_allow_html=True)


def _render_talking_points(quick_brief: dict, key_suffix: str = "main"):
    """Render the numbered Talking Point expanders (no hook card)."""
    if not quick_brief:
        return
    talking_points = quick_brief.get("key_talking_points", [])
    if not talking_points:
        return
    st.markdown(_QUICK_BRIEF_CSS, unsafe_allow_html=True)
    st.markdown(_clean_html("""
    <div class="qb-tp-header">💬 Talking Points Utama</div>
    """), unsafe_allow_html=True)
    for i, tp in enumerate(talking_points):
        point  = tp.get("point",           "")
        why    = tp.get("why_it_lands",    "")
        example = tp.get("example_phrasing", "")
        driver  = tp.get("genome_driver",    "")
        with st.expander(f"💡 Talking Point {i + 1}", expanded=False):
            if point:
                st.markdown(
                    f'<div class="qb-tp-point" style="font-size:0.9rem;font-weight:700;'
                    f'color:#e2e8f0;margin-bottom:0.5rem;line-height:1.4;">{point}</div>',
                    unsafe_allow_html=True,
                )
            if driver:
                st.markdown(f'<div class="qb-tp-badge">🧬 {driver}</div>', unsafe_allow_html=True)
            if why:
                st.markdown(
                    f'<div class="qb-tp-why"><strong>Mengapa efektif:</strong> {why}</div>',
                    unsafe_allow_html=True,
                )
            if example:
                st.markdown(
                    f'<div class="qb-tp-example-label">Contoh kalimat — sesuaikan, jangan dibaca verbatim</div>'
                    f'<div class="qb-tp-example">"{example}"</div>',
                    unsafe_allow_html=True,
                )


def _render_quick_brief(quick_brief: dict, prospect_name: str, key_suffix: str = "main"):
    """Render the full Quick Brief: hook card + talking points. (Legacy / standalone use.)"""
    _render_hook_card(quick_brief, prospect_name)
    _render_talking_points(quick_brief, key_suffix=key_suffix)


def _render_whisperer_output(
    prospect_name, result, simulated_life,
    linkedin_url="", instagram_url="",
    show_download=True, key_suffix="main",
):
    """Render the full Human Whisperer output using the new premium layout."""
    if "error" in result:
        st.error(f"Processing error: {result['error']}")
        return

    # Extract dynamic text from PANTHEON string (Age, Region, Background)
    region = "Unknown Region"
    background = "Professional"
    for line in simulated_life.split('\n'):
        if "Region:" in line:
            region = line.split("Region:")[-1].strip()
        if line.startswith("Background:"):
            background = line.split("Background:")[-1].strip()

    initials = "".join([w[0].upper() for w in prospect_name.split() if w])[:2]
    
    # Extract Human Whisperer sections
    snap = result.get("section_1_human_snapshot", {})
    arch = result.get("section_2_conversation_architecture", {})
    sig = result.get("section_3_signal_reading", {})
    pf = result.get("section_5_product_fit", {})
    
    fit_status = pf.get("fit_status", "VERIFY FIT")
    fit_rationale = pf.get("fit_rationale", pf.get("pain_it_addresses", ""))

    # Injecting Custom CSS for the Premium Aesthetic
    st.markdown(textwrap.dedent("""
        <style>
        .report-bg { font-family: 'Inter', sans-serif; color: #cbd5e1; }
        .nav-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
        .nav-brand { color: #818cf8; font-weight: 600; font-size: 0.875rem; letter-spacing: 0.05em; }

        .premium-card { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 0.75rem; padding: 1.5rem; position: relative; overflow: hidden; margin-bottom: 1.5rem; }
        .card-accent-left { position: absolute; top: 0; left: 0; width: 4px; height: 100%; background-color: #6366f1; }

        .header-title { font-size: 1.5rem; font-weight: 700; color: #ffffff; margin-bottom: 0.25rem; line-height: 1.2; }
        .subtitle { color: #94a3b8; font-size: 0.875rem; margin-top: 0.25rem; display: flex; align-items: center; }
        .avatar { width: 48px; height: 48px; border-radius: 50%; background-color: #1e293b; border: 1px solid #334155; display: flex; align-items: center; justify-content: center; font-weight: 700; color: #818cf8; font-size: 1.25rem; }

        .sanity-box { background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 0.5rem; padding: 0.75rem; margin-top: 1.25rem; }
        .sanity-title { color: #fbbf24; font-weight: 600; font-size: 0.875rem; margin-bottom: 0.25rem; }
        .sanity-text { color: rgba(253, 230, 138, 0.7); font-size: 0.75rem; line-height: 1.4; }

        .section-label { font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1rem; }

        .hook-item { display: flex; align-items: flex-start; margin-bottom: 1rem; }
        .hook-icon-wrap { margin-top: 0.25rem; margin-right: 0.75rem; padding: 0.375rem; border-radius: 0.25rem; font-size: 0.875rem; line-height: 1; }
        .hook-bg-1 { background-color: rgba(16, 185, 129, 0.1); color: #34d399; }
        .hook-bg-2 { background-color: rgba(59, 130, 246, 0.1); color: #60a5fa; }
        .hook-bg-3 { background-color: rgba(168, 85, 247, 0.1); color: #c084fc; }

        .closer-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; }
        .closer-box { background-color: #0f172a; border-radius: 0.75rem; padding: 1.25rem; }
        .box-green { border: 1px solid rgba(6, 78, 59, 0.5); }
        .box-red { border: 1px solid rgba(136, 19, 55, 0.5); }
        .closer-title-green { color: #34d399; font-weight: 700; font-size: 0.875rem; margin-bottom: 0.75rem; }
        .closer-title-red { color: #fb7185; font-weight: 700; font-size: 0.875rem; margin-bottom: 0.75rem; }
        .closer-list { list-style: none; padding: 0; margin: 0; font-size: 0.875rem; color: #cbd5e1; }
        .closer-list li { margin-bottom: 0.5rem; display: flex; align-items: flex-start; }
        .check-icon { margin-right: 0.5rem; display: inline-block; }
        .text-green { color: #10b981; }
        .text-red { color: #f43f5e; }

        .playbook-card { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 0.75rem; overflow: hidden; margin-bottom: 1.5rem; }
        .playbook-header { background-color: rgba(30, 41, 59, 0.5); padding: 1rem; border-bottom: 1px solid #1e293b; color: #cbd5e1; font-weight: 700; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.1em; }
        .step-row { padding: 1.5rem; border-bottom: 1px solid rgba(30, 41, 59, 0.5); display: flex; align-items: flex-start; }
        .step-row:last-child { border-bottom: none; }
        .step-row:hover { background-color: rgba(30, 41, 59, 0.2); }
        .step-num { width: 32px; height: 32px; border-radius: 50%; background-color: rgba(99, 102, 241, 0.2); color: #818cf8; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.875rem; flex-shrink: 0; margin-right: 1rem; }
        .step-title { color: #e2e8f0; font-weight: 700; margin-bottom: 0.25rem; font-size: 1rem; }
        .step-desc { color: #94a3b8; font-size: 0.875rem; margin-bottom: 0.75rem; }
        .dialogue-box { background-color: #020617; border: 1px solid #1e293b; border-radius: 0.375rem; padding: 0.75rem 0.75rem 0.75rem 2.25rem; position: relative; font-size: 0.875rem; color: #c7d2fe; font-style: italic; }
        .quote-icon { position: absolute; left: 0.75rem; top: 0.75rem; color: #475569; font-style: normal; }

        /* ── Download button — gold, distinct from expanders ── */
        div[data-testid="stDownloadButton"] > button {
            background: linear-gradient(135deg, #E8B04B 0%, #c9922a 100%);
            color: #0D1B2A;
            font-weight: 700;
            font-size: 0.875rem;
            letter-spacing: 0.04em;
            border: none;
            border-radius: 0.5rem;
            padding: 0.6rem 1.25rem;
            width: 100%;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(232,176,75,0.25);
            transition: opacity 0.15s;
        }
        div[data-testid="stDownloadButton"] > button:hover { opacity: 0.88; }
        </style>
    """), unsafe_allow_html=True)

    # Top Nav
    st.markdown(textwrap.dedent(f"""
        <div class="report-bg">
            <div class="nav-bar">
                <div class="nav-brand">WHISPR <span style="color:#64748b">/</span> PIPELINE <span style="color:#64748b">/</span> {prospect_name.upper()}</div>
            </div>
        </div>
    """), unsafe_allow_html=True)

    # ── 1. Summary cards (always visible — no expander wrapper) ───────────────
    col_left, col_right = st.columns([1, 2], gap="large")

    # ==========================
    # LEFT COLUMN: Identity & Intel
    # ==========================
    with col_left:
        # 1. Identity Card
        st.markdown(_clean_html(f"""
        <div class="premium-card">
            <div class="card-accent-left"></div>
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <div class="header-title">{prospect_name}</div>
                    <div class="subtitle">💼 {background[:60]}{'...' if len(background)>60 else ''}</div>
                    <div class="subtitle">📍 {region}</div>
                </div>
                <div class="avatar">{initials}</div>
            </div>
            <div class="sanity-box">
                <div class="sanity-title">🚩 OBJECTIVE: {fit_status.upper()}</div>
                <div class="sanity-text">{fit_rationale}</div>
            </div>
        </div>
        """), unsafe_allow_html=True)

        # 2. Visual Intel / Hooks (from snapshot & signals)
        hook_1 = snap.get("what_they_actually_need", "Efisiensi dan menghemat waktu.")
        hook_2 = snap.get("pride_point", "Pencapaian profesional.")
        hook_3 = snap.get("one_thing_to_remember", "Jangan terlalu memaksakan penjualan (oversell).")
        open_sigs = sig.get("open_signals", [])
        if len(open_sigs) >= 2:
            hook_1 = open_sigs[0]
            hook_2 = open_sigs[1]

        st.markdown(_clean_html(f"""
        <div class="premium-card">
            <div class="section-label">🎯 Visual Intel (Hooks)</div>
            <div class="hook-item">
                <div class="hook-icon-wrap hook-bg-1">🎯</div>
                <div>
                    <div style="font-size:0.875rem; font-weight:600; color:#e2e8f0;">Dorongan Utama</div>
                    <div style="font-size:0.75rem; color:#94a3b8;">{hook_1}</div>
                </div>
            </div>
            <div class="hook-item">
                <div class="hook-icon-wrap hook-bg-2">⭐</div>
                <div>
                    <div style="font-size:0.875rem; font-weight:600; color:#e2e8f0;">Titik Kebanggaan</div>
                    <div style="font-size:0.75rem; color:#94a3b8;">{hook_2}</div>
                </div>
            </div>
            <div class="hook-item">
                <div class="hook-icon-wrap hook-bg-3">⚡</div>
                <div>
                    <div style="font-size:0.875rem; font-weight:600; color:#e2e8f0;">Aturan Utama</div>
                    <div style="font-size:0.75rem; color:#94a3b8;">{hook_3}</div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    # ==========================
    # RIGHT COLUMN: Playbook
    # ==========================
    with col_right:
        # 3. Win/Lose grid
        win_1 = pf.get("how_to_introduce_it", "Bingkasi sesuai dengan tujuan inti mereka.")
        win_2 = snap.get("what_makes_them_trust", "Angka langsung, tanpa kerumitan.")
        win_3 = pf.get("pain_it_addresses", "Menyelesaikan inefisiensi.")
        lose_1 = snap.get("what_makes_them_shut_down", "Bukti sosial, taktik tekanan tinggi.")
        lose_2 = pf.get("honest_limitation", "Berjanji berlebihan pada ruang lingkup (scope).")
        lose_3 = (sig.get("close_signals") or ["Mengabaikan batasan mereka."])[0]

        st.markdown(_clean_html(f"""
        <div class="closer-grid">
            <div class="closer-box box-green">
                <div class="closer-title-green">✔️ CARA MEMENANGKAN MEREKA</div>
                <ul class="closer-list">
                    <li><span class="check-icon text-green">✓</span> {win_1}</li>
                    <li><span class="check-icon text-green">✓</span> {win_2}</li>
                    <li><span class="check-icon text-green">✓</span> {win_3}</li>
                </ul>
            </div>
            <div class="closer-box box-red">
                <div class="closer-title-red">✖️ CARA KEHILANGAN MEREKA</div>
                <ul class="closer-list">
                    <li><span class="check-icon text-red">✗</span> {lose_1}</li>
                    <li><span class="check-icon text-red">✗</span> {lose_2}</li>
                    <li><span class="check-icon text-red">✗</span> {lose_3}</li>
                </ul>
            </div>
        </div>
        """), unsafe_allow_html=True)

        # 4. Meeting Blueprint stages + Talking Points
        st.markdown(_clean_html("""
        <div class="playbook-card">
            <div class="playbook-header">📋 Panduan Client</div>
        """), unsafe_allow_html=True)

        stages_to_show = [
            ("Pembukaan & Cek", arch.get("stage_1_arrive", {})),
            ("Mengubah Sudut Pandang", arch.get("stage_5_reframe", {})),
        ]
        step_idx = 1
        for title, stage_data in stages_to_show:
            if stage_data:
                purpose = stage_data.get("purpose", title)
                content = stage_data.get("content", "")
                st.markdown(_clean_html(f"""
                <div class="step-row">
                    <div class="step-num">{step_idx}</div>
                    <div style="width:100%;">
                        <div class="step-title">{title}</div>
                        <div class="step-desc">{purpose}</div>
                        <div style="font-size:0.65rem;color:#475569;margin-bottom:0.25rem;
                                    text-transform:uppercase;letter-spacing:0.08em;">
                            Contoh kalimat — sesuaikan, jangan dibaca verbatim
                        </div>
                        <div class="dialogue-box">
                            <span class="quote-icon">💬</span>
                            {content}
                        </div>
                    </div>
                </div>
                """), unsafe_allow_html=True)
                step_idx += 1

        cta_stage = arch.get("stage_7_cta", {})
        if cta_stage:
            st.markdown(_clean_html(f"""
            <div class="step-row">
                <div class="step-num">{step_idx}</div>
                <div style="width:100%;">
                    <div class="step-title">Penutupan Rendah Gesekan (Low-Friction Close)</div>
                    <div class="step-desc">{cta_stage.get('purpose', 'Beri mereka jalan keluar.')}</div>
                    <div style="font-size:0.65rem;color:#475569;margin-bottom:0.25rem;
                                text-transform:uppercase;letter-spacing:0.08em;">
                        Contoh kalimat — sesuaikan, jangan dibaca verbatim
                    </div>
                    <div class="dialogue-box">
                        <span class="quote-icon">💬</span>
                        {cta_stage.get('content', '')}
                    </div>
                </div>
            </div>
            """), unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # 5. Talking Points — inside Panduan Client column
        quick_brief = result.get("section_0_quick_brief", {})
        _render_talking_points(quick_brief, key_suffix=key_suffix)

    # ── 2. Kartu Cepat (hook card only) ────────────────────────────────────────
    quick_brief = result.get("section_0_quick_brief", {})
    _render_hook_card(quick_brief, prospect_name)

    # ── 3. Download button (gold, visually distinct) ────────────────────────────
    if show_download:
        docx_bytes = _build_docx(prospect_name, result, simulated_life, linkedin_url, instagram_url)
        safe_name  = prospect_name.replace(" ", "_").replace("/", "-")
        date_str   = datetime.date.today().strftime("%Y%m%d")
        st.download_button(
            label="⬇  Download Dokumen Persiapan Percakapan (.docx)",
            data=docx_bytes,
            file_name=f"{safe_name}_Playbook_{date_str}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key=f"dl_{key_suffix}",
            use_container_width=True,
        )
        st.write("")

    # ── 4. Deep Dive Raw Data (collapsible) ─────────────────────────────────────
    with st.expander("🔽 Lihat Data Psikologis Mentah (Untuk Persiapan)", expanded=False):
        st.markdown("### Ringkasan Genom PANTHEON")
        cols = st.columns(2)
        with cols[0]:
            st.markdown(f"**Ringkasan Bahasa Sederhana:**\n\n{result.get('plain_language_brief', 'Tidak ada ringkasan.')}")
        with cols[1]:
            st.markdown(f"**Pasca Pertemuan:**\n\n{result.get('section_6_post_conversation', {}).get('within_24_hours', '')}")
        st.divider()
        st.text(simulated_life)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🕵️ Human Whisperer")
    st.caption("PANTHEON-powered conversation intelligence")
    st.divider()

    apify_token   = os.getenv("APIFY_API_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    sb_url        = os.getenv("SUPABASE_URL")

    st.markdown("**Environment**")
    st.markdown(f"{'🟢' if anthropic_key else '🔴'} Anthropic API")
    st.markdown(f"{'🟢' if apify_token  else '🟡'} Apify (scraping) {'— mock mode' if not apify_token else ''}")
    st.markdown(f"{'🟢' if sb_url       else '🔴'} Supabase")
    st.divider()
    st.caption("Pipeline: LinkedIn → Instagram → Vision → Genome → Human Whisperer")


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_new, tab_history = st.tabs(["New Analysis", "Previous Analyses"])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — New Analysis
# ═════════════════════════════════════════════════════════════════════════════
with tab_new:
    st.header("Human Whisperer")
    st.markdown(
        "Enter a prospect's LinkedIn and Instagram, plus what you're offering. "
        "The engine builds their full life blueprint and returns a hyper-targeted "
        "conversation prep document — sanity check, human snapshot, 7-stage conversation "
        "architecture, signal reading guide, and a product fit summary."
    )

    with st.form("whisper_form"):
        col1, col2 = st.columns(2)
        with col1:
            linkedin_url = st.text_input(
                "LinkedIn Profile URL",
                placeholder="https://linkedin.com/in/username",
            )
        with col2:
            instagram_url = st.text_input(
                "Instagram Profile URL",
                placeholder="https://instagram.com/username",
            )

        product_details = st.text_area(
            "Product / Service Brief",
            height=140,
            placeholder=(
                "Describe what you're offering — what it does, who it's for, "
                "what it genuinely delivers, and what it cannot do. "
                "Honesty here makes the sanity check meaningful."
            ),
        )

        submitted = st.form_submit_button("Run Human Whisperer", type="primary", use_container_width=True)

    if submitted:
        if not linkedin_url or not instagram_url or not product_details:
            st.error("All three fields are required.")
            st.stop()

        from client_whisperer.scrapers        import scrape_linkedin, scrape_instagram
        from client_whisperer.vision          import analyze_images
        from client_whisperer.engine          import run_pantheon_simulation
        from client_whisperer.human_whisperer import run_human_whisperer

        progress = st.container()

        def step(label):
            return progress.status(label, expanded=False)

        with step("Step 1 — Scraping LinkedIn") as s:
            linkedin_data = scrape_linkedin(linkedin_url)
            if "error" in linkedin_data:
                s.update(label="Step 1 — LinkedIn ⚠️ (used fallback)", state="error", expanded=False)
            else:
                s.update(label=f"Step 1 — LinkedIn: {linkedin_data.get('name', '—')}", state="complete")

        with step("Step 2 — Scraping Instagram") as s:
            instagram_data = scrape_instagram(instagram_url)
            if "error" in instagram_data:
                s.update(label="Step 2 — Instagram ⚠️ (used fallback)", state="error", expanded=False)
            else:
                s.update(label=f"Step 2 — Instagram: {instagram_data.get('follower_count', 0):,} followers", state="complete")

        with step("Step 3 — Vision analysis on recent images") as s:
            images          = instagram_data.get("recent_images", [])
            vision_insights = analyze_images(images)
            s.update(label=f"Step 3 — Vision: {len(images)} image(s) analysed", state="complete")

        with step("Step 4 — Genome inference + life blueprint (PANTHEON)") as s:
            engine_result  = run_pantheon_simulation(
                linkedin_data=linkedin_data,
                insta_data=instagram_data,
                vision_insights=vision_insights,
            )
            simulated_life = engine_result["simulated_life"]
            genome_id      = engine_result.get("genome_id")
            prospect_name  = engine_result.get("prospect_name", linkedin_data.get("name", "Unknown"))
            s.update(label="Step 4 — PANTHEON life blueprint complete", state="complete")

        with step("Step 5 — Human Whisperer (sanity check + 5 passes + conversation prep)") as s:
            result = run_human_whisperer(
                simulated_life=simulated_life,
                product_details=product_details,
                prospect_name=prospect_name,
            )
            if "error" in result:
                s.update(label="Step 5 — Human Whisperer failed", state="error")
                st.error(result["error"])
                st.stop()
            s.update(label="Step 5 — Conversation prep ready", state="complete")

        # Save run to Supabase
        _save_whisper_run(
            prospect_name=prospect_name,
            linkedin_url=linkedin_url,
            instagram_url=instagram_url,
            product_details=product_details,
            genome_id=genome_id,
            strategy_result=result,
            simulated_life=simulated_life,
        )

        _render_whisperer_output(
            prospect_name=prospect_name,
            result=result,
            simulated_life=simulated_life,
            linkedin_url=linkedin_url,
            instagram_url=instagram_url,
            key_suffix="new",
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — Previous Analyses
# ═════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.header("Previous Analyses")

    if st.button("🔄 Refresh", key="refresh_history"):
        st.rerun()

    runs = _load_previous_runs(limit=30)

    if not runs:
        st.info("No previous analyses found. Run the pipeline in the New Analysis tab.")
    else:
        for run in runs:
            created = (run.get("created_at") or "")[:16].replace("T", " ")
            name    = run.get("prospect_name") or "Unknown"
            result  = run.get("strategy_result") or {}

            # Determine fit status for the label
            fit_raw  = (result.get("section_5_product_fit") or {}).get("fit_status", "")
            ficon, _ = FIT_ICONS.get(fit_raw, ("⚪", fit_raw))

            with st.expander(f"**{name}** — {created}  {ficon}"):
                li  = run.get("linkedin_url")  or ""
                ig  = run.get("instagram_url") or ""
                if li: st.caption(f"LinkedIn: {li}")
                if ig: st.caption(f"Instagram: {ig}")

                prod = run.get("product_details") or ""
                if prod:
                    st.markdown("**Product / Service Brief**")
                    st.caption(prod)

                sim_life = run.get("simulated_life") or ""

                # DOCX download for historical run
                if result and sim_life:
                    docx_bytes = _build_docx(name, result, sim_life, li, ig)
                    safe_name  = name.replace(" ", "_").replace("/", "-")
                    date_str   = (run.get("created_at") or "")[:10].replace("-", "")
                    st.download_button(
                        label="⬇ Download Conversation Prep (.docx)",
                        data=docx_bytes,
                        file_name=f"{safe_name}_HumanWhisperer_{date_str}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"dl_{run['id']}",
                    )

                _render_whisperer_output(
                    prospect_name=name,
                    result=result,
                    simulated_life=sim_life,
                    linkedin_url=li,
                    instagram_url=ig,
                    show_download=False,
                    key_suffix=run["id"],
                )
