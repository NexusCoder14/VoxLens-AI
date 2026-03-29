"""
news_fetcher.py
Fetches REAL, FRESH news from NewsAPI with proper region/country support.
Always fetches live data — mock articles only as last-resort fallback.
"""

import os
import time
import hashlib
import requests
from typing import Optional
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_API_BASE = "https://newsapi.org/v2"

# Simple in-memory cache: {cache_key: (timestamp, data)}
_cache = {}
CACHE_TTL = 300  # 5 minutes


def _cached_get(url: str, params: dict) -> Optional[dict]:
    """Make a cached GET request to NewsAPI."""
    cache_key = hashlib.md5((url + str(sorted(params.items()))).encode()).hexdigest()
    now = time.time()

    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if now - ts < CACHE_TTL:
            return data

    try:
        resp = requests.get(url, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        _cache[cache_key] = (now, data)
        return data
    except Exception as e:
        print(f"[news_fetcher] API error: {e}")
        return None


def fetch_top_headlines(country: str = "in", category: str = "general", page_size: int = 20) -> list:
    """
    Fetch live top headlines from NewsAPI.
    Falls back to 'everything' endpoint with recent filter if country headlines fail.
    """
    if not NEWS_API_KEY:
        print("[news_fetcher] No NEWS_API_KEY — returning mock articles")
        return _get_mock_articles(12)

    # Primary: country top headlines
    data = _cached_get(f"{NEWS_API_BASE}/top-headlines", {
        "apiKey": NEWS_API_KEY,
        "country": country,
        "category": category,
        "pageSize": min(page_size, 40),
    })

    articles = []
    if data and data.get("articles"):
        articles = [_normalize(a) for a in data["articles"] if a.get("title") and a["title"] != "[Removed]"]

    # If country returns < 5 results, supplement with global English news
    if len(articles) < 5:
        data2 = _cached_get(f"{NEWS_API_BASE}/top-headlines", {
            "apiKey": NEWS_API_KEY,
            "language": "en",
            "category": category,
            "pageSize": min(page_size, 40),
        })
        if data2 and data2.get("articles"):
            extra = [_normalize(a) for a in data2["articles"] if a.get("title") and a["title"] != "[Removed]"]
            # Merge, deduplicate by title
            seen = {a["title"] for a in articles}
            for a in extra:
                if a["title"] not in seen:
                    articles.append(a)
                    seen.add(a["title"])

    return articles[:page_size] if articles else _get_mock_articles(12)


def fetch_local_news(city: str, country: str = "in", page_size: int = 15) -> list:
    """
    Fetch news relevant to a specific city using keyword search.
    Uses 'everything' endpoint with city + country name for broad coverage.
    """
    if not NEWS_API_KEY:
        return _get_mock_articles(8, city=city)

    # Map country codes to readable names for better search results
    country_names = {
        "in": "India", "us": "USA", "gb": "UK", "au": "Australia",
        "ca": "Canada", "de": "Germany", "fr": "France", "jp": "Japan",
        "cn": "China", "br": "Brazil", "za": "South Africa", "ng": "Nigeria",
    }
    country_name = country_names.get(country.lower(), country.upper())

    # Search with city name — try multiple query variants
    queries = [
        f'"{city}"',
        f"{city} {country_name}",
        city,
    ]

    all_articles = []
    seen_titles = set()

    for q in queries:
        if len(all_articles) >= page_size:
            break
        data = _cached_get(f"{NEWS_API_BASE}/everything", {
            "apiKey": NEWS_API_KEY,
            "q": q,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(page_size, 30),
        })
        if data and data.get("articles"):
            for a in data["articles"]:
                title = a.get("title", "")
                if title and title != "[Removed]" and title not in seen_titles:
                    all_articles.append(_normalize(a))
                    seen_titles.add(title)

    return all_articles[:page_size] if all_articles else _get_mock_articles(8, city=city)


def search_news(query: str, page_size: int = 15) -> list:
    """Search for news articles using a keyword query."""
    if not NEWS_API_KEY:
        return _get_mock_articles(6)

    data = _cached_get(f"{NEWS_API_BASE}/everything", {
        "apiKey": NEWS_API_KEY,
        "q": query,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": min(page_size, 40),
    })

    if data and data.get("articles"):
        articles = [_normalize(a) for a in data["articles"] if a.get("title") and a["title"] != "[Removed]"]
        return articles[:page_size]

    return _get_mock_articles(6)


def fetch_article_from_url(url: str) -> Optional[dict]:
    """Scrape article content from a given URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract title
        title = ""
        for selector in [soup.find("h1"), soup.find("meta", property="og:title"), soup.title]:
            if selector:
                title = selector.get_text(strip=True) if hasattr(selector, 'get_text') else (selector.get("content", "") or str(selector.string or ""))
                if title:
                    break

        # Extract body paragraphs
        paragraphs = soup.find_all("p")
        content = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
        content = re.sub(r'\s+', ' ', content).strip()[:4000]

        if not content and not title:
            return None

        domain = url.split("/")[2].replace("www.", "")
        return {
            "title": title or domain,
            "content": content,
            "url": url,
            "source": {"name": domain},
            "urlToImage": None,
            "publishedAt": datetime.now(timezone.utc).isoformat(),
            "description": content[:200] if content else "",
            "author": "",
        }
    except Exception as e:
        print(f"[news_fetcher] URL scrape error for {url}: {e}")
        return None


def _normalize(raw: dict) -> dict:
    """Normalize a raw NewsAPI article into a standard format."""
    content = raw.get("content", "") or raw.get("description", "") or ""
    # NewsAPI often truncates content with "[+N chars]" — clean it
    content = re.sub(r'\[\+\d+ chars\]', '', content).strip()

    return {
        "title": (raw.get("title") or "Untitled").strip(),
        "description": (raw.get("description") or "").strip(),
        "content": content,
        "url": raw.get("url", ""),
        "urlToImage": raw.get("urlToImage", ""),
        "publishedAt": raw.get("publishedAt", ""),
        "source": raw.get("source", {"name": "Unknown"}),
        "author": raw.get("author", "") or "",
    }


def _get_mock_articles(count: int, city: str = "") -> list:
    """Return mock articles when API key is missing (demo mode)."""
    loc = f" in {city}" if city else ""
    articles = [
        {
            "title": f"Global Climate Summit{loc} Reaches Landmark Agreement",
            "description": "World leaders finalise a new climate accord aimed at limiting global temperature rise.",
            "content": "World leaders from over 190 countries gathered at the Global Climate Summit to finalise a landmark agreement. The accord includes commitments to phase out coal by 2040, invest $100 billion annually in clean energy, and establish a carbon trading mechanism. Environmental groups have called it a historic step forward.",
            "url": "https://example.com/climate-summit",
            "urlToImage": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800",
            "publishedAt": datetime.now(timezone.utc).isoformat(),
            "source": {"name": "Global News"},
            "author": "Jane Smith",
        },
        {
            "title": f"Tech Giants Face New AI Regulation{loc}",
            "description": "Governments worldwide introduce laws to regulate artificial intelligence development.",
            "content": "Governments are rolling out comprehensive regulations targeting AI development. The EU's AI Act mandates transparency, safety testing, and human oversight for high-risk AI systems. The US Senate has proposed the American AI Safety Act requiring companies to disclose training data and conduct bias audits.",
            "url": "https://example.com/ai-regulation",
            "urlToImage": "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=800",
            "publishedAt": datetime.now(timezone.utc).isoformat(),
            "source": {"name": "Tech Tribune"},
            "author": "Raj Patel",
        },
        {
            "title": f"Economic Growth Slows Amid Inflation Concerns{loc}",
            "description": "Central banks signal interest rate adjustments as inflation remains elevated.",
            "content": "Global economic growth is decelerating as central banks grapple with elevated inflation. The IMF revised its global growth forecast downward to 2.8% for 2025. The US Fed, ECB, and Bank of England have all signalled a cautious approach to rate cuts, prioritising inflation control over growth stimulation.",
            "url": "https://example.com/economic-growth",
            "urlToImage": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800",
            "publishedAt": datetime.now(timezone.utc).isoformat(),
            "source": {"name": "Finance Daily"},
            "author": "Maria Chen",
        },
        {
            "title": f"Breakthrough in Quantum Computing{loc} Announced",
            "description": "Scientists achieve quantum advantage in drug discovery simulations.",
            "content": "Researchers have announced a breakthrough in quantum computing, demonstrating quantum advantage in real-world drug discovery simulations. The team's 1,000-qubit processor modelled complex protein folding interactions in hours — a task that would take classical supercomputers thousands of years.",
            "url": "https://example.com/quantum-computing",
            "urlToImage": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800",
            "publishedAt": datetime.now(timezone.utc).isoformat(),
            "source": {"name": "Science Today"},
            "author": "Dr. Alan Wu",
        },
        {
            "title": f"Infrastructure Investment Bill Passed{loc}",
            "description": "Major infrastructure package modernises roads, bridges, and digital connectivity.",
            "content": "A sweeping infrastructure investment bill has been signed into law, allocating funds for road repairs, bridge upgrades, high-speed rail, and nationwide broadband. The legislation designates significant funding for rural connectivity and aims to create thousands of construction jobs.",
            "url": "https://example.com/infrastructure-bill",
            "urlToImage": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800",
            "publishedAt": datetime.now(timezone.utc).isoformat(),
            "source": {"name": "Policy Watch"},
            "author": "Sarah Johnson",
        },
        {
            "title": f"Health Ministry Launches Mental Health Initiative{loc}",
            "description": "New national programme targets mental health support for young adults.",
            "content": "The Health Ministry has announced a comprehensive national mental health initiative targeting young adults. The programme includes free online counselling, community mental health centres in 500 cities, and a national awareness campaign. Funding of $2 billion over five years will support training of 10,000 new mental health professionals.",
            "url": "https://example.com/mental-health",
            "urlToImage": "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800",
            "publishedAt": datetime.now(timezone.utc).isoformat(),
            "source": {"name": "Health Herald"},
            "author": "Dr. Priya Nair",
        },
        {
            "title": f"Renewable Energy Capacity Doubles{loc}",
            "description": "Solar and wind installations hit record levels globally.",
            "content": "Global renewable energy capacity has doubled over three years, with solar and wind power installations reaching record highs. Solar energy now accounts for 25% of global electricity generation, up from 12% in 2021. Energy analysts predict renewables will surpass fossil fuels as the primary electricity source by 2030.",
            "url": "https://example.com/renewable-energy",
            "urlToImage": "https://images.unsplash.com/photo-1509391366360-2e959784a276?w=800",
            "publishedAt": datetime.now(timezone.utc).isoformat(),
            "source": {"name": "Energy Observer"},
            "author": "Thomas Green",
        },
        {
            "title": f"Education Reform Reshapes School Curriculum{loc}",
            "description": "New curriculum introduces AI literacy and critical thinking as core subjects.",
            "content": "Education authorities unveiled sweeping curriculum reforms introducing AI literacy, digital citizenship, and critical thinking as mandatory subjects from grade 6. The reforms also emphasise project-based learning and reduce rote memorisation. Teachers will receive paid training programmes over an 18-month transition.",
            "url": "https://example.com/education-reform",
            "urlToImage": "https://images.unsplash.com/photo-1497486751825-1233686d5d80?w=800",
            "publishedAt": datetime.now(timezone.utc).isoformat(),
            "source": {"name": "Education Weekly"},
            "author": "Lisa Park",
        },
    ]
    return articles[:count]
