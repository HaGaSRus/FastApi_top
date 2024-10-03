from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.questions.models import Question


class SearchQuestionRequest(BaseModel):
    query: str = Field(..., description="Текст для поиска")
    category_id: Optional[int] = Field(None, description="ID категории для фильтрации")


class QuestionSearchService:
    @staticmethod
    async def search_questions(
            db: AsyncSession,
            query: str,
            category_id: Optional[int] = None
    ) -> List[Question]:
        stmt = select(Question).where(Question.text.ilike(f"%{query}%"))  # Поиск по тексту

        if category_id is not None:
            stmt = stmt.filter(Question.category_id == category_id)

        result = await db.execute(stmt)
        return result.scalars().all()



