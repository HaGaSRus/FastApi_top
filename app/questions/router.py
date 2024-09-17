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

        # Fetch parent category
        query = select(Category).where(Category.id == parent_id)
        result = await db.execute(query)
        parent_category = result.scalar_one_or_none()
        logger.debug(f"Parent category: {parent_category}")

        if not parent_category:
            logger.warning(f"Parent category with id {parent_id} not found")
            raise HTTPException(status_code=404, detail="Родительская категория не найдена")

        # Check for existing category
        query = select(Category).where(Category.name == category.name)
        result = await db.execute(query)
        existing_category = result.scalar_one_or_none()
        logger.debug(f"Existing category: {existing_category}")

        if existing_category:
            logger.warning(f"Категория с именем {category.name} уже существует")
            raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")

        # Create new category
        new_category = Category(name=category.name, parent_id=parent_id)
        logger.debug(f"New category to be added: {new_category}")

        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        logger.info(f"Создана новая подкатегория: {new_category}")

        return new_category

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError при создании подкатегории: {e}")
        raise HTTPException(status_code=400,
                            detail="Ошибка целостности данных. Возможно, категория с таким именем уже существует.")

    except Exception as e:
        logger.error(f"Ошибка при создании подкатегории: {e}")
        logger.error(traceback.format_exc())
        await db.rollback()
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# Получение вопросов по категории
@router_question.get("/categories/{category_id}/questions", response_model=List[QuestionResponse])
@version(1)
async def get_questions_by_category(category_id: int, db: AsyncSession = Depends(get_db)):
    try:
        logger.debug(f"Fetching questions for category_id: {category_id}")
        result = await db.execute(
            select(Question).where(Question.category_id == category_id, Question.parent_question_id == None).options(
                selectinload(Question.sub_questions))
        )
        questions = result.scalars().all()
        logger.debug(f"Fetched questions: {questions}")
        return questions
    except Exception as e:
        logger.error(f"Ошибка при получении вопросов: {e}")
        logger.error(traceback.format_exc())
        raise FailedTGetDataFromDatabase


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

