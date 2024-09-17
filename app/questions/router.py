import traceback
from typing import List
from fastapi_versioning import version
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.dao.dependencies import get_current_user, get_current_admin_user
from app.database import get_db
from app.exceptions import FailedTGetDataFromDatabase
from app.logger.logger import logger
from app.questions.models import Category, Question
from app.questions.schemas import CategoryResponse, QuestionResponse, CategoryCreate, QuestionCreate, SubQuestionCreate, \
    CategoryCreateResponse

router_question = APIRouter(
    prefix="/question",
    tags=["Вопросы"],
)


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






# Получение всех категорий с вложенными подкатегориями
@router_question.get("/categories", response_model=List[CategoryResponse])
@version(1)
async def get_categories(db: AsyncSession = Depends(get_db)):
    try:
        logger.debug("Executing query to get root categories with parent_id == None")
        result = await db.execute(
            select(Category).where(Category.parent_id == None).options(selectinload(Category.subcategories))
        )
        categories = result.scalars().all()
        logger.debug(f"Fetched categories: {categories}")
        return categories
    except Exception as e:
        logger.error(f"Ошибка при получении категорий: {e}")
        logger.error(traceback.format_exc())
        raise FailedTGetDataFromDatabase


# Создание новой категории (только для админа)
@router_question.post("/categories", response_model=CategoryCreateResponse)
@version(1)
async def create_category(
        category: CategoryCreate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_user)
):
    try:
        new_category = Category(name=category.name)
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        logger.info(f"Создана новая категория: {new_category}")
        return CategoryCreateResponse.from_orm(new_category)
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError при создании категории: {e}")
        raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")
    except Exception as e:
        logger.error(f"Ошибка при создании категории: {e}")
        logger.error(traceback.format_exc())
        raise FailedTGetDataFromDatabase


# Создание подкатегории (только админ)
@router_question.post("/categories/{parent_id}/subcategories", response_model=CategoryResponse)
@version(1)
async def create_subcategory(
        category: CategoryCreate,
        parent_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_user)
):
    try:
        logger.debug(f"Fetching parent category with id: {parent_id}")
        parent_category = await fetch_parent_category(db, parent_id)
        logger.debug(f"Parent category: {parent_category}")

        if not parent_category:
            logger.warning(f"Parent category with id {parent_id} not found")
            raise HTTPException(status_code=404, detail="Родительская категория не найдена")

        logger.debug(f"Checking if category with name {category.name} already exists")
        existing_category = await check_existing_category(db, category.name)
        logger.debug(f"Existing category: {existing_category}")

        if existing_category:
            logger.warning(f"Category with name {category.name} already exists")
            raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")

        logger.debug(f"Creating new subcategory")
        new_category = await create_new_category(db, category, parent_id)
        logger.info(f"Created new subcategory: {new_category}")

        # Используйте dict для преобразования модели в словарь перед созданием Pydantic объекта
        category_data = {column.name: getattr(new_category, column.name) for column in Category.__table__.columns}
        return CategoryResponse(**category_data)

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError during subcategory creation: {e}")
        raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")

    except Exception as e:
        logger.error(f"Error during subcategory creation: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Не удалось получить данные из базы")


# Создание вопроса верхнего уровня
@router_question.post("/categories/{category_id}/questions", response_model=QuestionResponse)
@version(1)
async def create_question(
        question: QuestionCreate,
        category_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    try:
        logger.debug(f"Fetching category with id: {category_id}")
        category = await db.get(Category, category_id)
        if not category:
            logger.warning(f"Категория с id {category_id} не найдена")
            raise HTTPException(status_code=404, detail="Категория не найдена")

        new_question = Question(
            text=question.text,
            category_id=category_id,
            parent_question_id=None
        )
        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)
        logger.info(f"Создан новый вопрос: {new_question}")
        return new_question
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError при создании вопроса: {e}")
        raise HTTPException(status_code=400,
                            detail="Ошибка целостности данных. Возможно, вопрос с таким текстом уже существует.")
    except Exception as e:
        logger.error(f"Ошибка при создании вопроса: {e}")
        logger.error(traceback.format_exc())
        await db.rollback()
        raise HTTPException(status_code=500, detail="Не удалось создать вопрос")


# Создание под-вопроса
@router_question.post("/questions/{parent_question_id}/subquestions", response_model=QuestionResponse)
@version(1)
async def create_subquestion(
        question: SubQuestionCreate,
        parent_question_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    try:
        logger.debug(f"Fetching parent question with id: {parent_question_id}")
        parent_question = await db.get(Question, parent_question_id)
        if not parent_question:
            logger.warning(f"Родительский вопрос с id {parent_question_id} не найден")
            raise HTTPException(status_code=404, detail="Родительский вопрос не найден")

        new_question = Question(
            text=question.text,
            category_id=parent_question.category_id,
            parent_question_id=parent_question_id
        )
        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)
        logger.info(f"Создан новый под-вопрос: {new_question}")
        return new_question
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError при создании под-вопроса: {e}")
        raise HTTPException(status_code=400,
                            detail="Ошибка целостности данных. Возможно, под-вопрос с таким текстом уже существует.")
    except Exception as e:
        logger.error(f"Ошибка при создании под-вопроса: {e}")
        logger.error(traceback.format_exc())
        await db.rollback()
        raise HTTPException(status_code=500, detail="Не удалось создать под-вопрос")

