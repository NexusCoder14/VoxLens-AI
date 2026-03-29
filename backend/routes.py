"""
routes.py
All API route definitions for VoxLens.
Organized by feature: news, AI analysis, chatbot, discussions, TTS.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import os
import base64

from news_fetcher import (
    fetch_top_headlines,
    fetch_local_news,
    search_news,
    fetch_article_from_url,
)
from ai_engine import (
    get_smart_brief,
    get_so_what,
    get_pros_cons,
    get_quiz,
    get_story_timeline,
    analyze_sentiment,
)
from chatbot_engine import get_chatbot_response
from discussion_engine import (
    get_discussions,
    post_comment,
    like_comment,
    get_trending_topics,
    COMMUNITY_GUIDELINES,
)

router = APIRouter()

# ─────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────

class ArticleRequest(BaseModel):
    title: str
    content: str
    url: Optional[str] = ""

class URLRequest(BaseModel):
    url: str

class ChatMessage(BaseModel):
    message: str
    history: Optional[List[dict]] = []
    news_context: Optional[str] = ""

class CommentRequest(BaseModel):
    article_url: str
    username: str
    text: str

class LikeRequest(BaseModel):
    article_url: str
    comment_id: str

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "alloy"  # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer


# ─────────────────────────────────────────────
# NEWS ROUTES
# ─────────────────────────────────────────────

@router.get("/news/headlines")
async def headlines(
    country: str = Query("in", description="ISO country code"),
    category: str = Query("general", description="News category"),
    page_size: int = Query(20, ge=1, le=50),
):
    """Fetch top headlines for a country and category."""
    articles = fetch_top_headlines(country=country, category=category, page_size=page_size)
    return {"articles": articles, "count": len(articles)}


@router.get("/news/local")
async def local_news(
    city: str = Query(..., description="City name"),
    country: str = Query("in", description="Country code"),
):
    """Fetch news relevant to a specific city."""
    articles = fetch_local_news(city=city, country=country)
    return {"articles": articles, "city": city, "count": len(articles)}


@router.get("/news/search")
async def search(query: str = Query(..., description="Search keywords")):
    """Search news articles by keyword."""
    articles = search_news(query=query)
    return {"articles": articles, "query": query, "count": len(articles)}


@router.post("/news/from-url")
async def article_from_url(request: URLRequest):
    """Fetch and parse a news article from a URL."""
    article = fetch_article_from_url(request.url)
    if not article:
        raise HTTPException(status_code=422, detail="Could not extract article from URL. The site may block scraping.")
    return {"article": article}


# ─────────────────────────────────────────────
# AI ANALYSIS ROUTES
# ─────────────────────────────────────────────

@router.post("/ai/smart-brief")
async def smart_brief(request: ArticleRequest):
    """Generate a 5-bullet-point Smart Brief for an article."""
    bullets = get_smart_brief(title=request.title, content=request.content)
    return {"bullets": bullets, "count": len(bullets)}


@router.post("/ai/so-what")
async def so_what(request: ArticleRequest):
    """Explain why the news matters and its impact."""
    impact = get_so_what(title=request.title, content=request.content)
    return impact


@router.post("/ai/pros-cons")
async def pros_cons(request: ArticleRequest):
    """Generate balanced pros and cons for a news article."""
    analysis = get_pros_cons(title=request.title, content=request.content)
    return analysis


@router.post("/ai/quiz")
async def quiz(request: ArticleRequest):
    """Generate a multiple-choice quiz question for the article."""
    question = get_quiz(title=request.title, content=request.content)
    return question


@router.post("/ai/timeline")
async def timeline(request: ArticleRequest):
    """Generate a story timeline for the news article."""
    events = get_story_timeline(title=request.title, content=request.content)
    return {"timeline": events}


@router.post("/ai/sentiment")
async def sentiment(request: ArticleRequest):
    """Analyze the sentiment/tone of an article."""
    result = analyze_sentiment(text=request.content)
    return result


# ─────────────────────────────────────────────
# TEXT-TO-SPEECH ROUTE
# ─────────────────────────────────────────────

@router.post("/tts/speak")
async def text_to_speech(request: TTSRequest):
    """
    Convert article text to speech using browser Web Speech API.
    Groq does not provide TTS so we signal the frontend to use browser TTS.
    """
    return {
        "audio_base64": None,
        "format": None,
        "provider": "browser",
        "text": request.text[:3000],
    }


# ─────────────────────────────────────────────
# CHATBOT ROUTES
# ─────────────────────────────────────────────

@router.post("/chat")
async def chat(request: ChatMessage):
    """Send a message to the AI news chatbot."""
    response = get_chatbot_response(
        user_message=request.message,
        conversation_history=request.history,
        news_context=request.news_context,
    )
    return {"response": response}


# ─────────────────────────────────────────────
# DISCUSSION ROUTES
# ─────────────────────────────────────────────

@router.get("/discussions")
async def get_article_discussions(article_url: str = Query(...)):
    """Get all comments for a specific article."""
    data = get_discussions(article_url=article_url)
    return data


@router.post("/discussions/comment")
async def add_comment(request: CommentRequest):
    """Post a new comment on an article."""
    result = post_comment(
        article_url=request.article_url,
        username=request.username,
        text=request.text,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to post comment"))
    return result


@router.post("/discussions/like")
async def like_a_comment(request: LikeRequest):
    """Like a comment."""
    result = like_comment(article_url=request.article_url, comment_id=request.comment_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/discussions/trending")
async def trending_discussions():
    """Get articles with the most discussion activity."""
    topics = get_trending_topics()
    return {"trending": topics}


@router.get("/discussions/guidelines")
async def community_guidelines():
    """Get community discussion guidelines."""
    return {"guidelines": COMMUNITY_GUIDELINES}
