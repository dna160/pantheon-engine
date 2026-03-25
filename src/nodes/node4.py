import os

NODE4_SYSTEM_BASE = (
    "You are a qualitative research director facilitating focus groups. "
    "Your job is to faithfully simulate a realistic, multi-turn debate between "
    "real consumers reacting to a campaign stimulus. Each participant must speak "
    "in their own voice — shaped by their age, culture, psychology, and initial reaction. "
    "Drive the conversation through disagreement, alignment, and emotional escalation. "
    "Produce a raw, unmoderated 15-turn debate transcript."
)

NODE4_VISION_ADDENDUM = (
    "\n\nThe participants have been shown the actual visual slides of the campaign. "
    "You are evaluating a campaign. You have been provided the raw text AND the actual "
    "visual slides of the campaign. React to the visual design, the model choices, and "
    "the layout, not just the copy. Debate dialogue should reference specific visual "
    "elements: the imagery used, the color palette, model/talent choices, layout and "
    "composition, and the emotional tone conveyed by the design — not only the words."
)


def _build_content(prompt: str, brief_images: list[str]) -> list[dict] | str:
    if not brief_images:
        return prompt
    content: list[dict] = [{"type": "text", "text": prompt}]
    for b64 in brief_images[:6]:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64,
            }
        })
    return content


def node4_breakout_room(group_reactions: list[dict], campaign_brief: str, brief_images: list[str] = []) -> dict:
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    parts = []
    for r in group_reactions:
        pa = r.get("phase_a") or {}
        parts.append(f"PARTICIPANT (Age {r.get('age')}, {r.get('demographic')}): {pa.get('gut_reaction')}")

    group_ctx = "\n\n".join(parts)
    agent_ages = [str(r.get("age")) for r in group_reactions]

    system = NODE4_SYSTEM_BASE + (NODE4_VISION_ADDENDUM if brief_images else "")

    prompt = (
        f"BRIEF: {campaign_brief}\n\n"
        + ("The participants have also been shown the campaign visuals (attached below). "
           "Weave visual references into the debate.\n\n" if brief_images else "")
        + f"PARTICIPANTS:\n{group_ctx}\n\nWrite 15-turn debate."
    )
    content = _build_content(prompt, brief_images)

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2500,
            system=system,
            messages=[{"role": "user", "content": content}]
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
        "error": error if "error" in locals() else None,
    }
