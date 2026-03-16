"""
run_seed.py  --  Standalone agent seeder (no Modal required)
Calls dynamic_seed_agents() from main.py directly.

Usage:
  D:\\Pantheon\\venv\\Scripts\\python.exe run_seed.py
"""
import io
import os
import sys

# Force UTF-8 stdout so box-drawing chars in main.py prints don't crash
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure the root directory is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client
import anthropic

# -- Configuration -------------------------------------------------------------
DEMOGRAPHIC = "Vietnamese Metropolitan, 21-35"
COUNT       = 1
# ------------------------------------------------------------------------------

_VIETNAMESE_SEED_TEMPLATES = [
    "Vietnamese {age}yo startup founder in {city}, deeply embedded in the tech and cafe culture, "
    "hustle-driven mentality, fluent in English, extremely brand-conscious, and relies on Shopee/Grab daily.",

    "Vietnamese {age}yo corporate employee (finance/marketing) living in {city}, values family approval but wants independence, "
    "saves money meticulously but spends on occasional premium experiences/travel, navigates modern vs traditional expectations.",

    "Vietnamese {age}yo freelancer/creative based in {city}, anti-9-to-5, active on TikTok/Facebook, "
    "trend-follower, values aesthetics and social validation, high disposable income spent on lifestyle.",

    "Vietnamese {age}yo small business owner (F&B or retail) in {city}, family-oriented, pragmatic, "
    "cash-reliant, navigates informal economy but uses Zalo heavily for networking and business.",

    "Vietnamese {age}yo manufacturing/logistics middle-manager in {city}, frugal, focuses on long-term stability and property investment, "
    "suspicious of flashy marketing, relies on close peer recommendations for big purchases."
]

load_dotenv(".env", override=True)
url     = os.environ["SUPABASE_URL"]
key     = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
api_key = os.environ["ANTHROPIC_API_KEY"]

sb     = create_client(url, key)
client = anthropic.Anthropic(api_key=api_key)

# Import the Genesis engine from src/genesis.py
from src.genesis import dynamic_seed_agents

print("\n" + "=" * 60)
print("  PANTHEON Genesis -- Standalone Seed Run")
print(f"  Demographic : {DEMOGRAPHIC}")
print(f"  Count       : {COUNT} agents")
print("=" * 60 + "\n")

created = dynamic_seed_agents(
    demographic=DEMOGRAPHIC,
    count=COUNT,
    sb=sb,
    anthropic_client=client,
    city_pool=["Ho Chi Minh City", "Hanoi", "Da Nang"],
    country="Vietnam",
    seed_templates=_VIETNAMESE_SEED_TEMPLATES
)

print("\n" + "=" * 60)
print(f"  Done -- {len(created)}/{COUNT} agents stored in Supabase.")
print("=" * 60 + "\n")
