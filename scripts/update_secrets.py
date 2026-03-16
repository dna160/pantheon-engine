"""Reads pantheon.env and updates the Modal pantheon-secrets secret, then exits."""
import subprocess
import sys
from dotenv import load_dotenv
import os

load_dotenv('pantheon.env', override=True)

supabase_url = os.getenv("SUPABASE_URL", "")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
apify_token = os.getenv("APIFY_API_TOKEN", "")

missing = []
if not supabase_url:       missing.append("SUPABASE_URL")
if not supabase_key:       missing.append("SUPABASE_SERVICE_ROLE_KEY")
if not anthropic_key:      missing.append("ANTHROPIC_API_KEY")
if not apify_token:        missing.append("APIFY_API_TOKEN")

if missing:
    print(f"[ERROR] Missing from pantheon.env: {', '.join(missing)}")
    sys.exit(1)

print("Updating Modal secret 'pantheon-secrets'...")
result = subprocess.run(
    [
        sys.executable, "-m", "modal", "secret", "create", "pantheon-secrets",
        f"SUPABASE_URL={supabase_url}",
        f"SUPABASE_SERVICE_ROLE_KEY={supabase_key}",
        f"ANTHROPIC_API_KEY={anthropic_key}",
        f"APIFY_API_TOKEN={apify_token}",
        "--force",   # overwrite existing secret
    ],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("[OK] Modal secret 'pantheon-secrets' updated successfully.")
    print("     Variables pushed: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ANTHROPIC_API_KEY, APIFY_API_TOKEN")
else:
    print("[ERROR] Failed to update Modal secret:")
    print(result.stderr)
    sys.exit(1)
