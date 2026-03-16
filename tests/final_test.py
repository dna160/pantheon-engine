import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv('pantheon.env', override=True)

anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
if not anthropic_key:
    print("❌ ANTHROPIC_API_KEY not set in pantheon.env")
    exit(1)

# NODE 1 mock:
agent_data = {
    "target_demographic": "Urban Millennial",
    "age": 30,
    "region": "North America",
    "neuroticism": 60,
    "conscientiousness": 75,
    "independence_layer": {
        "summary": "Moved to the city, started a tech job, relies heavily on fintech digital convenience apps.",
        "key_events": ["Got first apartment in city", "Subscribed to multiple fintech tools for budgeting", "Began splitting bills with roommates using applications"],
        "psychological_impact": "Values speed, convenience, and financial fluidity. Often feels slight background anxiety about rent, making installment tools highly appealing."
    }
}

# NODE 2: Claude Snapshot
history = agent_data.get("independence_layer", {})

SNAPSHOT_SCHEMA = """Respond with ONLY valid JSON, no markdown, no code fences. Schema:
{
  "current_emotional_state": "string — their exact emotional state right now",
  "current_mental_bandwidth": "string — Exhausted / Highly focused / Distracted etc.",
  "current_financial_pressure": "string — immediate financial context"
}"""

prompt = (
    f"Given this agent's life stage history:\n{json.dumps(history, indent=2)}\n\n"
    f"Neuroticism: {agent_data.get('neuroticism', 50)} | Conscientiousness: {agent_data.get('conscientiousness', 50)}\n\n"
    "Write a specific, highly contextual description of their exact mental and emotional state RIGHT NOW before a focus group."
)

data = {
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 512,
    "system": SNAPSHOT_SCHEMA,
    "messages": [{"role": "user", "content": prompt}]
}

req_claude = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(data).encode('utf-8'))
req_claude.add_header("x-api-key", anthropic_key)
req_claude.add_header("anthropic-version", "2023-06-01")
req_claude.add_header("content-type", "application/json")

resp_claude = urllib.request.urlopen(req_claude)
result = json.loads(resp_claude.read())

content = result["content"][0]["text"]
try:
    obj = json.loads(content)
    print("--- OUTPUT ---")
    print(json.dumps({
        "current_emotional_state": obj.get("current_emotional_state"),
        "current_financial_pressure": obj.get("current_financial_pressure")
    }, indent=2))
except Exception as e:
    print(content)
