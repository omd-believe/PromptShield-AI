"""
Unit tests for LLMLinguaService and the evaluate_llmlingua_candidate evaluator.

These tests run entirely without loading real model weights:
- LLMLinguaService is tested via mocking PromptCompressor.
- evaluate_llmlingua_candidate is tested with fully mocked lightweight
  dependencies (no spaCy, no numpy re-import, no model loading).
- Integration tests use live HTTP requests to the already-running dev server.
"""

import threading
import types
import unittest
from unittest.mock import MagicMock, patch

import sys
import os

_AI_SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AI_SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _AI_SERVICE_ROOT)


# ─────────────────────────────────────────────────────────────────────────────
# LLMLinguaService — model loading
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMLinguaServiceLoadModel(unittest.TestCase):

    def _make_service(self):
        from app.services.llmlingua_service import LLMLinguaService
        return LLMLinguaService()

    def test_load_model_returns_false_when_disabled(self):
        svc = self._make_service()
        with patch("app.config.LLMLINGUA_ENABLED", False):
            result = svc.load_model()
        self.assertFalse(result)
        self.assertFalse(svc.is_available)

    def test_load_model_returns_false_on_import_error(self):
        svc = self._make_service()
        with patch("app.config.LLMLINGUA_ENABLED", True), \
             patch("app.config.LLMLINGUA_MODEL_ID", "mock-model"), \
             patch("app.config.LLMLINGUA_DEVICE", "cpu"), \
             patch("app.config.LLMLINGUA_USE_ONLINE_DOWNLOAD", False), \
             patch.dict("sys.modules", {"llmlingua": None}):
            result = svc.load_model()
        self.assertFalse(result)
        self.assertFalse(svc.is_available)

    def test_load_model_succeeds_with_mock_compressor(self):
        svc = self._make_service()
        mock_compressor = MagicMock()
        mock_llmlingua = types.ModuleType("llmlingua")
        mock_llmlingua.PromptCompressor = MagicMock(return_value=mock_compressor)
        with patch("app.config.LLMLINGUA_ENABLED", True), \
             patch("app.config.LLMLINGUA_MODEL_ID", "mock-model"), \
             patch("app.config.LLMLINGUA_DEVICE", "cpu"), \
             patch("app.config.LLMLINGUA_USE_ONLINE_DOWNLOAD", False), \
             patch.dict("sys.modules", {"llmlingua": mock_llmlingua, "torch": MagicMock()}), \
             patch.object(svc, "resolve_device", return_value="cpu"):
            result = svc.load_model()
        self.assertTrue(result)
        self.assertTrue(svc.is_available)
        self.assertIs(svc._compressor, mock_compressor)

    def test_load_model_is_idempotent(self):
        svc = self._make_service()
        mock_compressor = MagicMock()
        svc._compressor = mock_compressor
        svc._is_available = True
        with patch("app.config.LLMLINGUA_ENABLED", True):
            result = svc.load_model()
        self.assertTrue(result)
        self.assertIs(svc._compressor, mock_compressor)


