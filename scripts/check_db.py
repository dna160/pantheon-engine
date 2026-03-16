from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv('pantheon.env', override=True)
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
r = sb.table("agent_genomes").select("id", count="exact").execute()
print(f"Agents in DB: {r.count}")
