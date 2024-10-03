from pydantic import BaseModel, Field
from typing import Optional


class SearchQuestionRequest(BaseModel):
    query: str = Field(..., description="Текст для поиска")
    category_id: Optional[int] = Field(None, description="ID категории для фильтрации")


