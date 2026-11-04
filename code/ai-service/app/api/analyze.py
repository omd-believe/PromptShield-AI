"""POST /analyze — privacy-only prompt analysis endpoint."""

import logging
import secrets
import uuid

from fastapi import APIRouter, HTTPException, status, Header, Response

from app import config
from app.models.request import PromptRequest
from app.models.response import PrivacyResponse
from app.services.shared import preprocessor, privacy_engine

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Service-to-service authentication ─────────────────────────────────────────

def _require_api_key(api_key: str | None) -> None:
    """Validate the API key (from X-API-Key or X-AI-Service-Key) when AI_SERVICE_API_KEY is configured.

    Uses constant-time comparison to prevent timing attacks.
    If AI_SERVICE_API_KEY is not configured, authentication is skipped
    (useful for local development without a tunnel).
    """
    configured_key = config.AI_SERVICE_API_KEY
    if not configured_key:
        return
    if not api_key or not secrets.compare_digest(
        configured_key.encode(), api_key.encode()
    ):
        logger.warning("Rejected /analyze request: missing or invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


@router.post(
    "/analyze",
    response_model=PrivacyResponse,
    summary="Analyze a prompt for privacy risks",
)
def analyze_prompt(
    request: PromptRequest,
    response: Response = None,
    x_request_id: str | None = Header(None, alias="X-Request-ID"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_ai_service_key: str | None = Header(None, alias="X-AI-Service-Key"),
) -> PrivacyResponse:
    """Detect and anonymize sensitive information without optimizing the prompt."""
    _require_api_key(x_api_key or x_ai_service_key)

    req_id = x_request_id or str(uuid.uuid4())
    if response is not None:
        response.headers["X-Request-ID"] = req_id

    logger.info("[%s] Privacy analysis request received: prompt_length=%d", req_id, len(request.prompt))
    try:
        cleaned_prompt = preprocessor.clean(request.prompt)
        privacy_result = privacy_engine.analyze(
            cleaned_prompt, request.privacy_policy
        )
    except ValueError as exc:
        logger.warning("Privacy analysis rejected prompt: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Privacy analysis error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Privacy analysis failed due to an internal error.",
        ) from exc

    return PrivacyResponse(
        original_prompt=request.prompt,
        anonymized_prompt=privacy_result["anonymized_prompt"],
        entities=privacy_result["entities"],
        privacy_report=privacy_result["privacy_report"],
        risk_score=privacy_result["risk_score"],
        risk_level=privacy_result["risk_level"],
        policy_actions=privacy_result["policy_actions"],
        confirmation_required=privacy_result["confirmation_required"],
        blocked=privacy_result["blocked"],
        blocked_labels=privacy_result["blocked_labels"],
    )
