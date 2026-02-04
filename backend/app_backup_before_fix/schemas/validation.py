from pydantic import BaseModel, Field, validator
from typing import Optional

class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    user_id: int
    role: str = "default"

    @validator('message')
    def prevent_prompt_injection(cls, v):
        forbidden = ["ignore previous", "system command", "admin mode", "you are now an evil ai"]
        for phrase in forbidden:
            if phrase in v.lower():
                raise ValueError("🚨 Виявлено підозрілу активність (Prompt Injection Attempt)")
        return v

class AIResponseSchema(BaseModel):
    id: str
    text: str
    anxiety_score: float = Field(ge=0.0, le=1.0)
    detected_emotion: str
    is_compliant: bool = True
