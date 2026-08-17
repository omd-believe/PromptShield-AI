from fastapi import FastAPI

from app.api.optimize import router as optimize_router

app = FastAPI(
    title="PromptShield AI",
    description="AI service for privacy-preserving prompt optimization",
    version="0.1.0"
)

app.include_router(optimize_router)


@app.get("/")
def root():
    return {
        "service": "PromptShield AI",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }