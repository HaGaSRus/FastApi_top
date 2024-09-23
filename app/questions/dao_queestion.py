from typing import Optional

from fastapi import Depends
from app.database import get_db
from app.exceptions import CategoryNotFound, ParentQuestionNotFound
from app.questions.models import Question, Category
from app.questions.schemas import QuestionCreate
from sqlalchemy.ext.asyncio import AsyncSession

from app.questions.utils import get_category_by_id


class QuestionService:
    @staticmethod
    async def create_question(
            question: QuestionCreate,
            category_id: int,
            parent_question_id: Optional[int],
            db: AsyncSession
    ) -> Question:
        # Обработка категории
        category = await get_category_by_id(category_id, db)
        if not category:
            raise CategoryNotFound

    # Обработка значения parent_question_id
        if parent_question_id is None:
            parent_question_id = None

    # Создание нового вопроса
        new_question = Question(
            text=question.text,
            answer=question.answer,
            category_id=category_id,
            parent_question_id=parent_question_id,
        )

        # Добавление и сохранение вопроса

        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)

        # Присваивание id в поле number

        new_question.number = new_question.id
        db.add(new_question)
        await db.commit()

        return new_question

    @staticmethod
    async def create_subquestion(
            question: QuestionCreate,
            parent_question_id: int,
            db: AsyncSession,
    ) -> Question:
        parent_question = await db.get(Question, parent_question_id)
        if not parent_question:
            raise ParentQuestionNotFound

        # Создание под-вопроса
        new_question = Question(
            text=question.text,
            category_id=parent_question.category_id,
            parent_question_id=parent_question_id,
        )
        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)

        # Устанавливаем значение number
        new_question.number = new_question.id
        db.add(new_question)
        await db.commit()

        return new_question


async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if not category:
        raise CategoryNotFound
    return category
