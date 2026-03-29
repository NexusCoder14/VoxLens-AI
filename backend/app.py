"""
VoxLens Backend - Main Application Entry Point
FastAPI server that orchestrates all AI-powered features.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from routes import router

app = FastAPI(
    title="VoxLens API",
    description="AI-powered news platform backend",
    version="1.0.0"
)

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://voxlens-frontend.vercel.app",  # Your Vercel frontend URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (for frontend if serving from backend)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Register all routes
app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "VoxLens API is running",
        "docs": "/docs",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
