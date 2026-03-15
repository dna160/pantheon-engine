import asyncio
import json
import os
from dotenv import load_dotenv
from client_whisperer.app import WhisperRequest, whisper_endpoint

# Load API Key
load_dotenv("pantheon.env")

async def main():
    print("Evaluating Client Whisperer flow...")
    
    req = WhisperRequest(
        linkedin_url="https://linkedin.com/in/mock-ceo",
        instagram_url="https://instagram.com/mock-ceo",
        product_details="""
        Client Whisperer SaaS: An enterprise AI assistant that analyzes B2B buyers across 
        Linkedin and Instagram, simulating their deep psychological profile and outputting 
        the definitive step-by-step strategy on how to close them.
        Pricing: $1,500/month.
        Value prop: Stop guessing what to say on sales calls. Know exactly what matters to them before you speak.
        """
    )
    
    try:
        # In a real environment, this requires ANTHROPIC_API_KEY environment variable.
        # This test ensures the Pydantic models and logic are wired up.
        result = await whisper_endpoint(req)
        print("\\n--- GENERATED STRATEGY ---")
        print(json.dumps(result, indent=2))
        print("--------------------------\\n")
    except Exception as e:
        print(f"Test failed with error: {e}")
        print("Note: Ensure ANTHROPIC_API_KEY is set in your environment variables for this test to succeed.")

if __name__ == "__main__":
    asyncio.run(main())
