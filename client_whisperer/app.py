import modal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from client_whisperer.scrapers import scrape_linkedin_parallel, scrape_instagram
from client_whisperer.vision import analyze_images
from client_whisperer.engine import run_pantheon_simulation
from client_whisperer.strategy import generate_strategy

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi[standard]",
        "pydantic>=2.4.0",
        "requests",
        "anthropic>=0.50.0",
        "apify-client",
        "python-dotenv",
    )
)

app = modal.App("client-whisperer")
web_app = FastAPI(title="Client Whisperer API")


class WhisperRequest(BaseModel):
    linkedin_url: str
    instagram_url: str
    product_details: str


@web_app.post("/whisper")
async def whisper_endpoint(req: WhisperRequest):
    try:
        # Step 1: LinkedIn profile + posts scrapers fire in parallel (single URL)
        linkedin_data, posts_data = scrape_linkedin_parallel(req.linkedin_url)

        # Step 2: Scrape Instagram
        instagram_data = scrape_instagram(req.instagram_url)

        # Step 3: Vision analysis on recent Instagram images
        vision_insights = analyze_images(instagram_data.get("recent_images", []))

        # Step 4: Simulate the full life blueprint via Pantheon engine
        engine_result = run_pantheon_simulation(
            linkedin_data=linkedin_data,
            posts_data=posts_data,
            insta_data=instagram_data,
            vision_insights=vision_insights
        )
        simulated_life = engine_result["simulated_life"]

        # Step 5: Cross-reference with product and generate sales strategy
        strategy_output = generate_strategy(
            simulated_life=simulated_life,
            product_details=req.product_details
        )

        return strategy_output

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("pantheon-secrets")],
)
@modal.asgi_app()
def fastapi_app():
    return web_app
