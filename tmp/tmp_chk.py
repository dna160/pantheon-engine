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

req = urllib.request.Request(f"{supabase_url}/rest/v1/agent_genomes?select=target_demographic")
req.add_header("apikey", supabase_key)
req.add_header("Authorization", f"Bearer {supabase_key}")
resp = urllib.request.urlopen(req)
agents = json.loads(resp.read())

demographics = {a.get('target_demographic') for a in agents}
print("Available demographics:", demographics)
