"""
Vision analysis module for Client/Human Whisperer.
Downloads Instagram images and sends them to Claude as base64 content blocks
for genuine pixel-level analysis. Returns rich, actionable insights for the
Human Whisperer's 5-pass pipeline.
"""
from __future__ import annotations

import base64
import mimetypes
from typing import List, Dict, Any

import requests
from anthropic import Anthropic
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Output schema — expanded for Human Whisperer fidelity
# ─────────────────────────────────────────────────────────────────────────────

class VisionInsights(BaseModel):
    # ── Core lifestyle signals ───────────────────────────────────────────────
    hobbies: List[str] = Field(
        description=(
            "Activities and interests visually confirmed across the images. "
            "Be specific — not 'travel' but 'beach travel, mountaineering'. "
            "Only include what is directly visible."
        )
    )
    relationship_status: str = Field(
        description=(
            "Inferred relationship status based on visual evidence. "
            "One of: 'In a relationship', 'Married', 'Single (no visible partner)', "
            "'Family-focused (children visible)', 'Unknown'. "
            "Cite the visual evidence that led to the inference."
        )
    )
    lifestyle_choices: List[str] = Field(
        description=(
            "Lifestyle descriptors inferred from image content. "
            "E.g. 'fitness-focused', 'luxury consumer', 'outdoors/nature-oriented', "
            "'urban professional', 'foodie', 'wellness-driven', 'creative/artistic'. "
            "Each entry must be justified by something visible."
        )
    )
    current_emotional_sentiment: str = Field(
        description=(
            "Overall emotional tone conveyed across recent posts. "
            "E.g. 'positive and energetic', 'stressed and achievement-focused', "
            "'relaxed and vacation mode', 'ambitious and on-the-move', 'celebratory'. "
            "Base on facial expression, body language, setting, and caption context if visible."
        )
    )

    # ── Deeper psychographic signals ─────────────────────────────────────────
    social_environment: str = Field(
        description=(
            "Who this person appears to spend time with, based on images. "
            "E.g. 'frequently photographed with a small tight-knit friend group', "
            "'mostly solo shots suggesting introversion or privacy-preference', "
            "'family-centric with children present', 'professional networking events visible'. "
            "Avoid assumptions not grounded in the images."
        )
    )
    brand_signals: List[str] = Field(
        description=(
            "Visible brand logos, luxury items, product placements, or status markers. "
            "E.g. 'Apple devices visible', 'luxury hotel branding in background', "
            "'athletic brands dominant (Nike, Lululemon)', 'no visible brand signals'. "
            "List only what can be clearly identified in the images."
        )
    )
    self_presentation_style: str = Field(
        description=(
            "How this person presents themselves visually. "
            "E.g. 'curated and polished — consistent aesthetic filter', "
            "'candid and unfiltered — authenticity-signalling', "
            "'aspirational/status-oriented — destinations, meals, experiences', "
            "'private — mostly landscapes, food, no selfies'. "
            "Reflect on the overall curation strategy."
        )
    )
    body_language_and_confidence: str = Field(
        description=(
            "Overall impression of confidence and physical presence from photos containing the person. "
            "E.g. 'open posture, direct camera engagement — high social confidence', "
            "'often photographed from behind or at a distance — privacy-oriented', "
            "'relaxed and unposed — comfortable being seen'. "
            "Only assess if person is visible in multiple images."
        )
    )
    apparent_life_stage: str = Field(
        description=(
            "Inferred life stage from visual cues. "
            "E.g. 'young professional building career', 'established executive with family', "
            "'empty-nester in exploration phase', 'entrepreneur hustling phase', "
            "'early-career with high social activity'. "
            "Cross-reference life cues: travel frequency, family presence, event types."
        )
    )

    # ── Human Whisperer–specific output ──────────────────────────────────────
    actionable_insights: List[str] = Field(
        description=(
            "Exactly 3–5 direct, specific insights that the Human Whisperer can use "
            "immediately in Stage 1 (Arrive) or Stage 3 (Probe) of the conversation. "
            "Each insight must:\n"
            "  1. Reference something SPECIFIC and VISIBLE in the images\n"
            "  2. State a clear implication for the sales/advisory conversation\n"
            "  3. Suggest how to use it without making the person feel surveilled\n"
            "Format each as: '[IMAGE SIGNAL] → [IMPLICATION] → [HOW TO USE IT]'\n"
            "Example: 'Multiple high-end restaurant photos → values quality experiences over price → "
            "lead with outcome quality, not cost savings in the opener'"
        )
    )
    privacy_flags: List[str] = Field(
        description=(
            "Any signals suggesting this person is particularly private, image-conscious, "
            "or likely to feel uncomfortable if approached with too much personal knowledge. "
            "E.g. 'Very few selfies — prefers to control personal visibility', "
            "'Posts are heavily curated — may be performance-oriented rather than authentic'. "
            "Empty list if no privacy sensitivity detected."
        )
    )
    image_count_analysed: int = Field(
        description="Number of images actually analysed in this call."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Image download helper
# ─────────────────────────────────────────────────────────────────────────────

_DOWNLOAD_TIMEOUT = 8  # seconds
_SUPPORTED_TYPES  = {"image/jpeg", "image/png", "image/webp", "image/gif"}

def _download_as_base64(url: str) -> tuple[str, str] | None:
    """
    Download an image from a URL and return (base64_data, media_type).
    Returns None if the download fails or the content type is unsupported.
    """
    try:
        resp = requests.get(url, timeout=_DOWNLOAD_TIMEOUT, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
        if not content_type:
            # Guess from URL extension
            guessed, _ = mimetypes.guess_type(url)
            content_type = guessed or "image/jpeg"

        # Normalise
        if "jpeg" in content_type or "jpg" in content_type:
            media_type = "image/jpeg"
        elif "png" in content_type:
            media_type = "image/png"
        elif "webp" in content_type:
            media_type = "image/webp"
        elif "gif" in content_type:
            media_type = "image/gif"
        else:
            print(f"  [Vision] Unsupported content type '{content_type}' for {url[:60]}... — skipping")
            return None

        raw = resp.content
        if len(raw) < 100:   # suspiciously small — likely a redirect or error page
            return None

        b64 = base64.standard_b64encode(raw).decode("utf-8")
        return b64, media_type

    except Exception as e:
        print(f"  [Vision] Download failed for {url[:60]}...: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def analyze_images(images: List[str]) -> Dict[str, Any]:
    """
    Downloads up to 8 Instagram image URLs, converts them to base64, and sends
    them to Claude as actual image content blocks for pixel-level vision analysis.

    Returns a dict matching VisionInsights schema, including:
    - hobbies, relationship_status, lifestyle_choices, emotional_sentiment
    - social_environment, brand_signals, self_presentation_style
    - body_language_and_confidence, apparent_life_stage
    - actionable_insights (3–5 Human Whisperer–ready conversation levers)
    - privacy_flags, image_count_analysed
    """
    _empty = {
        "hobbies": [],
        "relationship_status": "Unknown",
        "lifestyle_choices": [],
        "current_emotional_sentiment": "Neutral",
        "social_environment": "Unknown",
        "brand_signals": [],
        "self_presentation_style": "Unknown",
        "body_language_and_confidence": "Unknown",
        "apparent_life_stage": "Unknown",
        "actionable_insights": [],
        "privacy_flags": [],
        "image_count_analysed": 0,
    }

    if not images:
        return _empty

    # ── Step 1: Download images as base64 ─────────────────────────────────────
    print(f"  [Vision] Downloading up to 8 images for pixel-level analysis...")
    content_blocks = []
    downloaded_count = 0

    for url in images[:8]:
        result = _download_as_base64(url)
        if result:
            b64_data, media_type = result
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64_data,
                }
            })
            downloaded_count += 1
        else:
            # Fallback: try URL source if download failed
            content_blocks.append({
                "type": "image",
                "source": {"type": "url", "url": url}
            })

    if downloaded_count == 0 and not content_blocks:
        print("  [Vision] No images could be loaded. Returning empty insights.")
        return _empty

    print(f"  [Vision] {downloaded_count}/{min(len(images), 8)} images downloaded as base64. Sending to Claude...")

    # ── Step 2: Build prompt ──────────────────────────────────────────────────
    content_blocks.append({
        "type": "text",
        "text": (
            f"You are analysing {len(content_blocks) - 1} recent Instagram images from a single person's profile. "
            "Your job is to extract deep, actionable psychographic insights for a Human Whisperer "
            "conversation prep document.\n\n"
            "ANALYSIS RULES:\n"
            "1. Only state what is directly visible — no fabrication.\n"
            "2. Prioritise recency signals (assume left-to-right = oldest to newest).\n"
            "3. For actionable_insights: be specific and conversation-ready. "
            "Each must reference a real image signal and suggest exactly how to use it "
            "in a conversation opener or probe question WITHOUT making the person feel surveilled.\n"
            "4. For privacy_flags: err on the side of caution — flag anything that suggests "
            "this person guards their personal life carefully.\n"
            "5. If a person is rarely visible in the images, note that — it matters for trust calibration."
        )
    })

    # ── Step 3: Call Claude with tool_use ─────────────────────────────────────
    client = Anthropic()
    tool_schema = {
        "name": "extract_vision_insights",
        "description": (
            "Extract deep, actionable psychographic insights from Instagram images "
            "for use in Human Whisperer conversation prep."
        ),
        "input_schema": VisionInsights.model_json_schema(),
    }

    try:
        response = client.messages.create(
            model="claude-opus-4-5",   # Use Opus for best vision accuracy
            max_tokens=2000,
            tools=[tool_schema],
            tool_choice={"type": "tool", "name": "extract_vision_insights"},
            messages=[{"role": "user", "content": content_blocks}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "extract_vision_insights":
                result = block.input
                result["image_count_analysed"] = downloaded_count
                print(f"  [Vision] Analysis complete — {len(result.get('actionable_insights', []))} actionable insights extracted.")
                return result

        _empty["image_count_analysed"] = downloaded_count
        return _empty

    except Exception as e:
        print(f"  [Vision] Claude analysis failed: {e}")
        fallback = dict(_empty)
        fallback["error"] = str(e)
        fallback["image_count_analysed"] = downloaded_count
        return fallback
