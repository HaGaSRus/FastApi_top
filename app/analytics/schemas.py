from pydantic import BaseModel


class AnalyticsCreate(BaseModel):
    question_id: int
    author_id: int

    class Config:
        from_attributes = True
