"""
ai_engine.py - Uses Groq API for fast AI inference.
Powers: Smart Brief, So What?, Pros/Cons, Quiz, Timeline, Sentiment.
"""

import os
import json
import re
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
GROQ_MODEL = "llama-3.1-8b-instant"


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 600) -> str:
    if not client:
        return None
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ai_engine] Groq error: {e}")
        return None


def get_smart_brief(title: str, content: str) -> list:
    system = (
        "You are a concise news summarizer. Respond with EXACTLY 5 bullet points. "
        "Each line must start with a dash (-). No intro text, no numbering."
    )
    user = f"Summarize in exactly 5 bullet points:\n\nTitle: {title}\n\nContent: {content[:2000]}"
    result = _call_llm(system, user, max_tokens=400)

    if result:
        bullets = []
        for line in result.split("\n"):
            line = line.strip()
            if line:
                clean = re.sub(r'^[-•*\d\.\)]+\s*', '', line).strip()
                if len(clean) > 10:
                    bullets.append(clean)
        if len(bullets) >= 3:
            return bullets[:5]

    sentences = re.split(r'(?<=[.!?])\s+', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    return sentences[:5] if len(sentences) >= 5 else [
        f"This article covers: {title}",
        "Key developments were reported across major news outlets.",
        "The story has significant implications for affected communities.",
        "Experts and officials have weighed in on the situation.",
        "Further updates are expected as the story develops.",
    ]


def get_so_what(title: str, content: str) -> dict:
    system = (
        "You are a news impact analyst explaining news to ordinary citizens. "
        'Respond ONLY with valid JSON: {"why_matters": "...", "citizen_impact": "...", "future_implications": "..."}. '
        "Each value = 2-3 clear sentences. No markdown, no extra text."
    )
    user = f"Analyze the impact:\n\nTitle: {title}\n\nContent: {content[:2000]}"
    result = _call_llm(system, user, max_tokens=500)

    if result:
        try:
            clean = re.sub(r'```json|```', '', result).strip()
            data = json.loads(clean)
            return {
                "why_matters": data.get("why_matters", ""),
                "citizen_impact": data.get("citizen_impact", ""),
                "future_implications": data.get("future_implications", ""),
            }
        except Exception:
            pass

    return {
        "why_matters": f"This story about '{title}' is significant because it directly affects public policy, community life, or economic conditions that touch everyday citizens.",
        "citizen_impact": "People may see effects through changes in government services, prices, job opportunities, or community resources. Staying informed helps families plan ahead.",
        "future_implications": "As this develops, it could reshape legislation, market trends, or social behaviour. Watch for follow-up policy responses over the coming weeks.",
    }


def get_pros_cons(title: str, content: str) -> dict:
    system = (
        "You are a balanced news analyst. "
        'Respond ONLY with valid JSON: {"pros": ["...", "..."], "cons": ["...", "..."]}. '
        "3-4 items each. No extra text."
    )
    user = f"Pros and cons for:\n\nTitle: {title}\n\nContent: {content[:1500]}"
    result = _call_llm(system, user, max_tokens=400)

    if result:
        try:
            clean = re.sub(r'```json|```', '', result).strip()
            data = json.loads(clean)
            pros = data.get("pros", [])
            cons = data.get("cons", [])
            if pros and cons:
                return {"pros": pros[:4], "cons": cons[:4]}
        except Exception:
            pass

    return {
        "pros": [
            "May lead to positive policy changes benefiting the broader community.",
            "Creates opportunities for dialogue and collaborative problem-solving.",
            "Raises awareness about an important issue needing public attention.",
        ],
        "cons": [
            "Implementation may face practical challenges and resource constraints.",
            "Different stakeholder groups may have conflicting interests.",
            "Short-term disruptions or costs may affect some communities negatively.",
        ],
    }


def get_quiz(title: str, content: str) -> dict:
    system = (
        "You are an educational quiz creator. Create one multiple-choice comprehension question. "
        'Respond ONLY with valid JSON: {"question": "...", "options": ["A", "B", "C", "D"], '
        '"correct_index": 0, "explanation": "..."}. No extra text.'
    )
    user = f"Create a quiz for:\n\nTitle: {title}\n\nContent: {content[:1500]}"
    result = _call_llm(system, user, max_tokens=350)

    if result:
        try:
            clean = re.sub(r'```json|```', '', result).strip()
            data = json.loads(clean)
            if data.get("question") and data.get("options") and len(data["options"]) == 4:
                return data
        except Exception:
            pass

    return {
        "question": f"What is the primary subject of this article about '{title[:60]}'?",
        "options": [
            "The main topic as described in the article",
            "An unrelated political development",
            "A sports event from last season",
            "A fictional news story",
        ],
        "correct_index": 0,
        "explanation": "The article's title and opening paragraphs clearly establish the main topic being covered.",
    }


def get_story_timeline(title: str, content: str) -> list:
    system = (
        "You are a news timeline creator. Create a realistic 4-6 entry timeline of how this story developed. "
        'Respond ONLY with valid JSON array: [{"date": "...", "event": "...", "significance": "minor|major"}]. '
        "No extra text."
    )
    user = f"Create story timeline for:\n\nTitle: {title}\n\nContent: {content[:1500]}"
    result = _call_llm(system, user, max_tokens=500)

    if result:
        try:
            clean = re.sub(r'```json|```', '', result).strip()
            data = json.loads(clean)
            if isinstance(data, list) and len(data) >= 3:
                return data[:6]
        except Exception:
            pass

    return [
        {"date": "6 months ago", "event": "Initial reports surfaced about the underlying issue", "significance": "minor"},
        {"date": "3 months ago", "event": "Experts and stakeholders began discussing implications", "significance": "minor"},
        {"date": "1 month ago", "event": "Official response and policy discussions began", "significance": "major"},
        {"date": "2 weeks ago", "event": "Public debate intensified as new details emerged", "significance": "major"},
        {"date": "This week", "event": f"Major development reported: {title[:80]}", "significance": "major"},
        {"date": "Coming soon", "event": "Further investigation and follow-up actions expected", "significance": "minor"},
    ]


def analyze_sentiment(text: str) -> dict:
    positive_words = {
        "breakthrough", "success", "growth", "improve", "benefit", "positive",
        "hope", "achieve", "win", "advance", "progress", "record", "landmark",
        "promising", "innovative", "historic", "milestone", "recovery", "boost"
    }
    negative_words = {
        "crisis", "fail", "decline", "threat", "danger", "risk", "collapse",
        "loss", "concern", "problem", "issue", "challenge", "controversy",
        "conflict", "disaster", "protest", "violence", "shortage", "recession"
    }
    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))
    pos = len(words & positive_words)
    neg = len(words & negative_words)
    total = pos + neg
    score = 0 if total == 0 else (pos - neg) / total
    if score > 0.2:
        label, tone = "Positive", "optimistic"
    elif score < -0.2:
        label, tone = "Negative", "critical"
    else:
        label, tone = "Neutral", "balanced"
    return {"tone": tone, "score": round(score, 2), "label": label}