# ─────────────────────────────────────────────────────────────────────────────
# LLMLinguaService — compress_candidate
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMLinguaServiceCompressCandidate(unittest.TestCase):

    def _make_loaded_service(self, compress_output=None):
        from app.services.llmlingua_service import LLMLinguaService
        svc = LLMLinguaService()
        mock_compressor = MagicMock()
        mock_compressor.compress_prompt.return_value = compress_output or {
            "compressed_prompt": "Compressed output",
            "origin_tokens": 10,
            "compressed_tokens": 6,
            "ratio": "1.7x",
            "rate": "60.0%",
        }
        svc._compressor = mock_compressor
        svc._is_available = True
        svc._device = "cpu"
        return svc, mock_compressor

    def test_compress_candidate_returns_compressed_text(self):
        svc, _ = self._make_loaded_service({
            "compressed_prompt": "Short prompt.",
            "origin_tokens": 5,
            "compressed_tokens": 3,
        })
        with patch("app.config.LLMLINGUA_RATE", 0.6), \
             patch("app.config.LLMLINGUA_TARGET_TOKEN", -1), \
             patch("app.config.LLMLINGUA_FORCE_RESERVE_DIGIT", True), \
             patch("app.config.LLMLINGUA_DROP_CONSECUTIVE", True), \
             patch("app.config.LLMLINGUA_MAX_FORCE_TOKENS", 100), \
             patch("app.config.LLMLINGUA_MODEL_ID", "mock"), \
             patch("app.services.constraint_extractor.constraint_extractor.extract_critical_tokens",
                   return_value=[]):
            result, diagnostics = svc.compress_candidate("This is a longer sample prompt for testing.")
        self.assertEqual(result, "Short prompt.")
        self.assertIn("origin_tokens", diagnostics)
        self.assertIn("duration_ms", diagnostics)

    def test_compress_candidate_strips_outer_quotes(self):
        svc, _ = self._make_loaded_service({
            "compressed_prompt": '"quoted output"',
            "origin_tokens": 4,
            "compressed_tokens": 3,
        })
        with patch("app.config.LLMLINGUA_RATE", 0.6), \
             patch("app.config.LLMLINGUA_TARGET_TOKEN", -1), \
             patch("app.config.LLMLINGUA_FORCE_RESERVE_DIGIT", True), \
             patch("app.config.LLMLINGUA_DROP_CONSECUTIVE", True), \
             patch("app.config.LLMLINGUA_MAX_FORCE_TOKENS", 100), \
             patch("app.config.LLMLINGUA_MODEL_ID", "mock"), \
             patch("app.services.constraint_extractor.constraint_extractor.extract_critical_tokens",
                   return_value=[]):
            result, _ = svc.compress_candidate("Some input prompt here.")
        self.assertEqual(result, "quoted output")

    def test_compress_candidate_raises_on_empty_input(self):
        svc, _ = self._make_loaded_service()
        result, diagnostics = svc.compress_candidate("   ")
        self.assertEqual(result, "")
        self.assertEqual(diagnostics["status"], "empty_input")

    def test_compress_candidate_raises_when_unavailable(self):
        from app.services.llmlingua_service import LLMLinguaService, LLMLinguaUnavailableError
        svc = LLMLinguaService()
        with self.assertRaises(LLMLinguaUnavailableError):
            svc.compress_candidate("Some prompt")

    def test_compress_candidate_with_timeout_raises_on_timeout(self):
        from app.services.llmlingua_service import LLMLinguaService, LLMLinguaTimeoutError
        svc, _ = self._make_loaded_service()

        def slow_compress(*args, **kwargs):
            import time
            time.sleep(5)
            return "slow", {}

        with patch.object(svc, "compress_candidate", side_effect=slow_compress):
            with self.assertRaises(LLMLinguaTimeoutError):
                svc.compress_candidate_with_timeout("Test prompt", timeout=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# LLMLinguaService — thread safety
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMLinguaServiceThreadSafety(unittest.TestCase):

    def test_concurrent_load_calls_load_once(self):
        from app.services.llmlingua_service import LLMLinguaService
        svc = LLMLinguaService()
        load_count = {"n": 0}

        mock_compressor = MagicMock()
        mock_llmlingua = types.ModuleType("llmlingua")

        def counting_compressor(**kwargs):
            load_count["n"] += 1
            return mock_compressor

        mock_llmlingua.PromptCompressor = counting_compressor

        with patch("app.config.LLMLINGUA_ENABLED", True), \
             patch("app.config.LLMLINGUA_MODEL_ID", "mock-model"), \
             patch("app.config.LLMLINGUA_DEVICE", "cpu"), \
             patch("app.config.LLMLINGUA_USE_ONLINE_DOWNLOAD", False), \
             patch.dict("sys.modules", {"llmlingua": mock_llmlingua, "torch": MagicMock()}), \
             patch.object(svc, "resolve_device", return_value="cpu"):
            threads = [threading.Thread(target=svc.load_model) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        self.assertEqual(load_count["n"], 1)
        self.assertTrue(svc.is_available)


# ─────────────────────────────────────────────────────────────────────────────
# evaluate_llmlingua_candidate — isolated unit tests with mocked deps
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluateLlmlinguaCandidate(unittest.TestCase):
    """
    Unit tests for evaluate_llmlingua_candidate without real model inference.
    All spaCy/privacy/semantic dependencies are replaced with lightweight mocks,
    avoiding the numpy double-import error on Python 3.14.
    """

    def setUp(self):
        from app.services.candidate_evaluator import evaluate_llmlingua_candidate
        from app.services.token_counter import TokenCounter

        self._fn = evaluate_llmlingua_candidate
        self._tc = TokenCounter()

        self._mock_pe = MagicMock()
        self._mock_pe.analyze.return_value = {"entities": []}

        self._mock_qv = MagicMock()
        self._mock_qv.validate_prompt.side_effect = lambda anon, cand: (cand, [], False)

        self._mock_sv = MagicMock()
        self._mock_sv.score.return_value = 90.0

        self._mock_gc = MagicMock()
        self._mock_gc.correct.return_value = {"changed": False, "corrections": [], "prompt": ""}

    def _call(self, anonymized_prompt, deterministic_candidate, candidate,
              protected_entities=None, should_anon=None):
        if should_anon is None:
            should_anon = lambda e, p: False
        return self._fn(
            anonymized_prompt=anonymized_prompt,
            deterministic_candidate=deterministic_candidate,
            candidate=candidate,
            privacy_policy=None,
            protected_entities=protected_entities or [],
            token_counter=self._tc,
            privacy_engine=self._mock_pe,
            should_anonymize_fn=should_anon,
            quality_validator=self._mock_qv,
            semantic_validator=self._mock_sv,
            grammar_corrector=self._mock_gc,
            filler_patterns=[],
            compact_patterns=[],
        )

    def test_rejects_empty_candidate(self):
        accepted, reason = self._call(
            anonymized_prompt="Explain the concept.",
            deterministic_candidate="Explain concept.",
            candidate="",
        )
        self.assertFalse(accepted)
        self.assertIn("empty", reason.lower())

    def test_rejects_pathologically_short_candidate(self):
        anon = "Explain the concept of inheritance in object-oriented programming in detail and provide concrete examples."
        candidate = "OOP."
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=anon,
            candidate=candidate,
        )
        self.assertFalse(accepted)
        self.assertIn("shorter", reason.lower())

    def test_rejects_placeholder_alteration(self):
        anon = "Email [PERSON_1] at [EMAIL_1] for details."
        candidate = "Email [PERSON_1] for details."
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=anon,
            candidate=candidate,
        )
        self.assertFalse(accepted)
        self.assertIn("placeholder", reason.lower())

    def test_rejects_entity_leakage_via_entity_list(self):
        # Candidate preserves the placeholder but ALSO contains the raw entity text —
        # this simulates a model that copies the entity back alongside the placeholder.
        anon = "Contact [PERSON_1] for support."
        candidate = "Contact [PERSON_1] (John Smith) for support."
        protected = [{"text": "John Smith", "label": "PERSON", "confidence": 1.0}]
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=anon,
            candidate=candidate,
            protected_entities=protected,
        )
        self.assertFalse(accepted)
        self.assertIn("protected", reason.lower())

    def test_rejects_identical_to_anonymized(self):
        anon = "Explain encapsulation in Python with examples."
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=anon + " Done.",
            candidate=anon,
        )
        self.assertFalse(accepted)
        self.assertIn("identical", reason.lower())

    def test_rejects_identical_to_deterministic(self):
        anon = "Explain encapsulation in Python with examples please."
        det = "Explain encapsulation in Python with examples."
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=det,
            candidate=det,
        )
        self.assertFalse(accepted)
        self.assertIn("identical", reason.lower())

    def test_rejects_no_token_reduction_no_clarity(self):
        """Synonym substitution without token reduction should be rejected."""
        anon = "Explain the concept of encapsulation in object-oriented programming."
        candidate = "Describe the concept of encapsulation in object-oriented programming."
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=anon,
            candidate=candidate,
        )
        self.assertFalse(accepted)
        self.assertIn("no measurable", reason.lower())

    def test_accepts_candidate_with_genuine_token_reduction(self):
        anon = "Could you please kindly explain encapsulation in OOP with examples?"
        candidate = "Explain encapsulation in OOP with examples."
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=anon,
            candidate=candidate,
        )
        self.assertTrue(accepted, f"Expected accepted but got: {reason}")
        self.assertIsNone(reason)

    def test_low_semantic_score_rejects_candidate(self):
        anon = "Explain encapsulation in object-oriented programming."
        candidate = "Calculate derivatives of polynomial functions."
        self._mock_sv.score.return_value = 20.0
        with patch("app.config.LLMLINGUA_MIN_SEMANTIC_SCORE", 70.0):
            accepted, reason = self._call(
                anonymized_prompt=anon,
                deterministic_candidate=anon,
                candidate=candidate,
            )
        self.assertFalse(accepted)
        self.assertIn("semantic", reason.lower())

    def test_quality_validation_failure_rejects_candidate(self):
        anon = "Do not use global variables; write a recursive solution."
        candidate = "Use global variables; write an iterative solution."
        # quality validator says fallback_used=True (constraint violated)
        self._mock_qv.validate_prompt.side_effect = lambda a, c: (a, ["constraint violated"], True)
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=anon,
            candidate=candidate,
        )
        self.assertFalse(accepted)
        self.assertIn("quality", reason.lower())

    def test_does_not_reject_placeholder_labeled_as_person(self):
        """
        Regression test: When spaCy NER detects a placeholder name like 'EMAIL_3'
        as PERSON, evaluate_llmlingua_candidate must NOT reject it as sensitive data leakage.
        """
        anon = "Please send email to [PERSON_1] ([EMAIL_1]), [PERSON_2] ([EMAIL_2]), and [PERSON_3] ([EMAIL_3])."
        candidate = "Send email to [PERSON_1] [EMAIL_1] [PERSON_2] [EMAIL_2] [PERSON_3] [EMAIL_3]."
        # Simulate spaCy NER detecting EMAIL_3 as PERSON inside [EMAIL_3]
        self._mock_pe.analyze.return_value = {
            "entities": [
                {
                    "text": "EMAIL_3",
                    "label": "PERSON",
                    "start": candidate.index("EMAIL_3"),
                    "end": candidate.index("EMAIL_3") + len("EMAIL_3"),
                    "policy_action": "MASK",
                }
            ]
        }
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=anon,
            candidate=candidate,
            should_anon=lambda e, p: True,
        )
        self.assertTrue(accepted, f"Expected accepted, but got: {reason}")
        self.assertIsNone(reason)

    def test_does_not_reject_preexisting_term_in_anonymized_input(self):
        """
        If an entity was already present in anonymized_prompt, the candidate did not
        introduce it and must not be rejected.
        """
        anon = "Review Python guidelines for developer team."
        candidate = "Review Python guidelines team."
        self._mock_pe.analyze.return_value = {
            "entities": [
                {
                    "text": "Python",
                    "label": "ORG",
                    "start": candidate.index("Python"),
                    "end": candidate.index("Python") + len("Python"),
                    "policy_action": "MASK",
                }
            ]
        }
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=anon,
            candidate=candidate,
            should_anon=lambda e, p: True,
        )
        self.assertTrue(accepted, f"Expected accepted, but got: {reason}")
        self.assertIsNone(reason)

    def test_rejects_genuine_new_leakage_introduced_by_candidate(self):
        """
        If candidate introduces a new sensitive entity that was NOT in the anonymized prompt,
        it must be rejected as introduced leakage.
        """
        anon = "Send the quarterly summary."
        candidate = "Send quarterly summary to Alice Smith at secret org."
        self._mock_pe.analyze.return_value = {
            "entities": [
                {
                    "text": "Alice Smith",
                    "label": "PERSON",
                    "start": candidate.index("Alice Smith"),
                    "end": candidate.index("Alice Smith") + len("Alice Smith"),
                    "policy_action": "MASK",
                }
            ]
        }
        accepted, reason = self._call(
            anonymized_prompt=anon,
            deterministic_candidate=anon,
            candidate=candidate,
            should_anon=lambda e, p: True,
        )
        self.assertFalse(accepted)
        self.assertIn("introduced sensitive data leakage", reason)


