import os
import json
import urllib.request

with open('.env') as f:
    env = {}
    for line in f:
         line=line.strip()
         if line and not line.startswith('#'):
             k,v = line.split('=', 1)
             env[k] = v

supabase_url = env['SUPABASE_URL']
supabase_key = env['SUPABASE_SERVICE_ROLE_KEY']

payload = {
    "target_demographic": "Urban Millennial",
    "age": 30,
    "region": "North America",
    "openness": 80,
    "conscientiousness": 60,
    "extraversion": 70,
    "agreeableness": 65,
    "neuroticism": 40,
    "independence_layer": {
        "summary": "Moved to the city, started a tech job, relies heavily on fintech digital convenience apps.",
        "key_events": ["Got first apartment in city", "Subscribed to multiple fintech tools for budgeting", "Began splitting bills with roommates using applications"],
        "psychological_impact": "Values speed, convenience, and financial fluidity. Often feels slight background anxiety about rent, making installment tools highly appealing."
    }
}

req = urllib.request.Request(f"{supabase_url}/rest/v1/agent_genomes")
req.add_header("apikey", supabase_key)
req.add_header("Authorization", f"Bearer {supabase_key}")
req.add_header("Content-Type", "application/json")
req.add_header("Prefer", "return=representation")
data = json.dumps([payload]).encode('utf-8')

resp = urllib.request.urlopen(req, data=data)
print("Inserted.")
