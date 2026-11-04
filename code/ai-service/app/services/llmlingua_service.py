"""
LLMLingua-2 Prompt Compression Service for PromptShield-AI.

Manages one-time, thread-safe lazy loading and inference of Microsoft's
LLMLingua-2 prompt compression model (e.g. microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank).
Provides bounded concurrent inference, non-blocking wall-clock timeout execution,
critical token preservation (placeholders, negations, security instructions),
and telemetry diagnostics.
"""

import asyncio
import logging
import re
import threading
import time
from typing import Any, Sequence

from app import config
from app.services.constraint_extractor import constraint_extractor

logger = logging.getLogger(__name__)


class LLMLinguaError(Exception):
    """Base exception for LLMLingua-2 service errors."""


class LLMLinguaUnavailableError(LLMLinguaError):
    """Raised when model compression is requested but LLMLingua-2 is unavailable or disabled."""


class LLMLinguaTimeoutError(LLMLinguaError):
    """Raised when LLMLingua-2 inference exceeds configured timeout."""


class LLMLinguaService:
    """
    Manages lazy singleton loading and inference of the LLMLingua-2 compression model.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._semaphore_lock = threading.Lock()
        self._async_semaphore: asyncio.Semaphore | None = None
        self._async_semaphore_loop: asyncio.AbstractEventLoop | None = None
        self._compressor: Any = None
        self._is_available: bool = False
        self._device: str = "cpu"
        self._load_error: str | None = None
        self._load_duration_ms: float = 0.0
        self._last_inference_diagnostics: dict[str, Any] = {}

    @property
    def is_available(self) -> bool:
        """Return True if compressor is loaded and ready for inference."""
        return self._is_available

    @property
    def last_diagnostics(self) -> dict[str, Any]:
        """Return metadata and telemetry from the most recent compression call."""
        return dict(self._last_inference_diagnostics)

    def resolve_device(self) -> str:
        """Resolve and validate the execution device according to configuration."""
        import torch

        requested = config.LLMLINGUA_DEVICE.lower()
        cuda_available = torch.cuda.is_available()

        if requested == "cuda":
            if not cuda_available:
                raise RuntimeError(
                    "LLMLingua-2 device was configured as 'cuda', but CUDA is not available."
                )
            return "cuda"
        elif requested == "cpu":
            return "cpu"
        elif requested == "auto":
            return "cuda" if cuda_available else "cpu"
        else:
            logger.warning(
                "Unknown LLMLINGUA_DEVICE '%s'; falling back to 'auto'.", requested
            )
            return "cuda" if cuda_available else "cpu"

    def load_model(self) -> bool:
        """
        Load PromptCompressor into memory once per process.
        Thread-safe: multiple callers will wait and share the single load.
        """
        if not config.LLMLINGUA_ENABLED:
            logger.info("LLMLingua-2 is disabled (LLMLINGUA_ENABLED=false); skipping loading.")
            self._is_available = False
            return False

        if self._is_available and self._compressor is not None:
            return True

        with self._lock:
            if self._is_available and self._compressor is not None:
                return True

            start_time = time.perf_counter()
            try:
                import torch
                from llmlingua import PromptCompressor
            except ImportError as exc:
                self._load_error = f"Missing dependency for LLMLingua-2: {exc}"
                logger.error(self._load_error)
                self._is_available = False
                return False

            try:
                resolved_device = self.resolve_device()
            except Exception as exc:
                self._load_error = f"Device resolution error for LLMLingua-2: {exc}"
                logger.error(self._load_error)
                self._is_available = False
                return False

            logger.info(
                "Loading LLMLingua-2 model '%s' on device '%s' (online_download=%s)...",
                config.LLMLINGUA_MODEL_ID,
                resolved_device,
                config.LLMLINGUA_USE_ONLINE_DOWNLOAD,
            )

            try:
                model_config: dict[str, Any] = {}
                if not config.LLMLINGUA_USE_ONLINE_DOWNLOAD:
                    model_config["local_files_only"] = True

                compressor = PromptCompressor(
                    model_name=config.LLMLINGUA_MODEL_ID,
                    device_map=resolved_device,
                    model_config=model_config,
                    use_llmlingua2=True,
                )
                self._compressor = compressor
                self._device = resolved_device
                self._is_available = True
                self._load_error = None
                self._load_duration_ms = (time.perf_counter() - start_time) * 1000
                logger.info(
                    "LLMLingua-2 loaded successfully in %.1f ms on %s.",
                    self._load_duration_ms,
                    resolved_device,
                )
                return True

            except Exception as exc:
                self._load_error = f"Failed to load LLMLingua-2 model weights: {exc}"
                logger.warning(
                    "LLMLingua-2 loading failed (will fall back to deterministic baseline): %s",
                    exc,
                )
                self._is_available = False
                self._compressor = None
                return False

    def compress_candidate(
        self,
        prompt: str,
        rate: float | None = None,
        force_tokens: Sequence[str] | None = None,
        target_token: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Synchronously compress a prompt using LLMLingua-2.
        Must only be called with pre-processed, anonymized prompt text.

        Returns:
            (compressed_prompt, diagnostics_dict)
        """
        if not self._is_available or self._compressor is None:
            raise LLMLinguaUnavailableError(
                self._load_error or "LLMLingua-2 model is not loaded or unavailable."
            )

        clean_prompt = prompt.strip() if prompt else ""
        if not clean_prompt:
            return "", {"status": "empty_input", "duration_ms": 0.0}

        t_start = time.perf_counter()

        # Extract critical tokens (placeholders, constraints, negations) if not supplied
        extracted_critical = constraint_extractor.extract_critical_tokens(
            clean_prompt, max_tokens=config.LLMLINGUA_MAX_FORCE_TOKENS
        )
        if force_tokens:
            combined = list(dict.fromkeys(list(force_tokens) + extracted_critical))
        else:
            combined = extracted_critical

        effective_rate = rate if (rate is not None and 0.0 < rate <= 1.0) else config.LLMLINGUA_RATE
        effective_target = target_token if target_token is not None else config.LLMLINGUA_TARGET_TOKEN

        try:
            result = self._compressor.compress_prompt(
                context=[clean_prompt],
                rate=effective_rate,
                target_token=effective_target,
                force_tokens=combined[:config.LLMLINGUA_MAX_FORCE_TOKENS],
                force_reserve_digit=config.LLMLINGUA_FORCE_RESERVE_DIGIT,
                drop_consecutive=config.LLMLINGUA_DROP_CONSECUTIVE,
            )

            raw_compressed = result.get("compressed_prompt", "").strip()

            # Fix BERT detokenization artifacts (e.g. "beginner - friendly" -> "beginner-friendly", "[ PERSON_1 ]" -> "[PERSON_1]")
            raw_compressed = re.sub(r"(\w)\s+-\s+(\w)", r"\1-\2", raw_compressed)
            raw_compressed = re.sub(r"\[\s+([A-Z_0-9]+)\s+\]", r"[\1]", raw_compressed)

            # Clean outer quotes if model wrapped output in quotation marks
            if (raw_compressed.startswith('"') and raw_compressed.endswith('"')) or (
                raw_compressed.startswith("'") and raw_compressed.endswith("'")
            ):
                raw_compressed = raw_compressed[1:-1].strip()

            duration_ms = (time.perf_counter() - t_start) * 1000

            diagnostics = {
                "origin_tokens": result.get("origin_tokens", 0),
                "compressed_tokens": result.get("compressed_tokens", 0),
                "ratio": result.get("ratio", "1.0x"),
                "rate": result.get("rate", "100.0%"),
                "duration_ms": duration_ms,
                "forced_token_count": len(combined),
                "model_id": config.LLMLINGUA_MODEL_ID,
                "device": self._device,
            }
            self._last_inference_diagnostics = diagnostics
            return raw_compressed, diagnostics

        except Exception as exc:
            duration_ms = (time.perf_counter() - t_start) * 1000
            self._last_inference_diagnostics = {
                "error": str(exc),
                "error_category": type(exc).__name__,
                "duration_ms": duration_ms,
            }
            logger.error("LLMLingua-2 compression exception: %s", exc, exc_info=True)
            raise LLMLinguaError(f"Compression execution failed: {exc}") from exc

    def _get_async_semaphore(self) -> asyncio.Semaphore:
        """Get or create the asyncio Semaphore bound to current event loop."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        with self._semaphore_lock:
            if (
                self._async_semaphore is None
                or self._async_semaphore_loop is not current_loop
            ):
                self._async_semaphore = asyncio.Semaphore(
                    config.LLMLINGUA_MAX_CONCURRENT_REQUESTS
                )
                self._async_semaphore_loop = current_loop
        return self._async_semaphore

    async def compress_candidate_async(
        self,
        prompt: str,
        rate: float | None = None,
        force_tokens: Sequence[str] | None = None,
        target_token: int | None = None,
    ) -> str:
        """
        Asynchronously compress prompt with timeout and concurrency bounding.
        Prevents blocking FastAPI's event loop during inference.
        """
        if not self._is_available:
            raise LLMLinguaUnavailableError("LLMLingua-2 is not available.")

        sem = self._get_async_semaphore()
        async with sem:
            try:
                candidate, _ = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.compress_candidate,
                        prompt,
                        rate,
                        force_tokens,
                        target_token,
                    ),
                    timeout=config.LLMLINGUA_TIMEOUT_SECONDS,
                )
                return candidate
            except asyncio.TimeoutError as exc:
                logger.warning(
                    "LLMLingua-2 compression timed out after %.1f seconds.",
                    config.LLMLINGUA_TIMEOUT_SECONDS,
                )
                raise LLMLinguaTimeoutError(
                    f"LLMLingua-2 timed out after {config.LLMLINGUA_TIMEOUT_SECONDS}s."
                ) from exc

    def compress_candidate_with_timeout(
        self,
        prompt: str,
        rate: float | None = None,
        force_tokens: Sequence[str] | None = None,
        target_token: int | None = None,
        timeout: float | None = None,
    ) -> str:
        """
        Synchronously compress prompt with hard wall-clock timeout.
        Uses ThreadPoolExecutor with shutdown(wait=False) so request latency is
        strictly bounded even if the model thread takes longer to finish.
        """
        if timeout is None:
            timeout = config.LLMLINGUA_TIMEOUT_SECONDS

        import concurrent.futures

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self.compress_candidate, prompt, rate, force_tokens, target_token
        )
        try:
            candidate, _ = future.result(timeout=timeout)
            return candidate
        except concurrent.futures.TimeoutError as exc:
            logger.warning(
                "LLMLingua-2 inference timed out after %.1f seconds.", timeout
            )
            raise LLMLinguaTimeoutError(
                f"LLMLingua-2 inference timed out after {timeout}s."
            ) from exc
        finally:
            executor.shutdown(wait=False)


llmlingua_service = LLMLinguaService()
