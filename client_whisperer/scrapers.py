import math
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from apify_client import ApifyClient


# ─────────────────────────────────────────────────────────────────────────────
# RECENCY WEIGHTING
# Exponential decay with a 90-day half-life.
#   weight ≈ 1.0  → posted in the last week  (HOT)
#   weight ≈ 0.5  → posted ~90 days ago      (WARM)
#   weight ≈ 0.1  → posted ~300 days ago     (COLD)
# ─────────────────────────────────────────────────────────────────────────────

def _apply_recency_weight(post: dict, now: datetime) -> dict:
    date_str = (
        post.get("publishedAt") or
        post.get("date") or
        post.get("postedAt") or
        post.get("createdAt") or
        ""
    )
    if not date_str:
        post["recency_weight"] = 0.3
        post["days_ago"] = None
        return post
    try:
        pub = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        days = (now - pub).days
        # ln(2) / 90  →  half-life of 90 days
        weight = math.exp(-0.007697 * max(days, 0))
        post["recency_weight"] = round(max(0.05, min(1.0, weight)), 3)
        post["days_ago"] = days
    except (ValueError, TypeError):
        post["recency_weight"] = 0.3
        post["days_ago"] = None
    return post


def _recency_tier(weight: float) -> str:
    if weight >= 0.70:
        return "HOT"
    if weight >= 0.35:
        return "WARM"
    return "COLD"


# ─────────────────────────────────────────────────────────────────────────────
# MOCK DATA
# ─────────────────────────────────────────────────────────────────────────────

def _mock_profile(url: str) -> Dict[str, Any]:
    return {
        "source": "LinkedIn",
        "url": url,
        "name": "John Mock",
        "headline": "Senior Engineer at Tech Corp (MOCK)",
        "location": "San Francisco, CA (MOCK)",
        "summary": "Passionate technologist with 10+ years experience. (MOCK)",
        "connections": 500,
        "follower_count": 520,
        "top_skills": "Product Management • Data Analysis • Marketing (MOCK)",
        "open_to_work": False,
        "education": [
            {
                "school": "University of Technology", "degree": "B.Sc.", "field": "Computer Science",
                "years": "2010 - 2014", "description": "GPA: 3.8/4.0 (MOCK)"
            }
        ],
        "career_trajectory": [
            {"company": "Tech Corp", "title": "Senior Engineer", "duration": "2018 - Present",
             "employment_type": "Full-time", "description": "Led platform architecture. (MOCK)"},
            {"company": "Startup Inc", "title": "Software Engineer", "duration": "2014 - 2018",
             "employment_type": "Full-time", "description": "Built core product features. (MOCK)"}
        ],
        "skills": ["Product Management", "Data Analysis", "Python", "Marketing"],
        "certifications": ["Product Manager — RevoU (Issued Sep 2022) (MOCK)"],
        "languages": ["English (Professional working proficiency) (MOCK)"],
    }


