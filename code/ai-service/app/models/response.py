from pydantic import BaseModel


class DetectedEntity(BaseModel):
    text: str
    label: str


class PromptResponse(BaseModel):

    original_prompt: str

    optimized_prompt: str

    entities: list[DetectedEntity]

    risk_score: int

    risk_level: str