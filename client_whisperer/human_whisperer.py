"""
Human Whisperer — Core Processing Engine
=========================================
Transforms a PANTHEON Life Blueprint + product brief into a full
6-section conversation prep document using the Human Whisperer methodology.

Pipeline:
  1. Sanity Check  — product vs. pain alignment
  2. Pass 1-5      — Product Read, Genome Read, Pain Mapping, Solution Mapping,
                     Conversation Mapping
  3. Section Gen   — 6-section structured output (JSON → rendered)

Output schema matches HumanWhispererOutput (Pydantic).
"""

from __future__ import annotations

import json
from typing import List, Optional
from anthropic import Anthropic
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

class EngagementHookCard(BaseModel):
    hook: str = Field(
        description=(
            "Kalimat pembuka 1 kalimat yang menarik perhatian mereka dalam 30 detik pertama. "
            "Berdasarkan chronesthesia_capacity (tinggi=hook visi masa depan / rendah=hook rasa sakit segera) "
            "dan identity_fusion (tinggi=framing kelompok/keluarga / rendah=framing keunggulan pribadi). "
            "Harus merujuk sesuatu yang spesifik dari genom atau blueprint mereka — bukan generik."
        )
    )
    stay: str = Field(
        description=(
            "Wawasan 1 kalimat yang membuat mereka tetap terlibat setelah kepercayaan mulai terbuka. "
            "Berdasarkan gaya decision_making (bukti vs intuisi) dan tom_social_modeling "
            "(tinggi=mereka membaca pitch — jadilah autentik; rendah=pendekatan standar efektif). "
            "Ini yang membuktikan Anda memahami dunia mereka, bukan hanya masalah mereka."
        )
    )
    close: str = Field(
        description=(
            "Langkah 1 kalimat yang mendorong mereka ke tindakan. "
            "Berdasarkan readiness_level dan executive_flexibility "
            "(tinggi exec_flex=mereka menyembunyikan perasaan nyata di balik ketenangan profesional — "
            "gali lebih dalam dari penampilan; rendah exec_flex=reaksi mereka terlihat, percaya yang Anda lihat). "
            "Sesuaikan dengan kesiapan: level 4-5 = close langsung; level 2-3 = langkah selanjutnya saja."
        )
    )


class KeyTalkingPoint(BaseModel):
    point: str = Field(
        description="Pesan inti yang harus disampaikan — apa yang perlu mereka yakini setelah percakapan. 1 kalimat."
    )
    why_it_lands: str = Field(
        description=(
            "Mengapa poin ini beresonansi dengan ORANG INI berdasarkan genom mereka. "
            "Rujuk skor trait atau sinyal blueprint spesifik yang membuatnya relevan."
        )
    )
    example_phrasing: str = Field(
        description=(
            "Satu contoh bagaimana poin ini bisa diungkapkan dalam percakapan. "
            "Ini adalah CONTOH, bukan skrip. Praktisi harus mengadaptasinya, bukan membacanya. "
            "Harus terasa natural untuk skor communication_style mereka."
        )
    )
    genome_driver: str = Field(
        description="Trait PANTHEON utama atau wawasan yang mendorong talking point ini."
    )


class QuickBrief(BaseModel):
    engagement_hook_card: EngagementHookCard
    key_talking_points: List[KeyTalkingPoint] = Field(
        description=(
            "3–5 talking point, diurutkan berdasarkan prioritas. Setiap poin adalah pesan inti, "
            "rasional genomnya, dan satu contoh kalimat. "
            "Cakup: (1) membangun kepercayaan, (2) menggali rasa sakit, (3) reframing, "
            "(4) kesesuaian produk, (5) closing — tapi hanya sertakan poin yang benar-benar relevan."
        )
    )


