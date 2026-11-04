"""
POST /optimize — prompt optimization and privacy analysis endpoint.

This route orchestrates the AI pipeline:
  1. Preprocessing      — normalize and validate the prompt
  2. Privacy analysis   — detect entities, score risk, anonymize
  3. Prompt optimization — deterministic filler removal (baseline)
  4. Model compression  — LLMLingua-2 and/or FLAN-T5 candidate generation
  5. Grammar correction  — conservative spelling and punctuation cleanup
  6. Quality validation  — ensure output integrity
  7. Semantic validation — measure meaning preservation
  8. Token metrics       — model-aware token counts
  9. Response assembly   — return structured PromptResponse

Compression engine selection (COMPRESSION_ENGINE env var):
  'auto'          — try LLMLingua-2 first; if unavailable/rejected, try FLAN-T5
  'llmlingua'     — LLMLingua-2 only (fallback to deterministic)
  'flan-t5'       — FLAN-T5 only (fallback to deterministic)
  'deterministic' — skip all model stages
"""

import logging
import re
import time
import uuid
import secrets

from fastapi import APIRouter, HTTPException, status, Header, Response

from app import config
from app.models.request import PromptRequest
from app.models.response import PromptResponse
from app.services.optimizer import PromptOptimizer, _FILLER_PATTERNS, _COMPACT_PATTERNS
from app.services.grammar_corrector import GrammarCorrector
from app.services.quality_validator import QualityValidator
from app.services.semantic_validator import SemanticValidator
from app.services.privacy_policy import should_anonymize
from app.services.shared import preprocessor, privacy_engine
from app.services.token_counter import TokenCounter
from app.services.flan_t5_service import flan_t5_service, FlanT5Error
from app.services.llmlingua_service import llmlingua_service, LLMLinguaError
from app.services.candidate_evaluator import evaluate_llmlingua_candidate, evaluate_flan_t5_candidate, _is_leakage

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Service instances — created once, reused for all requests ──────────────────
_optimizer = PromptOptimizer()
_grammar_corrector = GrammarCorrector()
_validator = QualityValidator()
_semantic_validator = SemanticValidator()
_token_counter = TokenCounter()

_PLACEHOLDER_PATTERN = re.compile(r"\[[A-Z_]+(?:_\d+)?\]")


# ── Service-to-service authentication ─────────────────────────────────────────