# ─────────────────────────────────────────────────────────────────────────────
# Integration tests — live HTTP requests to running dev server
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMLinguaPipelineIntegration(unittest.TestCase):
    """
    Integration tests that call the live AI service on port 8000.
    These run only when the server is accessible; they skip gracefully otherwise.
    """

    BASE_URL = "http://localhost:8000"

    @classmethod
    def setUpClass(cls):
        import urllib.request
        try:
            urllib.request.urlopen(f"{cls.BASE_URL}/health", timeout=2)
            cls._server_available = True
        except Exception:
            cls._server_available = False

    def _skip_if_unavailable(self):
        if not self._server_available:
            self.skipTest("AI service not running on port 8000")

    def _post(self, prompt, extra=None):
        import json
        import urllib.request
        body = {"prompt": prompt}
        if extra:
            body.update(extra)
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.BASE_URL}/optimize",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def test_response_includes_anonymized_tokens(self):
        """The response must include anonymized_tokens as a non-negative integer."""
        self._skip_if_unavailable()
        data = self._post("Explain abstraction in OOP.")
        self.assertIn("anonymized_tokens", data)
        self.assertIsNotNone(data["anonymized_tokens"])
        self.assertGreaterEqual(data["anonymized_tokens"], 0)

    def test_response_has_optimization_strategy(self):
        """optimization_strategy must be one of the expected values."""
        self._skip_if_unavailable()
        data = self._post("Explain polymorphism briefly.")
        self.assertIn(data["optimization_strategy"], ("deterministic", "llmlingua-2", "flan-t5"))

    def test_deterministic_engine_override(self):
        """Explicitly requesting 'deterministic' engine skips all models."""
        self._skip_if_unavailable()
        data = self._post(
            "Could you please kindly summarize OOP principles?",
            {"compression_engine": "deterministic"},
        )
        self.assertEqual(data["optimization_strategy"], "deterministic")
        self.assertFalse(data["model_used"])

    def test_no_placeholder_leakage_in_response(self):
        """Optimized prompt must never contain raw sensitive entity values."""
        self._skip_if_unavailable()
        data = self._post("My email is test@example.com and I need help with Python.")
        opt = data.get("optimized_prompt", "")
        self.assertNotIn("test@example.com", opt)

    def test_risk_score_and_level_present(self):
        """Response must include risk_score and risk_level fields."""
        self._skip_if_unavailable()
        data = self._post("Explain machine learning briefly.")
        self.assertIn("risk_score", data)
        self.assertIn("risk_level", data)
        self.assertIn(data["risk_level"], ("LOW", "MEDIUM", "HIGH", "CRITICAL"))

    def test_token_count_consistency(self):
        """optimized_tokens must be <= original_tokens or a warning issued."""
        self._skip_if_unavailable()
        prompt = "Could you please kindly explain the concept of encapsulation in detail?"
        data = self._post(prompt)
        orig = data["original_tokens"]
        opt = data["optimized_tokens"]
        if opt > orig:
            # An increase warning must be present
            warnings_text = " ".join(data.get("optimization_warnings", []))
            self.assertIn("increased", warnings_text)


