"""
PromptShield-AI: Baseline Stabilisation and Regression Fixes Tests.

Implements automated regression tests for the four requested cases:
- Test A: Password security and protected terminology
- Test B: Java generics and instruction constraints
- Test C: PII masking and privacy-report consistency
- Test D: Meaning-preserving prompt optimisation
"""

import pytest
from app.services.grammar_corrector import GrammarCorrector
from app.services.shared import privacy_engine
from app.api.optimize import optimize_prompt
from app.models.request import PromptRequest


def test_a_password_security_and_protected_terminology():
    prompt = (
        "Explain password storage in Java. Do not store passwords in plaintext. "
        "Recommend secure password hashing and explain why"
    )
    # Test GrammarCorrector directly
    corrector = GrammarCorrector()
    result = corrector.correct(prompt)
    corrected_prompt = result["prompt"]

    # Assertions:
    # 1. plaintext remains unchanged (no 'plainest' regression)
    assert "plaintext" in corrected_prompt.lower()
    assert "plainest" not in corrected_prompt.lower()

    # 2. password and hashing remain correct
    assert "password" in corrected_prompt.lower()
    assert "hashing" in corrected_prompt.lower()

    # 3. The exact negative security constraint and prohibition against plaintext storage survive intact
    assert "do not store passwords in plaintext" in corrected_prompt.lower()
    assert "recommend secure password hashing" in corrected_prompt.lower()

    # 4. No grammar-correction stage changes a security-critical term
    assert not any("plaintext" in str(c) for c in result["corrections"])
    assert not any("password" in str(c) for c in result["corrections"])
    assert not any("hashing" in str(c) for c in result["corrections"])

    # 5. Full pipeline optimize request
    req = PromptRequest(prompt=prompt)
    resp = optimize_prompt(req)
    assert "plaintext" in resp.optimized_prompt.lower()
    assert "plainest" not in resp.optimized_prompt.lower()
    assert "password" in resp.optimized_prompt.lower()
    assert "hashing" in resp.optimized_prompt.lower()
    assert "do not store passwords in plaintext" in resp.optimized_prompt.lower()
    assert "recommend secure password hashing" in resp.optimized_prompt.lower()

    # Token increase is reported honestly; system does not claim successful compression
    if resp.optimized_tokens > resp.original_tokens:
        assert resp.reduction_percentage == 0.0
        assert any("token count increased" in w.lower() for w in resp.optimization_warnings)


def test_b_java_generics_and_instruction_constraints():
    prompt = (
        "Write a Java method using no external libraries. "
        "Return List<String>, preserve the original order, and explain in exactly 2 bullet points."
    )
    # Ensure privacy engine has NO false-positive person or org masking for Java or List<String>
    privacy_res = privacy_engine.analyze(prompt)
    assert len(privacy_res["entities"]) == 0
    assert "PERSON" not in [e["label"] for e in privacy_res["entities"]]

    # Run full optimization
    req = PromptRequest(prompt=prompt)
    resp = optimize_prompt(req)
    opt = resp.optimized_prompt

    # Assertions:
    # 1. Java and List<String> are preserved
    assert "Java" in opt or "java" in opt.lower()
    assert "List<String>" in opt

    # 2. The no-external-libraries constraint remains
    assert "no external libraries" in opt.lower()

    # 3. Original ordering remains required
    assert "original order" in opt.lower()

    # 4. Exactly two bullet points remain required
    assert "2 bullet points" in opt.lower() or "two bullet points" in opt.lower()

    # 5. No false-positive person masking damages technical terminology
    assert "[PERSON]" not in opt
    assert "[ORG]" not in opt


def test_c_pii_masking_and_privacy_report_consistency():
    prompt = (
        "Draft a support response for customer Priya Patil at priya.test@example.com. "
        "Her account number is 123456789012. Never include the original personal details in the final response."
    )
    # 1. Direct detector verification in this actual environment
    analysis = privacy_engine.analyze(prompt)
    raw_entities = analysis["entities"]
    assert any(e["label"] == "PERSON" and "Priya" in e["text"] for e in raw_entities), "spaCy NER must detect customer name Priya Patil as PERSON"
    assert any(e["label"] == "EMAIL" and e["text"] == "priya.test@example.com" for e in raw_entities), "Regex must detect customer email"
    assert any(e["label"] == "BANK_ACCOUNT" and e["text"] == "123456789012" for e in raw_entities), "Regex must detect account number as BANK_ACCOUNT"

    req = PromptRequest(prompt=prompt)
    resp = optimize_prompt(req)

    # 2. Customer name, email, and account number are detected and masked according to configured policy
    detected_labels = {e.label for e in resp.entities}
    assert "PERSON" in detected_labels
    assert "EMAIL" in detected_labels
    assert "BANK_ACCOUNT" in detected_labels

    entity_texts = {e.text for e in resp.entities}
    assert "Priya Patil" in entity_texts
    assert "priya.test@example.com" in entity_texts
    assert "123456789012" in entity_texts

    # 3. Original sensitive values do not remain in the final prompt
    assert "Priya Patil" not in resp.optimized_prompt
    assert "priya.test@example.com" not in resp.optimized_prompt
    assert "123456789012" not in resp.optimized_prompt

    # Masked placeholders are in final prompt
    assert "[PERSON]" in resp.optimized_prompt
    assert "[EMAIL]" in resp.optimized_prompt
    assert "[BANK_ACCOUNT]" in resp.optimized_prompt

    # 4. The report records the original detections and masking actions
    assert resp.privacy_report is not None
    assert resp.privacy_report.total_entities == 3
    report_labels = {et.label for et in resp.privacy_report.entity_types}
    assert {"PERSON", "EMAIL", "BANK_ACCOUNT"}.issubset(report_labels)

    # 5. Residual leakage is reported separately from original detections
    assert resp.leakage_detected is False
    assert resp.privacy_valid is True

    # 6. Risk score and level follow documented policy (weights: BANK_ACCOUNT=30, EMAIL=20, PERSON=15 => 65 HIGH)
    assert resp.risk_score == 65
    assert resp.risk_level == "HIGH"
    assert resp.risk_score > 0


