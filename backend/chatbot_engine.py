"""
chatbot_engine.py
VoxBot AI chatbot using Groq API.
Fetches real current news headlines to ground responses in live data.
"""

import os
import re
from groq import Groq
from news_fetcher import fetch_top_headlines, search_news

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
GROQ_MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are VoxBot, an intelligent news assistant for VoxLens — an AI-powered news platform.

Your role:
- Answer questions about news topics using the LIVE NEWS CONTEXT provided to you
- Summarise and explain current headlines in simple, accessible language
- Provide balanced, factual perspectives — never take political sides
- Help users understand the context and impact of news events
- Be conversational, friendly, and concise (2-4 paragraphs max)

Rules:
- ALWAYS reference the live news context when it is relevant to the user's question
- Clearly mention article titles or sources when discussing specific stories
- If asked about something not in the news context, say so honestly
- Never fabricate facts or invent news stories
- Use plain language, avoid jargon
"""


def _build_news_context(user_message: str) -> str:
    """
    Fetch relevant live news to inject as context for the chatbot.
    Tries keyword search first, then falls back to top headlines.
    """
    context_articles = []

    # Extract keywords from user message for targeted search
    keywords = _extract_keywords(user_message)

    if keywords:
        try:
            results = search_news(query=keywords, page_size=5)
            context_articles.extend(results)
        except Exception:
            pass

    # Always include some top headlines for general context
    try:
        headlines = fetch_top_headlines(country="in", page_size=8)
        context_articles.extend(headlines)
    except Exception:
        pass

    if not context_articles:
        return ""

    # Build context string (deduplicated by title)
    seen = set()
    lines = ["=== CURRENT NEWS HEADLINES (live) ===\n"]
    for a in context_articles:
        title = a.get("title", "")
        if title in seen or not title:
            continue
        seen.add(title)
        source = a.get("source", {}).get("name", "")
        desc = a.get("description", "") or a.get("content", "")
        lines.append(f"• [{source}] {title}")
        if desc:
            lines.append(f"  {desc[:200]}")
    lines.append("\n=== Use the above headlines to inform your answer ===")
    return "\n".join(lines)


def _extract_keywords(message: str) -> str:
    """Extract useful search keywords from user message."""
    # Remove common stop words and question words
    stop = {"what", "who", "where", "when", "why", "how", "is", "are", "was",
            "were", "the", "a", "an", "in", "on", "at", "of", "to", "for",
            "me", "tell", "explain", "about", "latest", "news", "current",
            "today", "recent", "update", "can", "you", "please", "give"}
    words = re.findall(r'\b[a-zA-Z]{3,}\b', message.lower())
    keywords = [w for w in words if w not in stop]
    return " ".join(keywords[:6]) if keywords else ""


def get_chatbot_response(user_message: str, conversation_history: list = None, news_context: str = "") -> str:
    """
    Generate a VoxBot response grounded in current news.
    Args:
        user_message: The user's question
        conversation_history: Previous messages [{"role": ..., "content": ...}]
        news_context: Optional pre-supplied context (from article modal)
    Returns:
        Response string
    """
    if conversation_history is None:
        conversation_history = []

    # Build live news context if not already supplied
    if not news_context:
        news_context = _build_news_context(user_message)

    if client:
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            if news_context:
                messages.append({
                    "role": "system",
                    "content": news_context,
                })

            messages.extend(conversation_history[-10:])
            messages.append({"role": "user", "content": user_message})

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=600,
                temperature=0.8,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"[chatbot_engine] Groq error: {e}")

    return _fallback_response(user_message, news_context)


def _fallback_response(message: str, news_context: str = "") -> str:
    """Rule-based fallback when API is unavailable."""
    msg = message.lower()
    if any(w in msg for w in ["hello", "hi", "hey"]):
        return "Hi! I'm VoxBot, your AI news assistant. Ask me about any current news topic and I'll help you understand what's happening and why it matters!"
    if news_context:
        return (
            "I have access to today's live news headlines. Based on current reports, there are several "
            "developments across technology, politics, climate, and economics. Could you be more specific "
            "about what you'd like to know? For example: 'What's happening with AI regulation?' or "
            "'Explain the latest economic news.'"
        )
    return (
        "I'm having trouble connecting to the news feed right now. Please check your API keys "
        "and internet connection. Once connected, I can discuss live news across any topic!"
    )
