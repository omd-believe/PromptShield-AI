from app.services.grammar_corrector import GrammarCorrector
from app.api.optimize import optimize_prompt
from app.models.request import PromptRequest


def test_corrects_high_confidence_typos_and_reports_changes():
    result = GrammarCorrector().correct("Hlleo, Please recieve teh report.")

    assert result["prompt"] == "Hello, Please receive the report."
    assert result["changed"] is True
    assert "Hlleo → Hello" in result["corrections"]
    assert "recieve → receive" in result["corrections"]
    assert "teh → the" in result["corrections"]


def test_preserves_privacy_placeholders():
    result = GrammarCorrector().correct("Send [EMAIL] teh report .")

    assert result["prompt"] == "Send [EMAIL] the report."
    assert "[EMAIL]" in result["prompt"]


def test_does_not_change_already_correct_prompt():
    prompt = "Summarize the report in five bullet points."

    result = GrammarCorrector().correct(prompt)

    assert result == {"prompt": prompt, "corrections": [], "changed": False}


def test_corrects_words_not_in_manual_dictionary():
    result = GrammarCorrector().correct("Please summrize the report.")

    assert result["prompt"] == "Please summarize the report."
    assert "summrize → summarize" in result["corrections"]


def test_preserves_capitalized_names_and_technical_terms():
    prompt = "Ask Gaurav to review the Kubernetes deployment."

    result = GrammarCorrector().correct(prompt)

    assert result["prompt"] == prompt
    assert result["corrections"] == []


def test_pipeline_reports_grammar_and_does_not_penalize_pii_masking():
    result = optimize_prompt(
        PromptRequest(
            prompt="Please recieve teh report from john@example.com.",
            compression_engine="deterministic",
        )
    )

    assert result.grammar_corrected is True
    assert result.grammar_corrections == [
        "recieve → receive",
        "teh → the",
    ]
    assert "[EMAIL]" in result.optimized_prompt
    assert result.semantic_valid is True


def test_preserves_code_fence_formatting():
    prompt = "Please explain:\n```python\n  def  greet():\n    return 'Please'\n```"

    result = GrammarCorrector().correct(prompt)

    assert "  def  greet():" in result["prompt"]
    assert "return 'Please'" in result["prompt"]


def test_preserves_structured_json_line():
    prompt = 'Return JSON: {"message": "Please keep this"}'

    result = GrammarCorrector().correct(prompt)

    assert result["prompt"] == prompt
