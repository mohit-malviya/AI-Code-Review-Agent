from fastapi import FastAPI

from app.api.webhook import router as webhook_router
from app.api.approval import router as approval_router

app = FastAPI(
    title="AI Code Review Agent",
    version="1.0.0",
    description="AI Agent for reviewing GitHub commits and pull requests",
)

# Include Routers
app.include_router(approval_router)
app.include_router(webhook_router)


@app.get("/")
def home():
    return {
        "status": "online",
        "message": "AI Code Review Agent is running successfully!",
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check():
    """
    Dedicated health check endpoint for Google Cloud Run startup & liveness probes.
    """
    return {
        "status": "healthy",
        "service": "ai-code-review-agent",
    }