from fastapi import APIRouter

from app.models.request import PromptRequest
from app.models.response import PromptResponse

router = APIRouter()


@router.post("/optimize", response_model=PromptResponse)
def optimize_prompt(request: PromptRequest):

    prompt = request.prompt

    return PromptResponse(
        original_prompt=prompt,
        optimized_prompt=prompt
    )