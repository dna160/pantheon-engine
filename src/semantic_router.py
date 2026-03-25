import anthropic as _anthropic

_SEMANTIC_ROUTER_TOOL = {
    "name": "return_matching_demographics",
    "description": (
        "Return ONLY the demographic strings from the provided list that are "
        "practically synonymous with or a reasonable substitute for the requested PTM/STM."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "approved_matches": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["approved_matches"],
    },
}

def evaluate_demographics(ptm_requested: str, stm_requested: str, available_demos: list[str], anthropic_client) -> list[str]:
    if not available_demos: return []
    stm_line = f"STM: {stm_requested}" if stm_requested.strip() else "STM: (none)"
    available_str = "\n".join(f"  - {d}" for d in available_demos)
    system_prompt = (
        "You are a semantic routing agent. Your job is to match a requested target demographic "
        "against a list of available demographic strings stored in the database.\n\n"
        "STRICT AGE RULE (HIGHEST PRIORITY):\n"
        "If the requested PTM or STM contains an explicit age range (e.g. '12-25', 'aged 18-30', "
        "'teenagers', 'Gen Z'), you MUST only approve demographics whose age range meaningfully "
        "overlaps with the requested range. A demographic targeting 25-45 year-olds is NOT a match "
        "for a request targeting 12-25 year-olds — even if all other attributes match. Age range "
        "mismatches are disqualifying. When in doubt, return an empty list rather than approving "
        "an age-mismatched demographic.\n\n"
        "AGE KEYWORD MAPPING:\n"
        "- 'children', 'kids', 'pre-teen' → approx 8-12\n"
        "- 'teenagers', 'teens', 'adolescents' → approx 13-19\n"
        "- 'Gen Z', 'zoomers', 'young adults' → approx 18-27\n"
        "- 'millennials' → approx 28-43\n"
        "- 'Gen X' → approx 44-59\n\n"
        "Only return demographics that are BOTH culturally/contextually similar AND age-range compatible."
    )
    user_message = f"PTM: {ptm_requested}\n{stm_line}\nAvailable:\n{available_str}"
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=system_prompt,
            tools=[_SEMANTIC_ROUTER_TOOL],
            tool_choice={"type": "tool", "name": "return_matching_demographics"},
            messages=[{"role": "user", "content": user_message}],
        )
        block = next((b for b in response.content if b.type == "tool_use"), None)
        return [d for d in block.input.get("approved_matches", []) if d in available_demos] if block else []
    except Exception:
        return []
