"""
Module: signal_extractor.py
Zone: 1 (Pre-session — called by genome_resolver scrape path)
Input: linkedin_data dict, instagram_data dict
Output: extracted_signals dict (feature counts for genome_builder)
LLM calls: 0 (keyword-based rule extraction)
Side effects: None
Latency tolerance: <500ms

Extracts behavioral signal counts from raw scraped post data.
Bilingual: English + Indonesian (Bahasa Indonesia) keyword sets.
"""

from __future__ import annotations

import re
from typing import Any

# ================================================================== #
#  KEYWORD SETS — bilingual EN + ID                                   #
# ================================================================== #

EXPERIMENTAL_KW = {
    "experiment", "try", "explore", "discover", "innovate", "creative", "novel", "prototype",
    "eksperimen", "coba", "eksplorasi", "temukan", "inovasi", "kreatif", "baru", "prototipe",
}
CONSERVATIVE_KW = {
    "proven", "traditional", "established", "safe", "reliable", "standard", "conventional",
    "terbukti", "tradisional", "mapan", "aman", "andal", "standar", "konvensional",
}
PLANNING_KW = {
    "plan", "strategy", "roadmap", "timeline", "milestone", "goal", "objective", "systematic",
    "rencana", "strategi", "peta jalan", "jadwal", "tonggak", "tujuan", "objektif", "sistematis",
}
ACHIEVEMENT_KW = {
    "achieved", "accomplished", "completed", "delivered", "launched", "promoted", "awarded",
    "dicapai", "selesai", "berhasil", "diluncurkan", "dipromosikan", "dihargai",
}
COLLABORATIVE_KW = {
    "team", "together", "collaborate", "partner", "community", "collective", "we", "our",
    "tim", "bersama", "kolaborasi", "mitra", "komunitas", "kolektif", "kami", "kita",
}
CONFRONTATIONAL_KW = {
    "challenge", "disagree", "push back", "debate", "confront", "oppose", "fight",
    "tantang", "tidak setuju", "debat", "konfrontasi", "lawan", "tolak",
}
DIRECT_KW = {
    "clearly", "directly", "specifically", "explicitly", "straightforward", "blunt",
    "jelas", "langsung", "spesifik", "eksplisit", "lugas",
}
INDIRECT_KW = {
    "perhaps", "might", "possibly", "consider", "maybe", "suggest",
    "mungkin", "barangkali", "pertimbangkan", "saran", "kira-kira",
}
DATA_KW = {
    "data", "metrics", "numbers", "statistics", "analysis", "research", "evidence", "roi",
    "data", "metrik", "angka", "statistik", "analisis", "riset", "bukti",
}
NARRATIVE_KW = {
    "story", "vision", "believe", "feel", "sense", "journey", "mission",
    "cerita", "visi", "percaya", "rasa", "perjalanan", "misi",
}
SOCIAL_PROOF_KW = {
    "everyone", "industry leaders", "top companies", "clients say", "testimonial",
    "semua orang", "pemimpin industri", "perusahaan terkemuka", "klien bilang",
}
EMOTIONAL_KW = {
    "excited", "passionate", "love", "thrilled", "proud", "grateful", "happy",
    "senang", "semangat", "cinta", "bangga", "bersyukur", "bahagia",
}
STOIC_KW = {
    "focused", "disciplined", "committed", "dedicated", "consistent", "steady",
    "fokus", "disiplin", "berkomitmen", "berdedikasi", "konsisten", "stabil",
}
AVOIDANCE_KW = {
    "avoid", "prefer not", "rather not", "stay away", "not comfortable", "skip",
    "hindari", "lebih suka tidak", "tidak nyaman", "lewati",
}
VOCABULARY_COMPLEX_KW = {
    "paradigm", "synergy", "leverage", "holistic", "ecosystem", "methodology", "framework",
    "paradigma", "sinergi", "memanfaatkan", "holistik", "ekosistem", "metodologi", "kerangka",
}
FRICTION_KW = {
    "difficult", "struggle", "challenging", "setback", "obstacle", "crisis", "pressure",
    "sulit", "perjuangan", "tantangan", "kemunduran", "hambatan", "krisis", "tekanan",
}
SUCCESS_KW = {
    "success", "win", "growth", "revenue", "profit", "expansion", "milestone",
    "sukses", "menang", "pertumbuhan", "pendapatan", "laba", "ekspansi", "tonggak",
}
GROUP_IDENTITY_KW = {
    "our community", "our people", "stand with", "represent", "culture", "heritage",
    "komunitas kami", "bangsa", "berdiri bersama", "mewakili", "budaya", "warisan",
}
INDIVIDUALIST_KW = {
    "my journey", "personally", "independent", "self-made", "own path", "individual",
    "perjalanan saya", "pribadi", "mandiri", "jalur sendiri", "individu",
}
FUTURE_VISION_KW = {
    "future", "vision", "2025", "2026", "five years", "transform", "next decade",
    "masa depan", "visi", "lima tahun", "transformasi", "dekade berikutnya",
}
LONG_TERM_KW = {
    "long-term", "sustainable", "legacy", "build for", "invest in",
    "jangka panjang", "berkelanjutan", "warisan", "membangun", "investasi",
}
SELF_REFLECTION_KW = {
    "learned", "realized", "looking back", "lesson", "insight", "growth mindset",
    "belajar", "menyadari", "melihat ke belakang", "pelajaran", "wawasan",
}
PERSPECTIVE_KW = {
    "from their perspective", "they feel", "understand them", "empathy", "put yourself",
    "dari sudut pandang mereka", "mereka merasa", "memahami mereka", "empati",
}
PROFESSIONAL_PERSONA_KW = {
    "professional", "executive", "leader", "position", "title", "corporate",
    "profesional", "eksekutif", "pemimpin", "jabatan", "gelar", "korporat",
}
AUTHENTIC_VULNERABILITY_KW = {
    "honest", "vulnerable", "admit", "struggle with", "not perfect", "raw",
    "jujur", "rentan", "mengakui", "berjuang dengan", "tidak sempurna",
}


