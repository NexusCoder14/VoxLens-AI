# 📰 VoxLens — AI-Powered News Platform

**Transform how you consume news with intelligent summaries, real-time insights, and AI-powered analysis.**

🌐 **Live Demo:** [https://voxlens-frontend.vercel.app](https://voxlens-frontend.vercel.app)

---

## ✨ Features

- **📍 Location-Based News** — Auto-detects your city and serves hyperlocal news
- **💡 So What?** — AI explains why news matters and real-world impact
- **📋 Smart Brief** — Auto-generated 5-bullet summary of any article
- **⚖️ Pros & Cons** — Balanced perspectives on topics
- **🧠 Quiz Generator** — Test comprehension with AI-generated questions
- **🕐 Story Timeline** — Visual timeline showing how stories evolve
- **📊 Sentiment Analyzer** — Tone detection (positive, negative, neutral)
- **🔊 Text-to-Speech** — Listen to articles for accessibility
- **🌙 Dark Mode** — Eye-friendly theme switching
- **🤖 AI Chatbot** — Ask questions about news with context-aware responses

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  VOXLENS ARCHITECTURE                    │
└─────────────────────────────────────────────────────────┘

┌───────────────────────────────┐
│   Frontend (Vercel)           │
│  ├─ index.html                │
│  ├─ style.css                 │
│  └─ script.js                 │
└────────────┬──────────────────┘
             │ HTTPS
             ▼
┌───────────────────────────────┐
│   FastAPI Backend (Render)    │
│  ├─ News Routes               │
│  ├─ AI Analysis Routes        │
│  ├─ Chat Routes               │
│  └─ Discussion Routes         │
└────┬───────────┬───────────┬──┘
     │           │           │
     ▼           ▼           ▼
  NewsAPI    Groq API   File Storage
  (news)   (AI)      (comments)
```

---

## � Project Structure

```
voxlens-ai/
│
├── backend/                    # FastAPI Backend
│   ├── app.py                  # Entry point, CORS config, route registration
│   ├── routes.py               # All API endpoints (news, AI, chat, discussion)
│   ├── ai_engine.py            # AI analysis engine
│   ├── news_fetcher.py         # NewsAPI integration
│   ├── chatbot_engine.py       # AI chatbot
│   ├── discussion_engine.py    # Community comments
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Environment variables template
│
├── frontend/                   # Vanilla JavaScript Frontend
│   ├── index.html              # Single-page app with all UI components
│   ├── style.css               # Responsive CSS with light/dark modes
│   ├── script.js               # Frontend logic, API calls, UI state
│   └── static/                 # Static assets (images, charts)
│
├── runtime.txt                 # Python version specification
├── README.md                   # This file
└── .gitignore                  # Git ignore rules
```

**Visit:** [https://voxlens-frontend.vercel.app](https://voxlens-frontend.vercel.app)

No installation required. Just open and start exploring news!