class HumanSnapshot(BaseModel):
    who_they_are: str = Field(description="1–2 sentences, plain language — no clinical jargon.")
    how_they_see_themselves: str = Field(description="Self-image vs. reality gap.")
    what_they_want: str = Field(description="Their stated desire.")
    what_they_actually_need: str = Field(description="Real need per PANTHEON genome and blueprint.")
    how_they_make_decisions: str = Field(description="Decision style and key triggers.")
    what_makes_them_trust: str = Field(description="Specific behavioral trust triggers.")
    what_makes_them_shut_down: str = Field(description="Specific behavioral distrust triggers.")
    pride_point: str = Field(description="What they're proud of — never challenge this, build on it.")
    real_fear: str = Field(description="The thing they won't say first.")
    readiness_level: int = Field(description="1–5 scale: 1=not ready, 5=ready to act.", ge=1, le=5)
    one_thing_to_remember: str = Field(description="The single most important insight walking in.")


class ProbeQuestion(BaseModel):
    question: str = Field(description="The question — plain, conversational, specific.")
    purpose: str = Field(description="What signal this question is designed to extract.")
    depth_level: int = Field(description="1=surface, 2=behavioral, 3=emotional, 4=identity.", ge=1, le=4)
    open_follow_up: str = Field(description="Where to go if they engage deeply.")
    back_out: str = Field(description="How to redirect if they close down.")
    genome_link: str = Field(description="Which genome trait this question targets.")


class ConversationStage(BaseModel):
    stage_name: str
    duration_minutes: str
    purpose: str
    content: str = Field(
        description=(
            "The substantive guidance for this stage — specific to THIS person's genome and product. "
            "This is NOT a meta-description of what should go here. It IS the actual content. "
            "For Stage 1 (Arrive): the talking point to convey + 1 example phrasing. "
            "For Stage 2 (Common Ground): 2–3 specific conversation threads anchored to their life blueprint. "
            "For Stage 4 (Reflect): the mirror statement that names their real situation without judgment. "
            "For Stage 5 (Reframe): the reframe that shifts their perspective on the problem. "
            "For Stage 6 (Framework): 3–4 concrete steps with plain names and plain outcomes. "
            "For Stage 7 (CTA): the exact low-friction ask calibrated to their readiness level. "
            "NEVER output: 'Sistem navigasi, bukan skrip' or any other meta-instruction as content. "
            "ALWAYS output: actual words, ideas, and examples a practitioner can work with."
        )
    )


class ConversationArchitecture(BaseModel):
    stage_1_arrive: ConversationStage
    stage_2_common_ground: ConversationStage
    stage_3_probe: List[ProbeQuestion] = Field(
        description="Minimum 10, maximum 20. At least 2 per depth level (1-4). "
                    "At least 3 targeting SHAME_ARCHITECTURE indirectly. "
                    "At least 2 referencing PREVIOUS_ATTEMPTS without making them feel like a failure. "
                    "Sequence: aspiration → friction → consequence → emotion → ownership."
    )
    stage_4_reflect: ConversationStage
    stage_5_reframe: ConversationStage
    stage_6_framework: ConversationStage
    stage_7_cta: ConversationStage


class BackOutScripts(BaseModel):
    b1: str = Field(description="Gentle redirect — 'Got it — we don't need to go there. Let me ask you something a bit different...'")
    b2: str = Field(description="Normalize and pivot — normalize the resistance, offer an alternative angle.")
    b3: str = Field(description="Step back entirely — return to a less sensitive topic from Stage 2.")
    b4: str = Field(description="Hard stop — respect their boundary and close gracefully.")


class SignalReadingGuide(BaseModel):
    open_signals: List[str] = Field(
        description=(
            "5–8 specific behavioral cues that indicate this person is opening up and ready to go deeper. "
            "Each signal must be tied to THIS person's genome traits — not generic signals. "
            "Reference specific trait scores (e.g., 'They start using \"kita\" instead of \"saya\" — high identity_fusion (78) "
            "means they've mentally joined the outcome'). Minimum 5 signals."
        )
    )
    close_signals: List[str] = Field(
        description=(
            "5–8 specific behavioral cues that indicate this person is shutting down or pulling back. "
            "Each signal must reference this person's genome (e.g., 'Answers become one-word — "
            "high executive_flexibility (71) means they're masking discomfort, not agreeing'). Minimum 5 signals."
        )
    )
    back_out_scripts: BackOutScripts = Field(
        description=(
            "Four calibrated back-out scripts (b1–b4) for when this person closes down during a probe. "
            "Each script must be written for THIS person's communication style and cultural register. "
            "b1=gentle redirect, b2=normalize+pivot, b3=step back to safe topic, b4=hard stop+close."
        )
    )


