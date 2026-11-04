"""
Regression tests for Technical NER False Positives (Phase 1).

Ensures that programming languages, frameworks, SQL queries, generics,
API identifiers, and CS terminology are never misclassified as PERSON,
ORG, GPE, or LOC, while genuine PII (names, locations) continues to be detected.
"""

import pytest
from app.services.ner import NERDetector
from app.services.privacy_engine import PrivacyEngine


@pytest.fixture(scope="module")
def ner_detector() -> NERDetector:
    return NERDetector()


@pytest.fixture(scope="module")
def privacy_engine() -> PrivacyEngine:
    return PrivacyEngine()


def test_java_hashmap_prompt_no_person_ner(ner_detector):
    prompt = (
        "Write a Java method using a HashMap to count the frequency of each integer "
        "in an array. The method must return Map<Integer, Integer>, handle an empty array, "
        "have O(n) expected time complexity, and use no external libraries. "
        "Explain the approach in 3 bullet points."
    )
    entities = ner_detector.detect(prompt)
    labels = {e["label"] for e in entities}
    assert "PERSON" not in labels
    assert "ORG" not in labels
    assert len(entities) == 0


def test_java_learning_plan_no_ner_false_positives(ner_detector):
    prompt = (
        "Create a 7-day Java learning plan for a beginner. Spend 2 hours daily. "
        "Cover OOP, collections, exception handling, Java 8 streams, multithreading, "
        "and JVM basics. Include one coding task per day. Use Java only, not Python. "
        "Keep each day's theory under 30 minutes."
    )
    entities = ner_detector.detect(prompt)
    assert len(entities) == 0


def test_spring_boot_jpa_rest_controller_no_ner(ner_detector):
    prompt = (
        "Write a Spring Boot REST controller with a GET endpoint `/api/v1/users/{id}` "
        "that queries a PostgreSQL database using JPA repository and returns a "
        "ResponseEntity<UserDto>. Handle UserNotFoundException with GlobalExceptionHandler."
    )
    entities = ner_detector.detect(prompt)
    assert len(entities) == 0


def test_sql_query_prompt_no_ner(ner_detector):
    prompt = (
        "SELECT user_id, email, created_at FROM users "
        "WHERE status = 'ACTIVE' ORDER BY created_at DESC LIMIT 10;"
    )
    entities = ner_detector.detect(prompt)
    assert len(entities) == 0


def test_fenced_code_blocks_ignored_by_ner(ner_detector):
    prompt = (
        "Review this code snippet:\n"
        "```java\n"
        "public class UserService {\n"
        "    private final UserRepository repository;\n"
        "    public User findById(Long id) { return repository.findById(id).orElse(null); }\n"
        "}\n"
        "```\n"
        "Explain any design issues."
    )
    entities = ner_detector.detect(prompt)
    assert len(entities) == 0


def test_genuine_person_still_detected(ner_detector):
    prompt = "Barack Obama delivered a speech in Chicago."
    entities = ner_detector.detect(prompt)
    person_entities = [e for e in entities if e["label"] == "PERSON"]
    assert any("Barack Obama" in e["text"] for e in person_entities)


def test_mixed_technical_prompt_with_genuine_pii(privacy_engine):
    prompt = (
        "Review the Java code submitted by candidate Rahul Sharma. "
        "His email is rahul.sharma@example.com and phone is +91 9876543210. "
        "The submission implements a binary search using Map<String, Integer> in Spring Boot."
    )
    result = privacy_engine.analyze(prompt)
    detected_texts = {e["text"] for e in result["entities"]}
    detected_labels = {e["label"] for e in result["entities"]}

    # PII must be detected
    assert "rahul.sharma@example.com" in detected_texts
    assert any("9876543210" in t for t in detected_texts)
    assert "Rahul Sharma" in detected_texts

    # Technical terms must NOT be masked as PII
    assert "Java" not in detected_texts
    assert "Spring Boot" not in detected_texts
    assert "Map" not in detected_texts

    # Anonymized prompt must preserve technical terms while masking PII
    anon = result["anonymized_prompt"]
    assert "Java" in anon
    assert "Spring Boot" in anon
    assert "Map<String, Integer>" in anon or "binary search" in anon
    assert "[EMAIL" in anon
    assert "[PHONE" in anon
    assert "[PERSON" in anon
    assert "rahul.sharma@example.com" not in anon
