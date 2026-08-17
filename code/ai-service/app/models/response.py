from pydantic import BaseModel

class PromptResponse(BaseModel):
    original_prompt: str
    optimized_prompt: str

    