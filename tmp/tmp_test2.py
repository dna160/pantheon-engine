import json
import urllib.request
import os

with open('.env') as f:
    env = {}
    for line in f:
         line=line.strip()
         if line and not line.startswith('#'):
             k,v = line.split('=', 1)
             env[k] = v

supabase_url = env['SUPABASE_URL']
supabase_key = env['SUPABASE_SERVICE_ROLE_KEY']
anthropic_key = env['ANTHROPIC_API_KEY']

# NODE 1: query supabase
req = urllib.request.Request(f"{supabase_url}/rest/v1/agent_genomes?target_demographic=eq.Urban%20Millennial&limit=1")
req.add_header("apikey", supabase_key)
req.add_header("Authorization", f"Bearer {supabase_key}")
resp = urllib.request.urlopen(req)
agents = json.loads(resp.read())

if not agents:
    print("No agents found")
    exit(1)

agent_data = agents[0]

# NODE 2: Claude Snapshot
age = agent_data.get("age", 30)
if age < 18:
    history = agent_data.get("formation_layer", {})
elif age < 35:
    history = agent_data.get("independence_layer", {})
else:
    history = agent_data.get("maturity_layer", {})

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
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 512,
    "system": SNAPSHOT_SCHEMA,
    "messages": [{"role": "user", "content": prompt}]
}

req_claude = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(data).encode('utf-8'))
req_claude.add_header("x-api-key", anthropic_key)
req_claude.add_header("anthropic-version", "2023-06-01")
req_claude.add_header("content-type", "application/json")

try:
    resp_claude = urllib.request.urlopen(req_claude)
    result = json.loads(resp_claude.read())
    content = result["content"][0]["text"]
    obj = json.loads(content)
    print("\n--- OUTPUT ---\n")
    print(json.dumps({
        "current_emotional_state": obj.get("current_emotional_state"),
        "current_financial_pressure": obj.get("current_financial_pressure")
    }, indent=2))
except Exception as e:
    print(e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