class SignalExtractor:
    """
    Extracts behavioral signal feature counts from raw scraped post data.
    Returns a dict of feature_name → count used by GenomeBuilder._derive_scores().
    """

    def extract(
        self,
        linkedin_data: dict[str, Any],
        instagram_data: dict[str, Any],
    ) -> dict[str, Any]:
        all_text = self._collect_text(linkedin_data, instagram_data)
        posts_per_month = self._estimate_posts_per_month(linkedin_data, instagram_data)
        engagement = instagram_data.get("avg_engagement_rate", 0.0)

        return {
            "experimental_language_count": self._count_kw(all_text, EXPERIMENTAL_KW),
            "conservative_language_count": self._count_kw(all_text, CONSERVATIVE_KW),
            "planning_language_count": self._count_kw(all_text, PLANNING_KW),
            "achievement_posts_count": self._count_kw(all_text, ACHIEVEMENT_KW),
            "public_posts_per_month": posts_per_month,
            "engagement_rate": engagement,
            "collaborative_language_count": self._count_kw(all_text, COLLABORATIVE_KW),
            "confrontational_language_count": self._count_kw(all_text, CONFRONTATIONAL_KW),
            "direct_language_count": self._count_kw(all_text, DIRECT_KW),
            "indirect_language_count": self._count_kw(all_text, INDIRECT_KW),
            "data_references_count": self._count_kw(all_text, DATA_KW),
            "narrative_language_count": self._count_kw(all_text, NARRATIVE_KW),
            "brand_mentions_count": linkedin_data.get("brand_mentions", 0),
            "price_focus_count": self._count_kw(all_text, {"price", "cost", "cheap", "budget", "harga", "murah"}),
            "social_proof_references": self._count_kw(all_text, SOCIAL_PROOF_KW),
            "peer_validation_posts": linkedin_data.get("endorsements_count", 0),
            "emotional_posts_count": self._count_kw(all_text, EMOTIONAL_KW),
            "stoic_language_count": self._count_kw(all_text, STOIC_KW),
            "avoidance_language_count": self._count_kw(all_text, AVOIDANCE_KW),
            "vocabulary_complexity_score": self._count_kw(all_text, VOCABULARY_COMPLEX_KW),
            "formal_writing_count": linkedin_data.get("formal_posts_count", 0),
            "friction_signals_count": self._count_kw(all_text, FRICTION_KW),
            "success_signals_count": self._count_kw(all_text, SUCCESS_KW),
            "group_identity_language_count": self._count_kw(all_text, GROUP_IDENTITY_KW),
            "individualist_language_count": self._count_kw(all_text, INDIVIDUALIST_KW),
            "future_vision_posts": self._count_kw(all_text, FUTURE_VISION_KW),
            "long_term_planning_language": self._count_kw(all_text, LONG_TERM_KW),
            "self_reflection_posts": self._count_kw(all_text, SELF_REFLECTION_KW),
            "meta_commentary_count": self._count_kw(all_text, PERSPECTIVE_KW),
            "other_perspective_language": self._count_kw(all_text, PERSPECTIVE_KW),
            "audience_awareness_signals": linkedin_data.get("audience_targeting_signals", 0),
            "professional_persona_signals": self._count_kw(all_text, PROFESSIONAL_PERSONA_KW),
            "authentic_vulnerability_posts": self._count_kw(all_text, AUTHENTIC_VULNERABILITY_KW),
            "anxiety_language_count": self._count_kw(all_text, {"worried", "anxious", "uncertain", "fear", "khawatir", "cemas", "takut"}),
            "stability_language_count": self._count_kw(all_text, STOIC_KW),
        }

    def _collect_text(self, li: dict, ig: dict) -> str:
        texts = []
        for post in li.get("recent_posts", []):
            texts.append(post.get("text", ""))
        for post in ig.get("recent_posts", []):
            texts.append(post.get("caption", ""))
        bio = li.get("bio", "") + " " + ig.get("bio", "")
        texts.append(bio)
        return " ".join(texts).lower()

    def _count_kw(self, text: str, keywords: set[str]) -> int:
        count = 0
        for kw in keywords:
            count += len(re.findall(r"\b" + re.escape(kw) + r"\b", text))
        return min(count, 20)  # Cap at 20 to prevent extreme scores

    def _estimate_posts_per_month(self, li: dict, ig: dict) -> float:
        li_count = len(li.get("recent_posts", []))
        ig_count = len(ig.get("recent_posts", []))
        total = li_count + ig_count
        # Assume recent_posts covers ~30 days
        return round(total / 1.0, 1)
