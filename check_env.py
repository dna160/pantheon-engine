from dotenv import load_dotenv
import os

load_dotenv('pantheon.env', override=True)

url = os.getenv("SUPABASE_URL", "NOT SET")
key_preview = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "NOT SET")
anthropic_preview = os.getenv("ANTHROPIC_API_KEY", "NOT SET")

# Only show first/last chars for security
def preview(s):
    if len(s) > 10:
        return s[:12] + "..." + s[-6:]
    return s

print(f"SUPABASE_URL         : {url}")
print(f"SUPABASE_SERVICE_KEY : {preview(key_preview)}")
print(f"ANTHROPIC_API_KEY    : {preview(anthropic_preview)}")
