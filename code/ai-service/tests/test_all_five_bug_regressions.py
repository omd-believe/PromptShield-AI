"""
PromptShield-AI: Automated regression tests for all 5 verified failure scenarios.

1. Collections comparison table: "Best Use Case", "Thread-Safe", "Allows Nulls" must NEVER be misclassified as PERSON.
2. Password security: "do not store passwords in plaintext", "recommend secure password hashing", "never log credentials" must survive.
3. Binary search: Prohibitions like "do not use advanced Java features" must reject reversals ("use advanced Java features") and accept safe equivalents ("don't use...").
4. Appointment reminder: PII correctly anonymized with placeholders, calibrated semantic score remains valid.
5. Cross-request contamination: Proves that alternating sequential and concurrent requests with disparate contents (e.g. Collections prompt and HashMap interview prompt) NEVER bleed text between each other.
"""

import pytest
import concurrent.futures
from app.api.optimize import optimize_prompt
from app.models.request import PromptRequest
from app.services.ner import NERDetector
from app.services.quality_validator import QualityValidator
from app.services.semantic_validator import SemanticValidator


COLLECTIONS_PROMPT = (
    "Compare ArrayList, LinkedList, and Vector in a table with columns: "
    "Collection, Type, Thread-Safe, Allows Nulls, Best Use Case. "
    "Do not include code examples."
)

HASHMAP_PROMPT = (
    "Write a Java method using a HashMap to count the frequency of each integer "
    "in an array. The method must return Map<Integer, Integer>, handle an empty array, "
    "have O(n) expected time complexity, and use no external libraries. "
    "Explain the approach in 3 bullet points."
)

PASSWORD_PROMPT = (
    "Explain password storage best practices in a Java Spring Boot application.\n\n"
    "Requirements:\n"
    "- Do not store passwords in plaintext under any circumstances.\n"
    "- Recommend secure password hashing (BCrypt, Argon2, or PBKDF2).\n"
    "- Explain why plaintext storage is dangerous.\n"
    "- Never log credentials or password hashes in application logs.\n"
    "- Return a structured response with sections: Overview, Implementation, Common Mistakes."
)

BINARY_SEARCH_PROMPT = (
    "Explain binary search in Java for a beginner. "
    "Do not use advanced Java features. "
    "Explain the approach step by step."
)

APPOINTMENT_PROMPT = (
    "Please remind Alice Johnson at alice@example.com about her appointment at 123 Main St "
    "on Monday at 10 AM. Phone: 555-123-4567."
)


# ── Test 1: Collections Table - False-Positive Anonymization ─────────────────

def test_collections_heading_not_anonymized_as_person():
    """Ensure Best Use Case, Thread-Safe, Allows Nulls are never misclassified as PERSON."""
    ner = NERDetector()
    entities = ner.detect(COLLECTIONS_PROMPT)

    # Must have 0 false positive PERSON / ORG entities detected
    person_ents = [e for e in entities if e["label"] == "PERSON"]
    org_ents = [e for e in entities if e["label"] == "ORG"]
    assert len(person_ents) == 0, f"Expected 0 PERSON entities, got: {person_ents}"
    assert len(org_ents) == 0, f"Expected 0 ORG entities, got: {org_ents}"

    # End-to-end optimization test
    req = PromptRequest(prompt=COLLECTIONS_PROMPT, compression_engine="deterministic")
    resp = optimize_prompt(req)
    out = resp.optimized_prompt

    assert "[PERSON" not in out, f"'Best Use Case' or attributes were masked as [PERSON]: {out}"
    assert "Best Use Case" in out or "best use case" in out.lower()
    assert "Thread-Safe" in out or "thread-safe" in out.lower()
    assert "Allows Nulls" in out or "allows nulls" in out.lower()


# ── Test 2: Password Security - Constraints & Preservation ──────────────────

def test_password_security_constraints_preserved():
    """Ensure critical security constraints and hashing recommendations survive."""
    req = PromptRequest(prompt=PASSWORD_PROMPT, compression_engine="deterministic")
    resp = optimize_prompt(req)
    out = resp.optimized_prompt.lower()

    assert "plaintext" in out, "'plaintext' was altered or dropped"
    assert "plainest" not in out, "plaintext was corrupted to plainest"
    assert "do not store passwords in plaintext" in out, "Prohibition was dropped"
    assert "recommend secure password hashing" in out or "hashing" in out
    assert "never log credentials" in out, "Logging constraint was dropped"