# ─────────────────────────────────────────────────────────────────────────────
# ConstraintExtractor — unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestConstraintExtractor(unittest.TestCase):

    def setUp(self):
        from app.services.constraint_extractor import ConstraintExtractor
        self.extractor = ConstraintExtractor()

    def test_extracts_placeholders(self):
        tokens = self.extractor.extract_critical_tokens(
            "Contact [PERSON_1] at [EMAIL_1] for details."
        )
        self.assertIn("[PERSON_1]", tokens)
        self.assertIn("[EMAIL_1]", tokens)

    def test_extracts_negations(self):
        tokens = self.extractor.extract_critical_tokens(
            "Do not include any Python 2 code."
        )
        # Negation regex captures full phrases like 'Do not'
        negation_found = any(
            "not" in t.lower() or "never" in t.lower() or "no" in t.lower()
            for t in tokens
        )
        self.assertTrue(negation_found, f"No negation token found in: {tokens}")

    def test_extracts_numeric_limits(self):
        tokens = self.extractor.extract_critical_tokens(
            "Provide exactly 3 examples."
        )
        # Either the full match or the bare digit should be present
        numeric_found = any("3" in t for t in tokens)
        self.assertTrue(numeric_found, f"No numeric token found in: {tokens}")

    def test_respects_max_tokens(self):
        long_prompt = " ".join([f"[TOKEN_{i}]" for i in range(200)])
        tokens = self.extractor.extract_critical_tokens(long_prompt, max_tokens=10)
        self.assertLessEqual(len(tokens), 10)

    def test_no_duplicates(self):
        tokens = self.extractor.extract_critical_tokens(
            "Do not use not use Python 2. Not allowed."
        )
        self.assertEqual(len(tokens), len(set(tokens)))

    def test_empty_prompt_returns_empty(self):
        tokens = self.extractor.extract_critical_tokens("")
        self.assertEqual(tokens, [])

    def test_extracts_python_language(self):
        tokens = self.extractor.extract_critical_tokens(
            "Write a solution in Python without using global variables."
        )
        python_found = any("python" in t.lower() for t in tokens)
        self.assertTrue(python_found, f"Python not found in: {tokens}")

    def test_extracts_output_format(self):
        tokens = self.extractor.extract_critical_tokens(
            "Return the answer as JSON with a 'result' key."
        )
        json_found = any("json" in t.lower() for t in tokens)
        self.assertTrue(json_found, f"JSON not found in: {tokens}")


if __name__ == "__main__":
    unittest.main()
