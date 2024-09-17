from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.logger.logger import logger
from app.questions.models import Category, Question
from app.questions.schemas import CategoryCreate, QuestionCreate
from fastapi import HTTPException


async def fetch_parent_category(db: AsyncSession, parent_id: int) -> Category:
    query = select(Category).where(Category.id == parent_id)
    result = await db.execute(query)
    parent_category = result.scalar_one_or_none()
    return parent_category


async def check_existing_category(db: AsyncSession, category_name: str) -> Category:
    query = select(Category).where(Category.name == category_name)
    result = await db.execute(query)
    existing_category = result.scalar_one_or_none()
    return existing_category


async def create_new_category(db: AsyncSession, category: CategoryCreate, parent_id: int) -> Category:
    new_category = Category(name=category.name, parent_id=parent_id)
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category


async def get_category_by_id(category_id: int, db: AsyncSession):
    try:
        category = await db.execute(select(Category).filter_by(id=category_id))
        return category.scalars().first()
    except Exception as e:
        logger.error(f"Ошибка при получении категории: {e}")
        raise HTTPException(status_code=500, detail="Не удалось получить категорию")


async def create_new_question(question: QuestionCreate, category_id: int, db: AsyncSession):
    new_question = Question(
        text=question.text,
        category_id=category_id,
        parent_question_id=None
    )
    db.add(new_question)
    await db.commit()
    await db.refresh(new_question)
    return new_question