def _mock_posts(url: str) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    raw_posts = [
        {
            "text": "Just wrapped a fantastic panel on AI-driven personalisation at SaaStr. The future of B2B is here — and it's personal. (MOCK)",
            "publishedAt": "2026-02-20T09:00:00+00:00",
            "likes": 184, "comments": 23, "shares": 9,
            "post_url": url, "post_type": "post",
        },
        {
            "text": "Q4 closed at 138% of quota. Grateful for every person on this team. We did it together. (MOCK)",
            "publishedAt": "2025-12-05T14:00:00+00:00",
            "likes": 97, "comments": 14, "shares": 3,
            "post_url": url, "post_type": "post",
        },
        {
            "text": "Sharing this piece on B2B buying committees — it mirrors exactly what we see in the field every quarter. (MOCK)",
            "publishedAt": "2025-09-12T10:00:00+00:00",
            "likes": 52, "comments": 7, "shares": 14,
            "post_url": url, "post_type": "reshare",
        },
    ]
    posts = [_apply_recency_weight(p, now) for p in raw_posts]
    posts.sort(key=lambda p: p["recency_weight"], reverse=True)
    return {
        "source": "LinkedIn_Posts",
        "url": url,
        "total_fetched": len(posts),
        "posts": posts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPERS
# ─────────────────────────────────────────────────────────────────────────────

def scrape_linkedin(url: str) -> Dict[str, Any]:
    """
    harvestapi/linkedin-profile-scraper — profile metadata, career, education.
    Falls back to mock data if APIFY_API_TOKEN is not set.
    """
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        print("Scraping LinkedIn profile mocked: APIFY_API_TOKEN not found.")
        return _mock_profile(url)

    client = ApifyClient(token)
    print(f"Scraping LinkedIn profile: {url} via Apify...")

    run_input = {
        "urls": [url],
        "proxy": {"useApifyProxy": True}
    }

    try:
        run = client.actor("harvestapi/linkedin-profile-scraper").call(run_input=run_input)

        for item in client.dataset(run["defaultDatasetId"]).iterate_items():

            def get_dates(entry):
                # Use pre-formatted period string when available (education has this)
                period = entry.get("period", "")
                if period:
                    return period
                # Fall back to startDate/endDate text fields
                start = entry.get("startDate") or entry.get("starts_at") or {}
                end   = entry.get("endDate")   or entry.get("ends_at")   or {}
                start_text = start.get("text") or str(start.get("year", "Unknown")) if start else "Unknown"
                end_text   = end.get("text")   or str(end.get("year", "Present"))   if end   else "Present"
                return f"{start_text} - {end_text}"

            # Location: actual schema returns an object, not a plain string
            location_raw = item.get("location", "")
            if isinstance(location_raw, dict):
                location = (
                    location_raw.get("linkedinText") or
                    (location_raw.get("parsed") or {}).get("text") or ""
                )
            else:
                location = location_raw or ""

            # Experience: actual key is "experience", title field is "position"
            career = []
            for exp in item.get("experience", [])[:6]:
                career.append({
                    "company":         (exp.get("companyName") or "Unknown"),
                    "title":           (exp.get("position") or exp.get("title") or "Unknown"),
                    "duration":        (exp.get("duration") or get_dates(exp)),
                    "employment_type": (exp.get("employmentType") or ""),
                    "description":     (exp.get("description") or "")[:600],
                })

            # Education: degree + fieldOfStudy are both present
            education = []
            for edu in item.get("education", [])[:3]:
                education.append({
                    "school":      (edu.get("schoolName") or edu.get("school") or "Unknown"),
                    "degree":      (edu.get("degree") or "Unknown"),
                    "field":       (edu.get("fieldOfStudy") or ""),
                    "years":       get_dates(edu),
                    "description": (edu.get("description") or ""),  # e.g. GPA
                })

            # Profile-level skills (top 15)
            skills = [
                s.get("name", "") for s in item.get("skills", [])[:15]
                if s.get("name")
            ]

            # Certifications
            certifications = [
                f"{c.get('title', '')} — {c.get('issuedBy', '')} ({c.get('issuedAt', '')})"
                for c in item.get("certifications", [])[:5]
                if c.get("title")
            ]

            # Languages
            languages = [
                f"{lang.get('name', '')} ({lang.get('proficiency', '')})"
                for lang in item.get("languages", [])
                if lang.get("name")
            ]

            return {
                "source":        "LinkedIn",
                "url":           url,
                "name":          (item.get("firstName", "") + " " + item.get("lastName", "")).strip(),
                "headline":      item.get("headline", ""),
                "location":      location,
                "summary":       item.get("about") or item.get("summary") or "",
                "connections":   item.get("connectionsCount") or item.get("connections") or "",
                "follower_count": item.get("followerCount") or 0,
                "top_skills":    item.get("topSkills") or "",
                "open_to_work":  item.get("openToWork") or False,
                "education":          education,
                "career_trajectory":  career,
                "skills":             skills,
                "certifications":     certifications,
                "languages":          languages,
            }

    except Exception as e:
        print(f"Apify LinkedIn profile scraping failed: {e}")

    return {"error": "Could not extract LinkedIn data", "url": url}


def scrape_linkedin_posts(url: str, limit: int = 20) -> Dict[str, Any]:
    """
    harvestapi/linkedin-profile-posts — full post text, engagement, and date.
    Posts are returned sorted newest-first with exponential recency weights applied.
    Falls back to mock data if APIFY_API_TOKEN is not set.
    """
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        print("Scraping LinkedIn posts mocked: APIFY_API_TOKEN not found.")
        return _mock_posts(url)

    client = ApifyClient(token)
    print(f"Scraping LinkedIn posts: {url} via Apify...")

    run_input = {
        "profileUrl": url,
        "maxPosts":   limit,
        "proxy": {"useApifyProxy": True},
    }

    try:
        run = client.actor("harvestapi/linkedin-profile-posts").call(run_input=run_input)
        now   = datetime.now(timezone.utc)
        posts = []

        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            post = {
                # Text — try every field name the actor may use
                "text": (
                    item.get("text") or
                    item.get("content") or
                    item.get("commentary") or
                    item.get("title") or ""
                ),
                # Date — multiple possible field names
                "publishedAt": (
                    item.get("publishedAt") or
                    item.get("date") or
                    item.get("postedAt") or
                    item.get("createdAt") or ""
                ),
                # Engagement
                "likes": (
                    item.get("numLikes") or
                    item.get("likesCount") or
                    item.get("reactions") or 0
                ),
                "comments": (
                    item.get("numComments") or
                    item.get("commentsCount") or 0
                ),
                "shares": (
                    item.get("numShares") or
                    item.get("sharesCount") or
                    item.get("repostsCount") or 0
                ),
                "post_url": (
                    item.get("postUrl") or
                    item.get("url") or
                    item.get("link") or ""
                ),
                "post_type": item.get("postType") or item.get("type") or "post",
            }
            post = _apply_recency_weight(post, now)
            posts.append(post)

        # Newest first
        posts.sort(key=lambda p: p.get("recency_weight", 0), reverse=True)

        return {
            "source": "LinkedIn_Posts",
            "url": url,
            "total_fetched": len(posts),
            "posts": posts,
        }

    except Exception as e:
        print(f"Apify LinkedIn posts scraping failed: {e}")

    return {"error": "Could not extract LinkedIn posts", "url": url, "posts": []}


def scrape_linkedin_parallel(url: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Fires harvestapi/linkedin-profile-scraper and harvestapi/linkedin-profile-posts
    simultaneously from a single LinkedIn URL.

    Returns:
        (profile_data, posts_data)
    """
    print(f"[Parallel] Launching LinkedIn profile + posts scrapers for: {url}")
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_profile = executor.submit(scrape_linkedin, url)
        future_posts   = executor.submit(scrape_linkedin_posts, url)
        profile_data   = future_profile.result()
        posts_data     = future_posts.result()
    print("[Parallel] Both LinkedIn scrapers complete.")
    return profile_data, posts_data


def scrape_instagram(url: str) -> Dict[str, Any]:
    """
    apify/instagram-scraper — profile info and recent post images.
    Falls back to mock data if APIFY_API_TOKEN is not set.
    """
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        print("Scraping Instagram mocked: APIFY_API_TOKEN not found.")
        return {
            "source": "Instagram",
            "url": url,
            "bio": "Building things. Living life. Coffee enthusiast. (MOCK)",
            "follower_count": 1200,
            "post_count": 87,
            "recent_images": [
                "https://example.com/mock_image_1.jpg",
                "https://example.com/mock_image_2.jpg"
            ]
        }

    client = ApifyClient(token)
    print(f"Scraping Instagram profile: {url} via Apify...")

    run_input = {
        "directUrls": [url],
        "resultsType": "details",
        "resultsLimit": 1,
    }

    try:
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)

        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            recent_images = [
                post.get("displayUrl")
                for post in item.get("latestPosts", [])[:6]
                if post.get("displayUrl")
            ]
            return {
                "source": "Instagram",
                "url": url,
                "bio": item.get("biography", ""),
                "follower_count": item.get("followersCount", 0),
                "post_count": item.get("postsCount", 0),
                "recent_images": recent_images
            }

    except Exception as e:
        print(f"Apify Instagram scraping failed: {e}")

    return {"error": "Could not extract Instagram data", "url": url}
