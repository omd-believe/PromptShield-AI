from fastapi import APIRouter

from app.models.request import PromptRequest
from app.models.response import PromptResponse
from app.services.preprocessing import Preprocessor

router = APIRouter()

preprocessor = Preprocessor()


@router.post("/optimize", response_model=PromptResponse)
def optimize_prompt(request: PromptRequest):

    original_prompt = request.prompt

    cleaned_prompt = preprocessor.clean(original_prompt)

    return PromptResponse(
        original_prompt=original_prompt,
        optimized_prompt=cleaned_prompt
    )