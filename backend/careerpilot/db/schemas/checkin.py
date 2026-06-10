from pydantic import BaseModel, Field


class CheckinCreate(BaseModel):
    user_id: str
    mood_score: int = Field(..., ge=1, le=10)
    energy_score: int = Field(..., ge=1, le=10)
    wins: list[str] = []
    blockers: list[str] = []
    notes: str = ""
    created_at: str


class CheckinOut(BaseModel):
    id: str
    user_id: str
    mood_score: int
    energy_score: int
    wins: list[str]
    blockers: list[str]
    notes: str
    created_at: str