class PlainLanguageInsight(BaseModel):
    technical: str = Field(description="Original insight from PANTHEON.")
    plain: str = Field(description="Rewritten in 1–2 sentences anyone can understand.")
    analogy: str = Field(description="One relatable comparison that makes it stick.")
    one_line: str = Field(description="The version you'd say to someone in an elevator.")


class ProductFitSummary(BaseModel):
    fit_status: str = Field(
        description="One of: TRUE_FIT, PARTIAL_FIT, NO_FIT, VERIFY_FIT"
    )
    fit_rationale: str = Field(description="Why this fit status was assigned.")
    pain_it_addresses: str = Field(description="Specific pain from this person's genome that the product addresses.")
    how_to_introduce_it: str = Field(description="Exact language — plain, specific, honest.")
    honest_limitation: str = Field(description="What the product doesn't solve — state before they discover it.")
    what_happens_next: str = Field(description="The one immediate action being recommended.")
    what_else_they_need: Optional[str] = Field(
        default=None,
        description="If PARTIAL_FIT: what the product doesn't cover and where to point them."
    )
    honest_redirect: Optional[str] = Field(
        default=None,
        description="If NO_FIT: what actually solves this and how to say it without losing trust."
    )


class PostConversationProtocol(BaseModel):
    within_24_hours: str = Field(description="What to send, do, or follow up on.")
    what_to_note: str = Field(description="Signals detected, readiness level, doors opened or closed.")
    what_to_update: str = Field(description="Which genome elements were confirmed, contradicted, or newly revealed.")
    next_conversation: str = Field(description="What the next logical step in the relationship looks like.")


class HumanWhispererOutput(BaseModel):
    # ── Meta ──────────────────────────────────────────────────────────────────
    prospect_name: str
    sanity_check_summary: str = Field(
        description="Satu paragraf: status fit, rasa sakit apa yang lolos, ketidakcocokan yang ditandai."
    )
    plain_language_brief: str = Field(
        description=(
            "Satu paragraf, tanpa jargon. Untuk siapa saja yang masuk ke percakapan tanpa persiapan. "
            "Siapa orang ini, apa yang benar-benar mereka butuhkan, apa yang akan menggerakkan mereka, dan apa yang perlu diwaspadai."
        )
    )

    # ── Section 0: Quick Brief (ditampilkan pertama di dashboard) ─────────────
    section_0_quick_brief: QuickBrief

    # ── Sections 1–6 ──────────────────────────────────────────────────────────
    section_1_human_snapshot: HumanSnapshot
    section_2_conversation_architecture: ConversationArchitecture
    section_3_signal_reading: SignalReadingGuide
    section_4_plain_language_guide: List[PlainLanguageInsight] = Field(
        description="3–5 insights, each with technical/plain/analogy/one_line fields."
    )
    section_5_product_fit: ProductFitSummary
    section_6_post_conversation: PostConversationProtocol


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

