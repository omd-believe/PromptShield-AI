"""
PromptShield AI Service — Configuration

All tunable values live here.
Override with environment variables where appropriate.
"""

import os

# ─── Service-to-service authentication ────────────────────────────────────────

AI_SERVICE_API_KEY: str = os.getenv("AI_SERVICE_API_KEY", "")
"""Shared secret between Spring Boot backend and this AI service.

Incoming requests to /optimize and /analyze must include the header:
  X-AI-Service-Key: <key>

Leave empty to disable authentication for local development only.
Generate a production key with: openssl rand -hex 32
NEVER commit the real key to source control.
"""

# ─── Prompt constraints ────────────────────────────────────────────────────────

MAX_PROMPT_LENGTH: int = int(os.getenv("MAX_PROMPT_LENGTH", "8000"))
"""Maximum allowed prompt length in characters. Requests exceeding this are
rejected before entering the NLP pipeline."""

# ─── spaCy model ───────────────────────────────────────────────────────────────

SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_sm")
"""spaCy language model to load. Must be installed in the environment."""

TOKENIZER_MODEL: str = os.getenv("TOKENIZER_MODEL", "gpt-4o-mini")
"""Model name used to select the tokenizer for token metrics."""

# ─── NER — privacy-relevant entity types ──────────────────────────────────────

NER_PRIVACY_TYPES: set[str] = {"PERSON", "GPE", "ORG", "LOC"}
"""Entity types detected by spaCy that are considered privacy-relevant.
Only these types will appear in the entity list and be considered for
anonymization according to the privacy policy.

Not included: DATE, TIME, MONEY, PERCENT, CARDINAL, ORDINAL, QUANTITY,
NORP, FAC, PRODUCT, EVENT, WORK_OF_ART, LAW, LANGUAGE — these are not
personally identifying in isolation.
"""

# ─── Privacy policy — what gets anonymized ────────────────────────────────────

#  Regex-detected labels are ALWAYS anonymized (they are definitionally PII).
REGEX_ALWAYS_ANONYMIZE: set[str] = {
    "EMAIL",
    "PHONE",
    "PAN",
    "AADHAAR",
    "API_KEY",
    "DATE_OF_BIRTH",
    "BANK_ACCOUNT",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "ADDRESS",
    "PASSPORT",
    "JWT",
    "PRIVATE_KEY",
    "DATABASE_URL",
    "CLOUD_CREDENTIAL",
    "WEBHOOK_SECRET",
    "GENERIC_SECRET",
    "SSN",
    "DRIVER_LICENSE",
    "UK_NINO",
    "CANADIAN_SIN",
    "IBAN",
    "EU_TAX_ID",
}

#  NER-detected types that should be anonymized according to privacy policy.
#  ORG is intentionally excluded — knowing someone works at "Google" is not
#  necessarily PII; PERSON and GPE are higher-risk.
NER_ANONYMIZE_TYPES: set[str] = {"PERSON", "GPE"}

# ─── Risk weights ──────────────────────────────────────────────────────────────

RISK_WEIGHTS: dict[str, int] = {
    "API_KEY":  40,
    "AADHAAR":  30,
    "PAN":      30,
    "EMAIL":    20,
    "PHONE":    20,
    "DATE_OF_BIRTH": 25,
    "BANK_ACCOUNT": 30,
    "CREDIT_CARD": 35,
    "IP_ADDRESS": 10,
    "ADDRESS": 20,
    "PASSPORT": 30,
    "JWT": 40,
    "PRIVATE_KEY": 50,
    "DATABASE_URL": 40,
    "CLOUD_CREDENTIAL": 40,
    "WEBHOOK_SECRET": 40,
    "GENERIC_SECRET": 35,
    "SSN": 30,
    "DRIVER_LICENSE": 25,
    "UK_NINO": 30,
    "CANADIAN_SIN": 30,
    "IBAN": 35,
    "EU_TAX_ID": 25,
    "PERSON":   15,
    "GPE":      10,
    "ORG":       5,
    "LOC":       5,
}
"""Risk weight per entity type. Weights sum toward a maximum of 100."""

RISK_MAX_SCORE: int = 100

# ─── Risk level thresholds (inclusive lower bound) ────────────────────────────

RISK_THRESHOLDS: dict[str, int] = {
    "CRITICAL": 70,
    "HIGH":     40,
    "MEDIUM":   20,
    "LOW":       0,
}

# ─── Service metadata ──────────────────────────────────────────────────────────

SERVICE_TITLE: str = "PromptShield AI"
SERVICE_DESCRIPTION: str = (
    "Privacy-preserving prompt optimization service.\n\n"
    "Detects and anonymizes sensitive information in prompts, "
    "scores privacy risk, and applies deterministic prompt optimization."
)
SERVICE_VERSION: str = "1.0.0"

# ─── Compression Engine Selection ─────────────────────────────────────────────

COMPRESSION_ENGINE: str = os.getenv("COMPRESSION_ENGINE", "auto").strip().lower()
"""Strategy selector: 'auto', 'llmlingua', 'flan-t5', or 'deterministic'."""

# ─── LLMLingua-2 model settings (prompt compression) ──────────────────────────

LLMLINGUA_ENABLED: bool = os.getenv("LLMLINGUA_ENABLED", "true").strip().lower() in ("true", "1", "yes")
"""Whether LLMLingua-2 prompt compression candidate generation is enabled."""

LLMLINGUA_MODEL_ID: str = os.getenv(
    "LLMLINGUA_MODEL_ID",
    "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
)
"""Hugging Face model ID or local directory path for LLMLingua-2 weights."""

