"""
PromptShield AI Service — FastAPI application entry point.

Endpoints:
  GET  /         — service identity
  GET  /health   — health check (used by Docker/load balancers)
  POST /analyze  — privacy analysis and anonymization without optimization
  POST /optimize — prompt optimization and privacy analysis pipeline

See app/api/optimize.py for the full pipeline documentation.
"""

import logging
import logging.config

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app import config
from app.api.optimize import router as optimize_router
from app.api.analyze import router as analyze_router

# ── Logging setup ──────────────────────────────────────────────────────────────
# Structured logging with INFO level by default.
# IMPORTANT: Raw prompt content is never logged at INFO or above.
# Only metadata (lengths, entity counts, risk levels) is logged.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

from app.services.flan_t5_service import flan_t5_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: optionally load model on startup and cleanup on shutdown."""
    # Warn loudly if running without API key authentication (insecure when tunnel is active)
    if not config.AI_SERVICE_API_KEY:
        logger.warning(
            "AI_SERVICE_API_KEY is not set — service-to-service authentication is DISABLED. "
            "Set AI_SERVICE_API_KEY before exposing this service via Cloudflare Tunnel."
        )
    else:
        logger.info("AI_SERVICE_API_KEY is configured — service-to-service authentication ENABLED.")

    if config.FLAN_T5_ENABLED:
        logger.info("FLAN_T5_ENABLED is true: initializing model on application startup...")
        try:
            flan_t5_service.load_model()
        except Exception as exc:
            logger.warning("Startup model initialization failed: %s", exc)
    yield
    if flan_t5_service.is_available:
        flan_t5_service.unload_model()


# ── Application ────────────────────────────────────────────────────────────────

app = FastAPI(
    title=config.SERVICE_TITLE,
    description=config.SERVICE_DESCRIPTION,
    version=config.SERVICE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(optimize_router)
app.include_router(analyze_router)


# ── Global exception handlers ──────────────────────────────────────────────────

@app.exception_handler(ValidationError)
async def pydantic_validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with a 422 response."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(
    request: Request, exc: ValueError
) -> JSONResponse:
    """Handle ValueError from pipeline stages with a 400 response."""
    logger.warning("Bad request: %s", exc)
    return JSONResponse(
        status_code=400,
        content={
            "error": "Bad request",
            "detail": str(exc),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all handler — returns 500 without exposing internal details."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again.",
        },
    )


# ── Health and identity endpoints ──────────────────────────────────────────────

@app.get(
    "/",
    summary="Service identity",
    tags=["Health"],
)
def root() -> dict:
    """Returns service name, version, and status."""
    return {
        "service": config.SERVICE_TITLE,
        "version": config.SERVICE_VERSION,
        "status": "running",
    }


@app.get(
    "/health",
    summary="Health check",
    tags=["Health"],
)
def health() -> dict:
    """
    Simple health check endpoint.
    Returns 200 if the service is running.
    Used by Docker health checks and load balancers.
    """
    return {"status": "healthy"}