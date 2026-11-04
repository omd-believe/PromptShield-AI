"""
Unit tests for FlanT5Service.

These tests use mocks to test model loading, device resolution, error handling,
timeouts, and metadata without requiring a GPU or real model weights.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app import config
from app.services.flan_t5_service import (
    FlanT5Error,
    FlanT5Service,
    FlanT5TimeoutError,
    FlanT5UnavailableError,
)


@pytest.fixture
def service():
    """Create a fresh FlanT5Service instance for isolated unit testing."""
    srv = FlanT5Service()
    yield srv
    srv.unload_model()


def test_disabled_mode_does_not_load_model(service, monkeypatch):
    """When FLAN_T5_ENABLED is False, load_model returns False and is_available is False."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", False)
    loaded = service.load_model()
    assert loaded is False
    assert service.is_available is False


def test_device_resolution_auto_with_cuda(service, monkeypatch):
    """When device is auto and CUDA is available, resolves to cuda."""
    monkeypatch.setattr(config, "FLAN_T5_DEVICE", "auto")
    with patch("torch.cuda.is_available", return_value=True):
        dev = service.resolve_device()
        assert dev == "cuda"


def test_device_resolution_auto_without_cuda(service, monkeypatch):
    """When device is auto and CUDA is unavailable, resolves to cpu."""
    monkeypatch.setattr(config, "FLAN_T5_DEVICE", "auto")
    with patch("torch.cuda.is_available", return_value=False):
        dev = service.resolve_device()
        assert dev == "cpu"


def test_device_resolution_cpu(service, monkeypatch):
    """When device is explicitly cpu, resolves to cpu."""
    monkeypatch.setattr(config, "FLAN_T5_DEVICE", "cpu")
    dev = service.resolve_device()
    assert dev == "cpu"


def test_explicit_unavailable_cuda_raises_error(service, monkeypatch):
    """When device is explicitly cuda but CUDA is unavailable, raises RuntimeError."""
    monkeypatch.setattr(config, "FLAN_T5_DEVICE", "cuda")
    with patch("torch.cuda.is_available", return_value=False):
        with pytest.raises(RuntimeError) as exc_info:
            service.resolve_device()
        assert "explicitly configured as 'cuda'" in str(exc_info.value)


def test_model_loading_occurs_only_once(service, monkeypatch):
    """Calling load_model multiple times reuses the already loaded model."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    mock_tok = MagicMock()
    mock_model = MagicMock()

    with patch.object(service, "resolve_device", return_value="cpu"), \
         patch("transformers.AutoTokenizer.from_pretrained", return_value=mock_tok) as mock_tok_load, \
         patch("transformers.AutoModelForSeq2SeqLM.from_pretrained", return_value=mock_model) as mock_mod_load:

        res1 = service.load_model()
        assert res1 is True
        assert service.is_available is True

        res2 = service.load_model()
        assert res2 is True

        # Ensure loaded once
        assert mock_tok_load.call_count == 1
        assert mock_mod_load.call_count == 1


def test_generate_candidate_when_unavailable_raises_error(service):
    """Attempting generation on an unloaded service raises FlanT5UnavailableError."""
    assert service.is_available is False
    with pytest.raises(FlanT5UnavailableError):
        service.generate_candidate("Test prompt")


def test_generate_candidate_empty_or_whitespace_returns_empty(service, monkeypatch):
    """Empty or whitespace input safely returns empty string without calling model."""
    service._is_available = True
    service._model = MagicMock()
    service._tokenizer = MagicMock()

    assert service.generate_candidate("") == ""
    assert service.generate_candidate("   \n\t  ") == ""


def test_generate_candidate_with_mocked_model(service, monkeypatch):
    """Candidate generation properly tokenizes, runs inference, and strips prefixes."""
    monkeypatch.setattr(config, "FLAN_T5_MAX_INPUT_TOKENS", 128)
    monkeypatch.setattr(config, "FLAN_T5_MAX_NEW_TOKENS", 64)
    monkeypatch.setattr(config, "FLAN_T5_NUM_BEAMS", 2)

    service._is_available = True
    service._device = "cpu"

    mock_tokenizer = MagicMock()
    mock_model = MagicMock()

    mock_inputs = {"input_ids": MagicMock(), "attention_mask": MagicMock()}
    mock_tokenizer.return_value = mock_inputs
    mock_model.generate.return_value = [[1, 2, 3]]
    mock_tokenizer.decode.return_value = "Rewritten prompt: Summarize the document."

    service._model = mock_model
    service._tokenizer = mock_tokenizer

    result = service.generate_candidate("Please summarize the following document.")
    assert result == "Summarize the document."
    mock_model.generate.assert_called_once()


def test_generate_candidate_exception_raises_flan_t5_error(service):
    """Exceptions raised during model generation are wrapped in FlanT5Error."""
    service._is_available = True
    service._device = "cpu"

    mock_tokenizer = MagicMock()
    mock_model = MagicMock()
    mock_tokenizer.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}
    mock_model.generate.side_effect = RuntimeError("GPU out of memory")

    service._model = mock_model
    service._tokenizer = mock_tokenizer

    with pytest.raises(FlanT5Error) as exc_info:
        service.generate_candidate("Some input prompt")
    assert "Inference execution failed" in str(exc_info.value)


def test_generate_candidate_with_timeout_success(service):
    """generate_candidate_with_timeout returns result within time limit."""
    service._is_available = True
    with patch.object(service, "generate_candidate", return_value="Fast prompt"):
        result = service.generate_candidate_with_timeout("Test", timeout=2.0)
        assert result == "Fast prompt"


def test_generate_candidate_with_timeout_expires(service):
    """Slow generation raises FlanT5TimeoutError."""
    service._is_available = True

    def slow_gen(prompt):
        import time
        time.sleep(1.0)
        return "Slow prompt"

    with patch.object(service, "generate_candidate", side_effect=slow_gen):
        with pytest.raises(FlanT5TimeoutError):
            service.generate_candidate_with_timeout("Test", timeout=0.05)


def test_model_metadata_does_not_expose_prompt(service):
    """Metadata includes diagnostic flags and never includes prompt content."""
    meta = service.get_model_metadata()
    assert "model_id" in meta
    assert "device" in meta
    assert "enabled" in meta
    assert "prompt" not in meta
    assert "user_prompt" not in meta


def test_missing_model_files_logs_clear_error(service, monkeypatch):
    """When model files cannot be found, load_model returns False and sets descriptive error."""
    monkeypatch.setattr(config, "FLAN_T5_ENABLED", True)
    monkeypatch.setattr(config, "FLAN_T5_USE_ONLINE_DOWNLOAD", False)

    with patch.object(service, "resolve_device", return_value="cpu"), \
         patch("transformers.AutoTokenizer.from_pretrained", side_effect=OSError("Local files not found")):

        success = service.load_model()
        assert success is False
        assert service.is_available is False
        assert "Local files not found" in str(service._load_error)