LLMLINGUA_DEVICE: str = os.getenv("LLMLINGUA_DEVICE", "auto").strip().lower()
"""Device for inference: 'auto', 'cpu', or 'cuda'."""

LLMLINGUA_RATE: float = float(os.getenv("LLMLINGUA_RATE", "0.75"))
"""Target compression rate: proportion of tokens to keep.

Benchmark starting points (test in order):
  0.75 — default; preserves 75% of tokens, good balance of fidelity and savings.
  0.65 — moderate; useful when the prompt is verbose and information-dense.
  0.85 — light;   near-lossless, useful for short prompts with many constraints.

Never drop below 0.50 without explicit user confirmation — important instructions
and privacy placeholders may be lost."""

LLMLINGUA_TARGET_TOKEN: int = int(os.getenv("LLMLINGUA_TARGET_TOKEN", "-1"))
"""Target token count after compression (-1 to use LLMLINGUA_RATE instead)."""

LLMLINGUA_TIMEOUT_SECONDS: float = float(os.getenv("LLMLINGUA_TIMEOUT_SECONDS", "30.0"))
"""Timeout in seconds for LLMLingua-2 inference before falling back to deterministic candidate."""

LLMLINGUA_MAX_CONCURRENT_REQUESTS: int = int(os.getenv("LLMLINGUA_MAX_CONCURRENT_REQUESTS", "1"))
"""Maximum concurrent model compression calls allowed to protect CPU/RAM."""

LLMLINGUA_USE_ONLINE_DOWNLOAD: bool = os.getenv("LLMLINGUA_USE_ONLINE_DOWNLOAD", "false").strip().lower() in ("true", "1", "yes")
"""Whether to allow online downloading of weights from Hugging Face Hub if not cached."""

LLMLINGUA_FORCE_RESERVE_DIGIT: bool = os.getenv("LLMLINGUA_FORCE_RESERVE_DIGIT", "true").strip().lower() in ("true", "1", "yes")
"""Whether to forcibly preserve numeric tokens during compression."""

LLMLINGUA_DROP_CONSECUTIVE: bool = os.getenv("LLMLINGUA_DROP_CONSECUTIVE", "true").strip().lower() in ("true", "1", "yes")
"""Whether to drop consecutive force tokens if redundant."""

LLMLINGUA_MIN_SEMANTIC_SCORE: float = float(os.getenv("LLMLINGUA_MIN_SEMANTIC_SCORE", "70.0"))
"""Minimum semantic similarity score required to accept an LLMLingua-2 candidate."""

LLMLINGUA_MAX_FORCE_TOKENS: int = int(os.getenv("LLMLINGUA_MAX_FORCE_TOKENS", "100"))
"""Maximum number of critical tokens (placeholders, constraints, negations) forced in compression."""

# ─── FLAN-T5 model settings (optional candidate generator) ───────────────────

FLAN_T5_ENABLED: bool = os.getenv("FLAN_T5_ENABLED", "false").strip().lower() in ("true", "1", "yes")
"""Whether the optional FLAN-T5 prompt rewriting candidate stage is enabled."""

FLAN_T5_MODEL_ID: str = os.getenv("FLAN_T5_MODEL_ID", "google/flan-t5-small")
"""Hugging Face model ID or local directory path for FLAN-T5 weights."""

FLAN_T5_DEVICE: str = os.getenv("FLAN_T5_DEVICE", "auto").strip().lower()
"""Device for inference: 'auto', 'cpu', or 'cuda'."""

FLAN_T5_MAX_INPUT_TOKENS: int = int(os.getenv("FLAN_T5_MAX_INPUT_TOKENS", "512"))
"""Maximum tokens from input prompt fed to the model."""

FLAN_T5_MAX_NEW_TOKENS: int = int(os.getenv("FLAN_T5_MAX_NEW_TOKENS", "192"))
"""Maximum new tokens generated by the model."""

FLAN_T5_NUM_BEAMS: int = int(os.getenv("FLAN_T5_NUM_BEAMS", "2"))
"""Number of beams for beam search generation."""

FLAN_T5_TIMEOUT_SECONDS: float = float(os.getenv("FLAN_T5_TIMEOUT_SECONDS", "20.0"))
"""Timeout in seconds for model inference before falling back to deterministic candidate."""

FLAN_T5_MAX_CONCURRENT_REQUESTS: int = int(os.getenv("FLAN_T5_MAX_CONCURRENT_REQUESTS", "1"))
"""Maximum concurrent model generation calls allowed to protect VRAM/RAM."""

FLAN_T5_USE_ONLINE_DOWNLOAD: bool = os.getenv("FLAN_T5_USE_ONLINE_DOWNLOAD", "false").strip().lower() in ("true", "1", "yes")
"""Whether to allow online downloading of weights from Hugging Face Hub if not cached."""

FLAN_T5_MIN_SEMANTIC_SCORE: float = float(os.getenv("FLAN_T5_MIN_SEMANTIC_SCORE", "70.0"))
"""Minimum semantic similarity score required to accept a FLAN-T5 candidate."""

# ─── Quality validation length thresholds ─────────────────────────────────────

QUALITY_ANOMALY_LENGTH_RATIO: float = float(os.getenv("QUALITY_ANOMALY_LENGTH_RATIO", "0.4"))
"""Ratio of candidate length to input length below which a length anomaly is flagged
and strict deliverable/concept verification is triggered."""

QUALITY_ABSOLUTE_MIN_RATIO: float = float(os.getenv("QUALITY_ABSOLUTE_MIN_RATIO", "0.15"))
"""Absolute minimum ratio below which a candidate is rejected for excessive truncation."""


