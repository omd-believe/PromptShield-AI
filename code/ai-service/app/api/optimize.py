from fastapi import APIRouter

from app.models.request import PromptRequest
from app.models.response import PromptResponse
from app.services.preprocessing import Preprocessor
from app.services.privacy_engine import PrivacyEngine

router = APIRouter()

preprocessor = Preprocessor()
privacy_engine = PrivacyEngine()


@router.post("/optimize", response_model=PromptResponse)
def optimize_prompt(request: PromptRequest):

    original_prompt = request.prompt

    # Step 1: Preprocessing
    cleaned_prompt = preprocessor.clean(original_prompt)

    # Step 2: Privacy detection, risk scoring and anonymization
    privacy_result = privacy_engine.analyze(cleaned_prompt)

    return PromptResponse(
        original_prompt=original_prompt,
        optimized_prompt=privacy_result["anonymized_prompt"],
        entities=privacy_result["entities"],
        risk_score=privacy_result["risk_score"],
        risk_level=privacy_result["risk_level"]
    )