# ── Test 3: Binary Search - Prohibitions Scope & Reversals ───────────────────

def test_binary_search_prohibition_reversal_rejected():
    """Reject candidate that reverses 'Do not use' into 'Use'."""
    qv = QualityValidator()
    unsafe_cand = "Explain binary search in Java. Use advanced Java features. Step by step."
    _, _, fallback_used = qv.validate_prompt(BINARY_SEARCH_PROMPT, unsafe_cand)
    assert fallback_used is True, "Reversed prohibition must trigger safety fallback"


def test_binary_search_equivalent_negation_accepted():
    """Accept candidate that preserves prohibition with equivalent contraction ('don't use')."""
    qv = QualityValidator()
    safe_equiv = "Explain binary search in Java for beginner. Don't use advanced Java features. Step by step."
    _, _, fallback_used = qv.validate_prompt(BINARY_SEARCH_PROMPT, safe_equiv)
    assert fallback_used is False, "Equivalent negation ('don't use') must be accepted"


# ── Test 4: Appointment Reminder - PII Anonymization & Semantic Scoring ─────

def test_appointment_reminder_anonymized_and_semantically_valid():
    """Ensure PII is properly masked and calibrated semantic score accepts the result."""
    req = PromptRequest(prompt=APPOINTMENT_PROMPT, compression_engine="deterministic")
    resp = optimize_prompt(req)

    # PII must be masked
    assert "alice@example.com" not in resp.optimized_prompt
    assert "Alice Johnson" not in resp.optimized_prompt
    assert "[EMAIL" in resp.optimized_prompt
    assert "[PERSON" in resp.optimized_prompt

    # Semantic score must be calibrated and passing
    assert resp.semantic_valid is True
    assert resp.semantic_similarity_score >= 60.0, (
        f"Calibrated score was unexpectedly low: {resp.semantic_similarity_score}"
    )


# ── Test 5: Cross-Request Contamination Prevention ───────────────────────────

def test_cross_request_contamination_sequential_and_concurrent():
    """
    Ensure sequential and concurrent requests never leak contents across requests.
    A collections prompt output must NEVER contain HashMap interview keywords.
    """
    # 1. Sequential isolation test
    req_hashmap = PromptRequest(prompt=HASHMAP_PROMPT, compression_engine="deterministic")
    resp_hashmap = optimize_prompt(req_hashmap)
    assert "HashMap" in resp_hashmap.optimized_prompt
    assert "Collection" not in resp_hashmap.optimized_prompt

    req_collections = PromptRequest(prompt=COLLECTIONS_PROMPT, compression_engine="deterministic")
    resp_collections = optimize_prompt(req_collections)
    assert "Collection" in resp_collections.optimized_prompt
    assert "HashMap" not in resp_collections.optimized_prompt
    assert "frequency of each integer" not in resp_collections.optimized_prompt

    # 2. Concurrent isolation test
    def _run_req(prompt: str, engine: str = "deterministic"):
        return optimize_prompt(PromptRequest(prompt=prompt, compression_engine=engine))

    prompts = [
        COLLECTIONS_PROMPT,
        HASHMAP_PROMPT,
        PASSWORD_PROMPT,
        BINARY_SEARCH_PROMPT,
        COLLECTIONS_PROMPT,
        HASHMAP_PROMPT,
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(_run_req, prompts))

    # Validate each response has zero cross-contamination
    # Results 0 and 4 are Collections
    for idx in (0, 4):
        out = results[idx].optimized_prompt
        assert "frequency of each integer" not in out
        assert "HashMap" not in out
        assert "plaintext" not in out
        assert "binary search" not in out

    # Results 1 and 5 are HashMap
    for idx in (1, 5):
        out = results[idx].optimized_prompt
        assert "Thread-Safe" not in out
        assert "Best Use Case" not in out
        assert "plaintext" not in out

    # Result 2 is Password
    out_pass = results[2].optimized_prompt
    assert "HashMap" not in out_pass
    assert "ArrayList" not in out_pass
