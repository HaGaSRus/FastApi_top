from typing import Optional
from pydantic import BaseModel


class AnalyticsCreate(BaseModel):
    question_id: Optional[int] = None
    subquestion_id: Optional[int] = None
    author_id: int

    class Config:
        from_attributes = True
