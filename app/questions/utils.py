import json
from typing import List

from pydantic_core._pydantic_core import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import Request
from app.exceptions import ValidationErrorException, JSONDecodingError, InvalidDataFormat, \
    CategoryWithSameNameAlreadyExists, CategoryNotFoundException
from app.logger.logger import logger
from app.questions.models import Category, Question
from app.questions.schemas import CategoryCreate, QuestionCreate, UpdateCategoryData, CategoryResponse
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


async def process_category_updates(db: AsyncSession, category_data_list: List[dict]) -> List[CategoryResponse]:
    """Обработка обновления категорий"""
    updated_categories = []

    for category_data in category_data_list:
        data = validate_category_data(category_data)

        category = await find_category_by_id(db, data.id)
        await ensure_unique_category_name(db, data)

        updated_category = await update_category(db, category, data)
        updated_categories.append(updated_category)

    return updated_categories


async def get_category_data(request: Request):
    """Получение и декодирование данных из запроса"""
    body = await request.body()
    body_str = body.decode('utf-8')
    logger.debug(f"Полученные данные: {body_str}")

    try:
        category_data_list = json.loads(body_str)
        if not isinstance(category_data_list, list):
            raise InvalidDataFormat
        logger.debug(f"Преобразованные данные: {category_data_list}")
        return category_data_list
    except json.JSONDecodeError:
        logger.error(f"Ошибка декодирования JSON: {body_str}")
        raise JSONDecodingError


def validate_category_data(category_data: dict):
    """Валидация данных с использованием Pydantic"""
    try:
        return UpdateCategoryData(**category_data)
    except ValidationError as e:
        logger.error(f"Ошибка валидации данных: {e}")
        raise ValidationErrorException(error_detail=str(e))


async def find_category_by_id(db: AsyncSession, category_id: int) -> Category:
    """Поиск категории по id"""
    category = await db.get(Category, category_id)
    if not category:
        logger.warning(f"Категория с id {category_id} не найдена")
        raise CategoryNotFoundException(category_id=category_id)
    return category


async def ensure_unique_category_name(db: AsyncSession, data: UpdateCategoryData):
    """Проверка уникальности имени категории"""
    existing_category = await db.execute(
        select(Category).filter(
            Category.name == data.name,
            Category.id != data.id
        )
    )
    if existing_category.scalars().first():
        logger.error(f"Категория с именем '{data.name}' уже существует")
        raise CategoryWithSameNameAlreadyExists(data.name)


async def update_category(db: AsyncSession, category: Category, data: UpdateCategoryData) -> CategoryResponse:
    """Обновление полей категории и сохранение изменений"""
    updated = False
    if category.name != data.name:
        category.name = data.name
        updated = True

    if category.number != data.number:
        category.number = data.number
        updated = True

    if updated:
        db.add(category)
        await db.commit()
        await db.refresh(category)
        logger.debug(f"Обновленная категория: {category}")

    return CategoryResponse(
        id=category.id,
        name=category.name,
        parent_id=category.parent_id,
        number=category.number
    )
