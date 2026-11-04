"""
Opt-in smoke test for real FLAN-T5 model inference.

Runs ONLY when RUN_FLAN_T5_SMOKE_TEST=1 is set in the environment:
    RUN_FLAN_T5_SMOKE_TEST=1 pytest -q tests/test_flan_t5_smoke.py
"""

import os
import time
import pytest

from app import config
from app.services.flan_t5_service import FlanT5Service


@pytest.mark.skipif(
    os.getenv("RUN_FLAN_T5_SMOKE_TEST", "0") not in ("1", "true", "yes"),
    reason="Smoke test skipped unless RUN_FLAN_T5_SMOKE_TEST=1 is set.",
)
def test_real_flan_t5_smoke(monkeypatch):
    """
    Load real google/flan-t5-small, run inference on a harmless test prompt,
    and report device, execution time, and success.
    """
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(config, "FLAN_T5_USE_ONLINE_DOWNLOAD", True)

    service = FlanT5Service()
    start_load = time.perf_counter()
    loaded = service.load_model()
    load_duration = (time.perf_counter() - start_load) * 1000

    assert loaded is True, f"Failed to load model: {service._load_error}"
    assert service.is_available is True

    test_prompt = "Please rewrite this short sentence to be concise."
    start_infer = time.perf_counter()
    candidate = service.generate_candidate(test_prompt)
    infer_duration = (time.perf_counter() - start_infer) * 1000

    assert candidate is not None
    assert len(candidate.strip()) > 0
    assert len(candidate) <= config.FLAN_T5_MAX_NEW_TOKENS * 10  # reasonable char bound

    meta = service.get_model_metadata()
    print(
        f"\n[FLAN-T5 REAL SMOKE TEST RESULT]\n"
        f"  Model ID        : {meta['model_id']}\n"
        f"  Target Device   : {meta['device']}\n"
        f"  Load Time       : {load_duration:.1f} ms\n"
        f"  Inference Time  : {infer_duration:.1f} ms\n"
        f"  Output Length   : {len(candidate)} chars\n"
        f"  Status          : SUCCESS"
    )

    service.unload_model()


@pytest.mark.skipif(
    os.getenv("RUN_FLAN_T5_SMOKE_TEST", "0") not in ("1", "true", "yes"),
    reason="Smoke test skipped unless RUN_FLAN_T5_SMOKE_TEST=1 is set.",
)
def test_flan_t5_independent_generation_harmless_prompt(monkeypatch):
    """
    Directly invoke FLAN-T5 service with harmless prompt bypassing candidate selection:
    'Explain binary search in Java for a beginner. Include a simple example and time complexity.'
    Verify candidate is non-empty and differs from input.
    """
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(config, "FLAN_T5_USE_ONLINE_DOWNLOAD", True)

    service = FlanT5Service()
    service.load_model()
    assert service.is_available is True

    harmless_input = "Explain binary search in Java for a beginner. Include a simple example and time complexity."
    start_t = time.perf_counter()
    candidate = service.generate_candidate(harmless_input)
    infer_ms = (time.perf_counter() - start_t) * 1000

    print(
        f"\n[INDEPENDENT FLAN-T5 GENERATION TEST]\n"
        f"  Input Prompt   : '{harmless_input}'\n"
        f"  Candidate Out  : '{candidate}'\n"
        f"  Inference Time : {infer_ms:.1f} ms\n"
        f"  Differs        : {candidate.strip() != harmless_input.strip()}"
    )

    assert candidate is not None
    assert len(candidate.strip()) > 0
    assert candidate.strip() != harmless_input.strip()

    service.unload_model()