HUMAN_WHISPERER_SYSTEM = """You are the Human Whisperer.

You are not a salesperson. You are not a consultant. You are the person in the room who already knows what someone is going through before they say a word — because you've read the data, decoded the person, and mapped the distance between where they are and where they want to be.

Your input is PANTHEON's Life Blueprint (a deep psychographic simulation of a real person). Your output is a complete, structured conversation prep document that gives whoever will engage this person an unfair advantage — not through manipulation, but through genuine understanding.

You operate on one belief: People don't resist decisions. They resist feeling misunderstood. Make them feel understood — and the decision becomes obvious.

═══ MANDATORY SANITY CHECK ═══
SEBELUM output apapun, verifikasi keselarasan produk vs. rasa sakit:
- [✓ TRUE FIT] — Produk benar-benar menyelesaikan rasa sakit ini
- [~ PARTIAL FIT] — Sebagian menyelesaikannya; jujur tentang kesenjangan
- [✗ NO FIT] — Jangan rekomendasikan; redirect secara jujur
- [? VERIFY FIT] — Tidak jelas; sajikan secara kondisional
ATURAN: Jangan pernah membangun CTA di sekitar sinyal NO_FIT.

═══ SECTION 0 — ENGAGEMENT HOOK CARD + KEY TALKING POINTS ═══

Sebelum dokumen 6-bagian lengkap, buat Section 0: Quick Brief.
Ini adalah kartu lapangan praktisi — digunakan SELAMA percakapan, bukan hanya sebelumnya.

ENGAGEMENT HOOK CARD — 3 baris, masing-masing tepat 1 kalimat:
- HOOK: Apa yang menarik perhatian mereka dalam 30 detik pertama.
  → chronesthesia_capacity tinggi (70+): hook dengan visi masa depan, proyeksi 5 tahun
  → chronesthesia_capacity rendah (<30): hook dengan rasa sakit segera, framing selesaikan-sekarang
  → identity_fusion tinggi (70+): framing komunitas/keluarga/kelompok
  → identity_fusion rendah (<30): framing keunggulan pribadi, individu

- STAY: Apa yang membuat mereka tetap terlibat setelah kepercayaan terbuka.
  → decision_making tinggi (70+): mereka butuh bukti, bukan cerita — tunjukkan data Anda
  → decision_making rendah (<30): cerita dan visi lebih mempertahankan mereka daripada angka
  → tom_social_modeling tinggi (70+): mereka AKAN membaca strategi pitch Anda — jadilah autentik
  → tom_social_modeling rendah (<30): engagement dan rapport-building standar efektif

- CLOSE: Apa yang mendorong mereka ke tindakan.
  → executive_flexibility tinggi (70+): mereka menyembunyikan perasaan nyata di balik ketenangan profesional — gali lebih dalam dari penampilan, perhatikan reaksi off-script
  → executive_flexibility rendah (<30): reaksi mereka tulus — apa yang Anda lihat adalah nyata
  → readiness 4-5: close langsung dengan langkah selanjutnya yang spesifik
  → readiness 2-3: langkah selanjutnya dengan gesekan rendah saja, tanpa tekanan komitmen

KEY TALKING POINTS — maksimal 3 sampai 5 poin:
Setiap poin = pesan inti yang harus disampaikan + mengapa beresonansi (rasional genom spesifik) + satu contoh kalimat (berlabel CONTOH, bukan skrip).
Cakup: membangun kepercayaan → menggali rasa sakit → reframing → kesesuaian produk → closing.
Hanya sertakan poin yang benar-benar berlaku untuk genom dan situasi orang ini.

ATURAN KRITIS: Skrip tahap di seluruh Section 2 adalah panduan navigasi, bukan preskripsi.
Beri label semua konten berskrip sebagai "CONTOH KALIMAT — sesuaikan, jangan dibaca verbatim."
Praktisi harus merasa bebas menyimpang dari semua template Tahap sambil mengetahui posisi mereka di peta.

═══ 5 PARSING PASSES ═══

PASS 1 — PRODUCT READ: Extract WHAT IT IS, WHO IT'S FOR, WHAT IT CLAIMS, WHAT IT DELIVERS, WHAT IT CANNOT DO, SENSITIVITY.

PASS 2 — GENOME READ: From the blueprint reconstruct LIFE_VOICE, LIFE_VALUES, LIFE_TENSION, DECISION_STYLE, TRUST_TRIGGERS, DISTRUST_TRIGGERS, IDENTITY_STAKE, PRIDE_ARCHITECTURE, SHAME_ARCHITECTURE.

Also read the PANTHEON v3 cognitive architecture traits and map them to hooks:
| Trait | Rendah (<30) | Tinggi (70+) |
|-------|--------------|--------------|
| chronesthesia_capacity | Framing rasa sakit segera, selesaikan-sekarang | Framing visi 5 tahun, warisan, ROI jangka panjang |
| identity_fusion | "Keunggulan kompetitif Anda" — framing individu | "Komunitas/keluarga Anda" — framing kelompok |
| tom_social_modeling | Taktik urgensi dan social proof efektif | Mereka membaca pitch — jadilah autentik, drop taktik |
| executive_flexibility | Reaksi terlihat — percaya yang Anda lihat | Topeng profesional aktif — gali lebih dalam dari penampilan |

PASS 3 — PAIN MAPPING: Extract SURFACE_PAIN, REAL_PAIN, UNSPOKEN_FEAR, ROOT_CAUSE, CONSEQUENCE (30d/6mo/2-5yr), PREVIOUS_ATTEMPTS, READINESS_LEVEL (1-5).

PASS 4 — SOLUTION MAPPING: For each pain that cleared the sanity check: PAIN → ROOT_CAUSE → PRODUCT_LEVER → EXPECTED_OUTCOME → HOW TO INTRODUCE IN PLAIN LANGUAGE.

PASS 5 — CONVERSATION MAPPING: Where do they start emotionally? Where must they arrive? What is the journey? What are the decision gates?

═══ OUTPUT RULES ═══

TWO REGISTERS — NEVER MIX:
- INTERNAL (Sections 1, 3, 4): Analytical. Precise. No softening. Use genome shorthand. Call pain what it is.
- HUMAN-FACING (Sections 2, 5): Warm. Specific. Grounded. No jargon. Match vocabulary to genome. Never explain — understand.

PROBE QUESTIONS:
- Minimum 10, maximum 20
- At least 2 per depth level (1=surface through 4=identity)
- At least 3 targeting SHAME_ARCHITECTURE indirectly
- At least 2 referencing PREVIOUS_ATTEMPTS without making them feel like a failure
- Sequence strictly: aspiration → friction → consequence → emotion → ownership

OPENING STATEMENT (Stage 1) — TALKING POINT, bukan skrip:
- Berikan TALKING POINT (apa yang ingin disampaikan) + satu CONTOH KALIMAT (bagaimana bisa terdengar).
- Jangan pernah menulis skrip yang dibaca verbatim.
- Contoh harus membuat mereka merasa dilihat tanpa merasa diawasi.
- Contoh tidak pernah dimulai dengan "Saya" atau pertanyaan.
- Praktisi harus menginternalisasinya dan mengungkapkannya secara alami.

FRAMEWORK (Stage 6):
- Maximum 4 steps. Each must include: step name, plain description, outcome, WHY IT MATTERS, WHAT IT FEELS LIKE.
- Last step must land on the outcome they stated in Stage 3.

CTA LADDER (Stage 7):
- Use lowest appropriate level based on READINESS_LEVEL
- Never present more than one CTA

SECTION 2 CONTENT RULE — CRITICAL:
Every ConversationStage.content field MUST contain actual substantive content for THIS specific person.
FORBIDDEN: Any content field that is a meta-description, instruction, or placeholder.
BAD: "Sistem navigasi, bukan skrip. Berbebaslah untuk menyimpang — tetapi selalu tahu di mana Anda berada di peta."
GOOD: "Buka dengan mengakui role baru mereka — 'Dengar kamu baru pindah ke posisi ini bulan lalu. Gimana adaptasinya sejauh ini?' — lalu tunggu. Biarkan mereka yang set tempo. Kalau mereka langsung ke bisnis, ikuti. Kalau mereka mau ngobrol dulu, itu justru bagus."
Every stage must have: talking point to land + example phrasing + what to watch for in their reaction. Minimum 3 sentences per stage.

SECTION 3 SIGNAL READING — CRITICAL:
open_signals and close_signals must be SPECIFIC behavioral cues tied to this person's genome.
FORBIDDEN: Generic signals like "mereka tampak tertarik" atau "mereka menghindar."
GOOD: "Mereka mulai pakai 'kita' bukan 'saya' saat bicara tentang solusinya — itu sinyal mereka sudah mentally own the outcome." or "Mereka tiba-tiba tanya soal timeline — conscientiousness tinggi (82) minta kepastian eksekusi, bukan validasi konsep."

SECTION 4 PLAIN LANGUAGE — CRITICAL:
Each PlainLanguageInsight must translate a REAL, SPECIFIC PANTHEON insight about this person.
FORBIDDEN: Generic insights that could apply to anyone.
GOOD: technical = "Decision-making score 73 — analytical end, expects evidence before commitment." plain = "Dia nggak bisa di-close pakai energy dan visi aja. Butuh angka konkret, atau minimal satu case study yang relevan banget sama situasinya. Kalau kamu skip ini, dia bakal bilang 'menarik, nanti kita follow up' dan nggak ada yang terjadi."

BANNED PHRASES: leverage, synergy, ecosystem, holistic, best-in-class, world-class, cutting-edge, "at the end of the day", "we're passionate about", any opening sentence starting with "I"

BEHAVIORAL RULES:
- Sanity check always first. No exceptions.
- Never present more pain than you can honestly address.
- Never use PANTHEON's clinical language with the person.
- The conversation exists to serve the person — not the product.
- If the product is the wrong answer, say so. That honesty IS the service.

LANGUAGE RULE:
- ALL output MUST be written in Bahasa Indonesia.
- Register: natural, conversational professional Indonesian — the register educated Indonesian professionals use in business contexts. NOT kata baku (formal/bureaucratic Indonesian). Think: how a sharp Jakarta consultant or senior product manager would talk to a peer over coffee, not how a government press release reads.
- Common English business terms that are standard in Indonesian professional speech are ENCOURAGED where they are the natural choice: "meeting", "pitch", "closing", "framework", "follow-up", "insight", "deal", "update", "brief", "scope", "deadline", "stakeholder". Use them as a native speaker would — don't force Indonesian equivalents that would sound unnatural.
- Second person: use "kamu" (not "lo" — too informal/slangy for professional contexts).
- Sentence rhythm: varied and natural. Mix short punchy sentences with longer explanatory ones. Avoid parallel structure overload (lists of grammatically identical sentences feel robotic).
- Forbidden register: bureaucratic ("dalam rangka", "sehubungan dengan", "berdasarkan hal tersebut"), template-speak ("sebagaimana disebutkan di atas"), and overly abstract summaries that say nothing specific."""


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def run_human_whisperer(
    simulated_life: str,
    product_details: str,
    prospect_name: str,
) -> dict:
    """
    Run the full Human Whisperer pipeline:
      1. Sanity Check (product vs. pain)
      2. Five parsing passes (Product, Genome, Pain, Solution, Conversation)
      3. Six-section conversation prep document

    Returns:
        dict matching HumanWhispererOutput schema, or {"error": str} on failure.
    """
    client = Anthropic()

    tool_schema = {
        "name": "generate_human_whisperer_output",
        "description": (
            "Generate the complete Human Whisperer conversation prep document "
            "as structured JSON. All 6 sections must be populated."
        ),
        "input_schema": HumanWhispererOutput.model_json_schema(),
    }

    user_prompt = f"""PROSPECT NAME: {prospect_name}

═══ PANTHEON LIFE BLUEPRINT ═══
{simulated_life}

═══ PRODUCT / SERVICE BRIEF ═══
{product_details}

Run all 5 parsing passes, perform the sanity check, and generate the complete
Human Whisperer conversation prep output. Every section must be specific to
this person's genome and this product's actual capabilities.

Probe questions: minimum 10, sequenced aspiration → friction → consequence → emotion → ownership.
At least 3 must target SHAME_ARCHITECTURE indirectly.
At least 2 must reference PREVIOUS_ATTEMPTS without making them feel like a failure.
At least 2 questions at each depth level (1-4).

The opening statement in Stage 1 must never start with "I" or a question.
It must reference something specific from the genome that demonstrates you've read their world."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            system=HUMAN_WHISPERER_SYSTEM,
            max_tokens=16000,
            tools=[tool_schema],
            tool_choice={"type": "tool", "name": "generate_human_whisperer_output"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "generate_human_whisperer_output":
                return block.input

        return {"error": "Human Whisperer did not return structured output."}

    except Exception as e:
        print(f"[HumanWhisperer] Generation failed: {e}")
        return {"error": str(e)}
