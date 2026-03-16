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
    system_prompt = "You are a semantic routing agent..."
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
