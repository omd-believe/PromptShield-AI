"""
spaCy NER detector — named entity recognition stage.

Detects privacy-relevant named entities using the configured spaCy model.
Only returns entity types listed in config.NER_PRIVACY_TYPES.

Key design decisions:
- The spaCy model is loaded ONCE at instantiation (not per request).
- Detection returns structured dicts with character offsets.
- Detection does NOT perform anonymization (that is a separate stage).
- Unknown / irrelevant entity types (DATE, MONEY, etc.) are silently filtered.
"""

import logging

import spacy
from spacy.language import Language

from app import config

from app.services.technical_filter import TechnicalEntityFilter

import re

logger = logging.getLogger(__name__)

_PLACEHOLDER_TOKEN_RE = re.compile(r"^\[?[A-Z]+(?:_\d+)?\]?$")
_PLACEHOLDER_SPAN_RE = re.compile(r"\[[A-Z]+(?:_\d+)?\]")

_COMMON_NER_FALSE_POSITIVES = {
    "email", "phone", "call", "contact", "name", "pan", "aadhaar", "dob",
    "account", "bank", "api", "key", "prompt", "message", "request", "user",
    "summary", "answer", "question", "support", "help",
    # Instructional verbs & prompt terms frequently misclassified as GPE or PERSON
    "explain", "describe", "summarize", "compare", "review", "create", "write",
    "implement", "analyze", "list", "show", "generate", "provide", "return",
    "include", "approach", "step", "steps", "beginner", "beginners", "example",
    "examples", "overview", "practice", "practices",
}


class NERDetector:
    """
    Wraps spaCy NER and filters to privacy-relevant entity types only.

    Entity types returned are limited to config.NER_PRIVACY_TYPES:
      PERSON, GPE, ORG, LOC

    Technical terms (programming languages, generic types, frameworks,
    code blocks, identifiers) are preserved and never treated as PII.
    """

    def __init__(self) -> None:
        self._nlp: Language = self._load_model()

    @staticmethod
    def _load_model() -> Language:
        model_name = config.SPACY_MODEL
        try:
            nlp = spacy.load(model_name)
            logger.info("spaCy model loaded: %s", model_name)
            return nlp
        except OSError as exc:
            logger.error(
                "Failed to load spaCy model '%s'. "
                "Run: python -m spacy download %s",
                model_name,
                model_name,
            )
            raise RuntimeError(
                f"spaCy model '{model_name}' is not available. "
                f"Install it with: python -m spacy download {model_name}"
            ) from exc

    def detect(self, prompt: str) -> list[dict]:
        """
        Run NER on *prompt* and return privacy-relevant entities.

        Each entity dict contains:
          - text:  the surface form as it appears in the prompt
          - label: the entity type (PERSON, GPE, ORG, LOC)
          - start: character start offset
          - end:   character end offset

        Entities are returned in the order they appear in the text.
        """
        doc = self._nlp(prompt)
        code_spans = TechnicalEntityFilter.find_code_spans(prompt)

        entities: list[dict] = []
        for ent in doc.ents:
            if ent.label_ not in config.NER_PRIVACY_TYPES:
                continue

            text = ent.text.strip()
            normalized = text.lower()
            if normalized in _COMMON_NER_FALSE_POSITIVES:
                continue

            # Skip anonymization placeholder tokens (e.g. [PERSON_1], EMAIL_3 inside [EMAIL_3])
            if _PLACEHOLDER_TOKEN_RE.fullmatch(text):
                if (
                    (text.startswith("[") and text.endswith("]"))
                    or (ent.start_char > 0 and prompt[ent.start_char - 1] == "[" and ent.end_char < len(prompt) and prompt[ent.end_char] == "]")
                    or any(m.start() <= ent.start_char and ent.end_char <= m.end() for m in _PLACEHOLDER_SPAN_RE.finditer(prompt))
                ):
                    continue

            if TechnicalEntityFilter.is_technical_false_positive(
                text, ent.label_, ent.start_char, ent.end_char, prompt, code_spans
            ):
                logger.debug(
                    "Filtered technical false positive entity: '%s' (%s)",
                    text,
                    ent.label_,
                )
                continue

            entities.append(
                {
                    "text": text,
                    "label": ent.label_,
                    "confidence": 0.75,
                    "start": ent.start_char,
                    "end": ent.end_char,
                }
            )

        return entities