def _require_api_key(api_key: str | None) -> None:
    """Validate the API key (from X-API-Key or X-AI-Service-Key) when AI_SERVICE_API_KEY is configured.

    Uses constant-time comparison to prevent timing attacks.
    If AI_SERVICE_API_KEY is not configured, authentication is skipped
    (useful for local development without a tunnel).
    """
    configured_key = config.AI_SERVICE_API_KEY
    if not configured_key:
        # Authentication disabled — log a warning so it's visible in startup logs
        return
    if not api_key or not secrets.compare_digest(
        configured_key.encode(), api_key.encode()
    ):
        logger.warning("Rejected request: missing or invalid API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )



# ── Engine routing helpers ─────────────────────────────────────────────────────

def _should_try_llmlingua(engine: str) -> bool:
    return engine in ("auto", "llmlingua") and config.LLMLINGUA_ENABLED


def _should_try_flan_t5(engine: str, llmlingua_accepted: bool) -> bool:
    if not config.FLAN_T5_ENABLED:
        return False
    if engine == "flan-t5":
        return True
    if engine == "auto" and not llmlingua_accepted:
        return True
    return False


# ── Convenience wrappers binding shared service state ─────────────────────────

def _eval_llmlingua(anonymized_prompt, deterministic_candidate, candidate, privacy_policy, protected_entities):
    return evaluate_llmlingua_candidate(
        anonymized_prompt=anonymized_prompt,
        deterministic_candidate=deterministic_candidate,
        candidate=candidate,
        privacy_policy=privacy_policy,
        protected_entities=protected_entities,
        token_counter=_token_counter,
        privacy_engine=privacy_engine,
        should_anonymize_fn=should_anonymize,
        quality_validator=_validator,
        semantic_validator=_semantic_validator,
        grammar_corrector=_grammar_corrector,
        filler_patterns=_FILLER_PATTERNS,
        compact_patterns=_COMPACT_PATTERNS,
    )


def _eval_flan_t5(anonymized_prompt, deterministic_candidate, candidate, privacy_policy, protected_entities):
    return evaluate_flan_t5_candidate(
        anonymized_prompt=anonymized_prompt,
        deterministic_candidate=deterministic_candidate,
        candidate=candidate,
        privacy_policy=privacy_policy,
        protected_entities=protected_entities,
        token_counter=_token_counter,
        privacy_engine=privacy_engine,
        should_anonymize_fn=should_anonymize,
        quality_validator=_validator,
        semantic_validator=_semantic_validator,
        grammar_corrector=_grammar_corrector,
        filler_patterns=_FILLER_PATTERNS,
        compact_patterns=_COMPACT_PATTERNS,
    )


# Backwards compatibility aliases for existing tests
_evaluate_flan_t5_candidate = _eval_flan_t5
_evaluate_llmlingua_candidate = _eval_llmlingua



@router.post(
    "/optimize",
    response_model=PromptResponse,
    summary="Optimize and analyze a prompt for privacy",
    description=(
        "Processes the input prompt through the full AI pipeline:\n\n"
        "1. **Preprocessing** — normalizes whitespace and punctuation.\n"
        "2. **Privacy Detection** — detects PII via regex (EMAIL, PHONE, PAN, "
        "AADHAAR, API_KEY, JWT, PRIVATE_KEY, DATABASE_URL, and cloud "
        "credentials, SSN, and driver licenses) and spaCy NER "
        "SSN, driver licenses, UK NINO, Canadian SIN, IBAN, and EU tax IDs) "
        "and spaCy NER "
        "(PERSON, GPE, ORG, LOC).\n"
        "3. **Entity Normalization** — deduplicates and merges detections.\n"
        "4. **Risk Scoring** — computes a 0–100 privacy risk score.\n"
        "5. **Anonymization** — replaces sensitive values with [LABEL] placeholders.\n"
        "6. **Prompt Optimization** — removes filler phrases (deterministic, not LLM).\n"
        "7. **Model Compression** — LLMLingua-2 token compression and/or FLAN-T5 rewriting "
        "(when enabled and applicable; engine selected via COMPRESSION_ENGINE).\n"
        "8. **Grammar Correction** — applies high-confidence spelling and punctuation fixes.\n"
        "9. **Quality Validation** — ensures output integrity.\n"
        "10. **Semantic Validation** — measures meaning preservation.\n"
        "11. **Token Metrics** — returns model-aware token counts using the "
        "configured tokenizer."
    ),
    responses={
        200: {"description": "Successful optimization and privacy analysis."},
        400: {"description": "Invalid or empty prompt."},
        422: {"description": "Request body validation failed."},
        500: {"description": "Internal pipeline error."},
    },
)
def optimize_prompt(
    request: PromptRequest,
    response: Response = None,
    x_request_id: str | None = Header(None, alias="X-Request-ID"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_ai_service_key: str | None = Header(None, alias="X-AI-Service-Key"),
) -> PromptResponse:
    """
    Optimize a prompt and analyze it for privacy risks.
    """
    _require_api_key(x_api_key or x_ai_service_key)
    req_id = x_request_id or str(uuid.uuid4())
    if response is not None:
        response.headers["X-Request-ID"] = req_id

    original_prompt = request.prompt

    logger.info(
        "[%s] Optimize request received: prompt_length=%d", req_id, len(original_prompt)
    )

    # ── Stage 1: Preprocessing ─────────────────────────────────────────────────
    try:
        cleaned_prompt = preprocessor.clean(original_prompt)
    except ValueError as exc:
        logger.warning("Preprocessing rejected prompt: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # ── Stage 2: Privacy analysis (detection + scoring + anonymization) ────────
    try:
        privacy_result = privacy_engine.analyze(
            cleaned_prompt, request.privacy_policy
        )
    except Exception as exc:
        logger.error("Privacy engine error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Privacy analysis failed due to an internal error.",
        ) from exc

    anonymized_prompt: str = privacy_result["anonymized_prompt"]
    if privacy_result["blocked"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Prompt contains a category blocked by the privacy policy.",
                "blocked_labels": privacy_result["blocked_labels"],
            },
        )

    # ── Stage 3: Deterministic prompt optimization (baseline) ──────────────────
    try:
        deterministic_candidate = _optimizer.optimize(anonymized_prompt)
    except Exception as exc:
        logger.error("Optimizer error: %s", exc, exc_info=True)
        deterministic_candidate = anonymized_prompt

    optimization_warnings: list[str] = []
    optimization_strategy = "deterministic"
    model_used = False
    model_candidate_accepted = False
    model_rejection_reason: str | None = None
    selected_candidate = deterministic_candidate

    protected_entities = [
        entity
        for entity in privacy_result["entities"]
        if should_anonymize(entity, request.privacy_policy)
    ]

    # Resolve compression engine: request body override takes precedence
    engine = getattr(request, "compression_engine", None) or config.COMPRESSION_ENGINE
    engine = engine.strip().lower() if engine else "auto"
    if engine not in ("auto", "llmlingua", "flan-t5", "deterministic"):
        logger.warning("Unknown compression_engine '%s'; defaulting to 'auto'.", engine)
        engine = "auto"

    # ── Stage 3b: LLMLingua-2 candidate generation & selection ────────────────
    llmlingua_accepted = False
    llmlingua_attempted = False
    llmlingua_duration_ms = 0.0

    if _should_try_llmlingua(engine):
        model_used = True
        try:
            if not llmlingua_service.is_available:
                llmlingua_service.load_model()

            if llmlingua_service.is_available:
                llmlingua_attempted = True
                t_ll_start = time.perf_counter()

                rate_override = getattr(request, "compression_rate", None)

                # Honour the caller's token budget: pass target_max_tokens as target_token
                # so LLMLingua-2 can target a hard token count rather than a rate ratio.
                # Use the configured rate as the fallback when no budget is given.
                ll_target_token: int | None = None
                if request.target_max_tokens is not None and request.target_max_tokens >= 1:
                    ll_target_token = request.target_max_tokens
                    logger.debug(
                        "Passing target_max_tokens=%d to LLMLingua-2 as target_token.",
                        ll_target_token,
                    )

                ll_candidate = llmlingua_service.compress_candidate_with_timeout(
                    anonymized_prompt,
                    rate=rate_override,
                    target_token=ll_target_token,
                    timeout=config.LLMLINGUA_TIMEOUT_SECONDS,
                )
                llmlingua_duration_ms = (time.perf_counter() - t_ll_start) * 1000

                accepted, rejection_reason = _eval_llmlingua(
                    anonymized_prompt=anonymized_prompt,
                    deterministic_candidate=deterministic_candidate,
                    candidate=ll_candidate,
                    privacy_policy=request.privacy_policy,
                    protected_entities=protected_entities,
                )
                llmlingua_accepted = accepted
                if accepted:
                    selected_candidate = ll_candidate
                    optimization_strategy = "llmlingua-2"
                    model_candidate_accepted = True
                    model_rejection_reason = None
                    logger.info(
                        "LLMLingua-2 candidate accepted (%.1f ms, %d -> %d tokens).",
                        llmlingua_duration_ms,
                        _token_counter.count(anonymized_prompt),
                        _token_counter.count(ll_candidate),
                    )
                else:
                    model_candidate_accepted = False
                    model_rejection_reason = rejection_reason
                    optimization_warnings.append(
                        f"LLMLingua-2 candidate rejected ({rejection_reason}); "
                        "falling back to next stage."
                    )
                    logger.info("LLMLingua-2 candidate rejected: %s", rejection_reason)
            else:
                model_rejection_reason = llmlingua_service._load_error or "LLMLingua-2 model not available"
                optimization_warnings.append(
                    "LLMLingua-2 model is not available; falling back to next stage."
                )
        except Exception as exc:
            logger.warning("LLMLingua-2 generation exception: %s", exc)
            model_rejection_reason = str(exc)
            optimization_warnings.append(
                f"LLMLingua-2 generation failed ({type(exc).__name__}); "
                "falling back to next stage."
            )

        logger.info(
            "LLMLingua-2 Diagnostics: enabled=%s loaded=%s attempted=%s model_id=%s "
            "device=%s duration_ms=%.1f accepted=%s engine=%s",
            config.LLMLINGUA_ENABLED,
            llmlingua_service.is_available,
            llmlingua_attempted,
            config.LLMLINGUA_MODEL_ID,
            llmlingua_service._device,
            llmlingua_duration_ms,
            llmlingua_accepted,
            engine,
        )

    # ── Stage 3c: Optional FLAN-T5 candidate generation & selection ────────────
    inference_attempted = False
    infer_duration_ms = 0.0
    differs_from_input = False
    validation_passed = False
    error_category: str | None = None

    if not llmlingua_accepted and _should_try_flan_t5(engine, llmlingua_accepted):
        model_used = True
        try:
            if not flan_t5_service.is_available:
                flan_t5_service.load_model()

            if flan_t5_service.is_available:
                inference_attempted = True
                t_infer_start = time.perf_counter()
                model_raw_candidate = flan_t5_service.generate_candidate_with_timeout(
                    anonymized_prompt, timeout=config.FLAN_T5_TIMEOUT_SECONDS
                )
                infer_duration_ms = (time.perf_counter() - t_infer_start) * 1000
                differs_from_input = (model_raw_candidate.strip() != anonymized_prompt.strip())

                accepted, rejection_reason = _eval_flan_t5(
                    anonymized_prompt=anonymized_prompt,
                    deterministic_candidate=deterministic_candidate,
                    candidate=model_raw_candidate,
                    privacy_policy=request.privacy_policy,
                    protected_entities=protected_entities,
                )
                validation_passed = accepted
                if accepted:
                    selected_candidate = model_raw_candidate
                    optimization_strategy = "flan-t5"
                    model_candidate_accepted = True
                    model_rejection_reason = None
                    logger.info("FLAN-T5 candidate accepted.")
                else:
                    model_candidate_accepted = False
                    model_rejection_reason = rejection_reason
                    optimization_warnings.append(
                        f"FLAN-T5 candidate rejected ({rejection_reason}); "
                        "deterministic candidate selected."
                    )
                    logger.info("FLAN-T5 candidate rejected: %s", rejection_reason)
            else:
                model_candidate_accepted = False
                error_category = "MODEL_UNAVAILABLE"
                model_rejection_reason = "FLAN-T5 model not available"
                optimization_warnings.append(
                    "FLAN-T5 model is not available; deterministic candidate selected."
                )
        except Exception as exc:
            logger.warning("FLAN-T5 generation exception: %s", exc)
            model_candidate_accepted = False
            error_category = type(exc).__name__
            model_rejection_reason = str(exc)
            optimization_warnings.append(
                f"FLAN-T5 generation failed ({error_category}); deterministic candidate selected."
            )
            selected_candidate = deterministic_candidate

        logger.info(
            "FLAN-T5 Diagnostics: enabled=%s loaded=%s attempted=%s model_id=%s device=%s "
            "duration_ms=%.1f differs_from_input=%s validation_passed=%s rejection_reason=%s "
            "strategy_selected=%s error_category=%s",
            config.FLAN_T5_ENABLED,
            flan_t5_service.is_available,
            inference_attempted,
            config.FLAN_T5_MODEL_ID,
            flan_t5_service._device,
            infer_duration_ms,
            differs_from_input,
            validation_passed,
            model_rejection_reason,
            optimization_strategy,
            error_category,
        )

    # ── Stage 4: Conservative grammar correction ───────────────────────────────
    grammar_result = _grammar_corrector.correct(selected_candidate)
    grammar_candidate = str(grammar_result["prompt"])

    # ── Stage 5: Quality validation ────────────────────────────────────────────
    if grammar_result.get("safety_reverted"):
        optimization_warnings.append(
            "Grammar correction was reverted because it could alter protected terminology."
        )

    optimized_prompt, quality_warnings, quality_fallback_used = _validator.validate_prompt(
        anonymized_prompt, grammar_candidate
    )
    optimization_warnings.extend(quality_warnings)

    if quality_fallback_used or grammar_result.get("safety_reverted"):
        effective_grammar_corrections: list[str] = []
        effective_grammar_corrected = False
    else:
        effective_grammar_corrections = [str(c) for c in grammar_result["corrections"]]
        effective_grammar_corrected = bool(grammar_result["changed"])

    # ── Stage 6: Post-optimization privacy leakage scan ───────────────────────
    candidate_leakage_labels = sorted(
        {
            entity["label"]
            for entity in protected_entities
            if entity["text"] in optimized_prompt
        }
    )
    candidate_post_scan = privacy_engine.analyze(
        optimized_prompt, request.privacy_policy
    )
    candidate_post_scan_leaks = any(
        should_anonymize(entity, request.privacy_policy)
        and _is_leakage(entity, optimized_prompt, anonymized_prompt)
        for entity in candidate_post_scan["entities"]
    )
    candidate_leaked = bool(candidate_leakage_labels or candidate_post_scan_leaks)
    if candidate_leaked:
        optimized_prompt = anonymized_prompt
        optimization_warnings.append(
            "Optimization candidate leaked protected data; the safe anonymized prompt was returned as fallback."
        )

    # Re-evaluate final returned prompt for residual sensitive data leakage
    residual_leakage_labels = sorted(
        {
            entity["label"]
            for entity in protected_entities
            if entity["text"] in optimized_prompt
        }
    )
    final_post_scan = privacy_engine.analyze(
        optimized_prompt, request.privacy_policy
    )
    final_post_scan_leaks = any(
        should_anonymize(entity, request.privacy_policy)
        and _is_leakage(entity, optimized_prompt, anonymized_prompt)
        for entity in final_post_scan["entities"]
    )
    leakage_detected = bool(residual_leakage_labels or final_post_scan_leaks)
    privacy_valid = not leakage_detected

    # ── Stage 7: Semantic validation ───────────────────────────────────────────
    semantic_score = _semantic_validator.score(anonymized_prompt, optimized_prompt)
    semantic_valid = _semantic_validator.validate(anonymized_prompt, optimized_prompt)
    if (
        request.minimum_semantic_score is not None
        and semantic_score < request.minimum_semantic_score
    ):
        semantic_valid = False
        optimization_warnings.append(
            f"Minimum semantic score ({request.minimum_semantic_score}%) was not met "
            f"(achieved {semantic_score}%); safe anonymized prompt was returned as fallback."
        )
        optimized_prompt = anonymized_prompt
        semantic_score = 100.0
        semantic_valid = True

    # Ensure metadata accurately reflects the final selection if a fallback occurred
    if optimization_strategy in ("llmlingua-2", "flan-t5") and (
        optimized_prompt == anonymized_prompt or candidate_leaked or quality_fallback_used
    ):
        optimization_strategy = "deterministic"
        model_candidate_accepted = False
        if not model_rejection_reason:
            if candidate_leaked:
                model_rejection_reason = "Candidate leaked protected data during post-scan"
            elif quality_fallback_used:
                model_rejection_reason = "Candidate failed post-optimization quality validation"
            else:
                model_rejection_reason = "Candidate failed semantic threshold validation"

    # ── Stage 8: Token metrics ─────────────────────────────────────────────────
    original_tokens = _token_counter.count(cleaned_prompt)
    anonymized_tokens = _token_counter.count(anonymized_prompt)
    optimized_tokens = _token_counter.count(optimized_prompt)
    reduction_pct = _token_counter.reduction_percentage(original_tokens, optimized_tokens)
    anonymization_token_delta = anonymized_tokens - original_tokens
    compression_percentage = _token_counter.reduction_percentage(anonymized_tokens, optimized_tokens)

    if optimized_tokens > original_tokens:
        increase_pct = round(((optimized_tokens - original_tokens) / original_tokens) * 100, 2)
        optimization_warnings.append(
            f"Prompt token count increased from {original_tokens} to {optimized_tokens} "
            f"(+{increase_pct}%); reduction is reported as 0.0% and not as compression."
        )

    token_budget_met = (
        None
        if request.target_max_tokens is None
        else optimized_tokens <= request.target_max_tokens
    )
    if token_budget_met is False:
        optimization_warnings.append(
            "The optimized prompt is above the requested token budget; "
            "no unsafe content was removed to force the target."
        )

    if privacy_result["confirmation_required"]:
        optimization_warnings.append(
            "Confirmation is required by the privacy policy for one or more detected categories."
        )

    logger.info(
        "[%s] Optimize complete: entities=%d risk=%s score=%d "
        "semantic_score=%.2f semantic_valid=%s orig_tokens=%d anon_tokens=%d opt_tokens=%d "
        "reduction=%.1f%% anon_delta=%+d compression=%.1f%% strategy=%s",
        req_id,
        len(privacy_result["entities"]),
        privacy_result["risk_level"],
        privacy_result["risk_score"],
        semantic_score,
        semantic_valid,
        original_tokens,
        anonymized_tokens,
        optimized_tokens,
        reduction_pct,
        anonymization_token_delta,
        compression_percentage,
        optimization_strategy,
    )

    # ── Stage 9: Assemble response ─────────────────────────────────────────────
    return PromptResponse(
        original_prompt=original_prompt,
        optimized_prompt=optimized_prompt,
        entities=privacy_result["entities"],
        privacy_report=privacy_result["privacy_report"],
        risk_score=privacy_result["risk_score"],
        risk_level=privacy_result["risk_level"],
        semantic_similarity_score=semantic_score,
        semantic_valid=semantic_valid,
        grammar_corrections=effective_grammar_corrections,
        grammar_corrected=effective_grammar_corrected,
        original_tokens=original_tokens,
        anonymized_tokens=anonymized_tokens,
        optimized_tokens=optimized_tokens,
        reduction_percentage=reduction_pct,
        anonymization_token_delta=anonymization_token_delta,
        compression_percentage=compression_percentage,
        target_max_tokens=request.target_max_tokens,
        minimum_semantic_score=request.minimum_semantic_score,
        token_budget_met=token_budget_met,
        optimization_warnings=optimization_warnings,
        privacy_valid=privacy_valid,
        leakage_detected=leakage_detected,
        policy_actions=privacy_result["policy_actions"],
        confirmation_required=privacy_result["confirmation_required"],
        optimization_strategy=optimization_strategy,
        model_used=model_used,
        model_candidate_accepted=model_candidate_accepted,
        model_rejection_reason=model_rejection_reason,
    )
