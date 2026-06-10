from pydantic import BaseModel


class PlanCreate(BaseModel):
    user_id: str
    date: str
    coach_note: str = ""


class PlanTaskCreate(BaseModel):
    plan_id: str
    user_id: str
    title: str
    category: str
    priority: int
    completed: bool = False
    due_date: str | None = None