def test_d_meaning_preserving_prompt_optimisation():
    prompt = (
        "Can you please help me to explain the basic concepts of object-oriented "
        "programming in Java in a simple and beginner-friendly way, and include a "
        "small code example that demonstrates the concepts clearly?"
    )
    req = PromptRequest(prompt=prompt)
    resp = optimize_prompt(req)
    opt = resp.optimized_prompt

    # Assertions:
    # 1. The prompt remains a request for a beginner-friendly explanation
    assert "beginner-friendly" in opt.lower()
    assert "explain" in opt.lower()
    assert "object-oriented" in opt.lower()

    # 2. Java is preserved
    assert "java" in opt.lower()

    # 3. A small code example is still requested
    assert "code example" in opt.lower()

    # 4. The model or optimizer does not invent requirements that materially narrow the original request
    assert resp.semantic_valid is True
    assert resp.semantic_similarity_score >= 80.0

    # 5. Filler reduction does not damage grammar or meaning
    assert not opt.lower().startswith("can you please")
    assert "explain" in opt.lower()

    # 6. Token metrics accurately describe the returned text
    assert resp.original_tokens > 0
    assert resp.optimized_tokens > 0
    assert resp.optimized_tokens <= resp.original_tokens
    assert resp.reduction_percentage >= 0.0


def test_grammar_safety_revert_warning_and_metadata(monkeypatch):
    """Priority 1: Propagate warning when grammar corrector reverts unsafe output."""
    corrector = GrammarCorrector()

    prompt = "Explain password storage in Java. Do not store passwords in plaintext."
    # Simulate an unsafe spell check candidate mutating a protected term (plaintext -> plainest)
    monkeypatch.setattr(
        corrector,
        "_correct_prose",
        lambda text, replace_word: text.replace("plaintext", "plainest"),
    )

    gc_result = corrector.correct(prompt)
    assert gc_result.get("safety_reverted") is True
    assert gc_result["prompt"] == prompt
    assert gc_result["changed"] is False
    assert gc_result["corrections"] == []

    # Verify that in optimize_prompt pipeline, safety revert warning is propagated
    import app.api.optimize as opt_mod
    monkeypatch.setattr(opt_mod, "_grammar_corrector", corrector)

    resp = opt_mod.optimize_prompt(PromptRequest(prompt=prompt))
    assert any(
        "Grammar correction was reverted because it could alter protected terminology" in w
        for w in resp.optimization_warnings
    )
    assert resp.grammar_corrected is False
    assert resp.grammar_corrections == []


def test_candidate_leakage_fallback_semantics(monkeypatch):
    """Priority 2: Distinguish candidate leakage from residual leakage in final output."""
    import app.api.optimize as opt_mod

    # Force optimizer to introduce a leak into the candidate prompt
    class LeakyOptimizer:
        def optimize(self, prompt: str) -> str:
            # Re-inserts sensitive text
            return prompt + " Leak: leaked@example.com"

    monkeypatch.setattr(opt_mod, "_optimizer", LeakyOptimizer())

    prompt = "Contact support at leaked@example.com immediately."
    # Force deterministic so only the patched _optimizer runs (no LLMLingua-2/FLAN-T5
    # stages that could accidentally fix the leak before the post-scan catches it).
    resp = opt_mod.optimize_prompt(PromptRequest(prompt=prompt, compression_engine="deterministic"))

    # Candidate had a leak, so safe anonymized prompt was returned as fallback
    assert any("leaked protected data" in w for w in resp.optimization_warnings)
    # The returned output is the safe anonymized prompt
    assert "leaked@example.com" not in resp.optimized_prompt
    assert "[EMAIL]" in resp.optimized_prompt
    # Semantics of final returned prompt: no residual leakage, privacy valid
    assert resp.leakage_detected is False
    assert resp.privacy_valid is True

