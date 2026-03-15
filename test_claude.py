from dotenv import load_dotenv
import os
import anthropic

load_dotenv('pantheon.env', override=True)

api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key:
    print("❌ ANTHROPIC_API_KEY not set in .env!")
    exit(1)

print(f"Testing key: {api_key[:20]}...")

client = anthropic.Anthropic(api_key=api_key)

try:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=32,
        messages=[{"role": "user", "content": "Say OK"}]
    )
    print(f"✅ Claude API working! Response: {response.content[0].text}")
except anthropic.AuthenticationError as e:
    print(f"❌ Auth error — wrong API key: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
