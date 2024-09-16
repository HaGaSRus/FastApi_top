import traceback
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.dao.dependencies import get_current_admin_user, get_current_user
from app.database import get_db
from app.exceptions import FailedTGetDataFromDatabase
from app.logger.logger import logger
from app.questions.models import Category, Question
from app.questions.schemas import CategoryResponse, QuestionResponse, CategoryBase, QuestionBase, SubCategoryCreate, \
    SubQuestionCreate, QuestionCreate, CategoryCreate, CategoryCreateResponse
from fastapi_versioning import version

router_question = APIRouter(
    prefix="/question",
    tags=["Вопросы"],
)


# Получение всех категории с вложенными подкатегориями
@router_question.get("/categories", response_model=List[CategoryResponse])
@version(1)
async def get_categories(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Category)
            .where(Category.parent_id == None)
            .options(selectinload(Category.subcategories))
        )
        categories = result.scalars().all()
        return categories
    except Exception as e:
        logger.error(f"Ошибка при получении категории: {e}")
        raise FailedTGetDataFromDatabase


# Создание новой категории(Только для админа)
@router_question.post("/categories", response_model=CategoryCreateResponse)
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
        category_response = CategoryCreateResponse.from_orm(new_category)
        return category_response
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")
    except Exception as e:
        logger.error(f"Ошибка при создании категории: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Не удалось создать категорию")


# Создание подкатегории (только админ)
@router_question.post("/categories/{parent_id}/subcategories", response_model=CategoryResponse)
@version(1)
async def create_subcategory(
    parent_id: int = Path(..., ge=1),
    name: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    try:
        parent_category = await db.get(Category, parent_id)
        if not parent_category:
            raise HTTPException(status_code=404, detail="Родительская категория не найдена")

        # Проверяем, существует ли уже категория с таким именем
        existing_category = await db.execute(
            select(Category).where(Category.name == name)
        )
        if existing_category.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")

        new_category = Category(name=name, parent_id=parent_id)
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        return new_category

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")
    except Exception as e:
        logger.error(f"Ошибка при создании подкатегории: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")



# Получение вопрос по категории
@router_question.get("/categories/{category_id}/questions", response_model=List[QuestionResponse])
@version(1)
async def get_questions_by_category(category_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
        select(Question)
        .where(
            Question.category_id == category_id,
            Question.parent_question_id == None
        )
        .options(selectinload(Question.sub_questions))
        )
        questions = result.scalars().all()
        return questions
    except Exception as e:
        logger.error(f"Ошибка при получении вопросов: {e}")
        raise FailedTGetDataFromDatabase


# Создание вопроса верхнего уровня
@router_question.post("/categories/{category_id}/questions", response_model=QuestionResponse)
@version(1)
async def create_question(
    category_id: int = Path(..., ge=1),
    question: QuestionCreate = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        # Проверяем, существует ли категория
        category = await db.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Категория не найдена")

        new_question = Question(
            text=question.text,
            category_id=category_id
        )
        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)
        return new_question
    except Exception as e:
        logger.error(f"Ошибка при создании вопроса: {e}")
        raise HTTPException(status_code=500, detail="Не удалось создать вопрос")


# Создание под-вопроса
@router_question.post("/questions/{parent_question_id}/subquestions", response_model=QuestionResponse)
@version(1)
async def create_subquestion(
    parent_question_id: int = Path(..., ge=1),
    question: SubQuestionCreate = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        # Проверяем, существует ли родительский вопрос
        parent_question = await db.get(Question, parent_question_id)
        if not parent_question:
            raise HTTPException(status_code=404, detail="Родительский вопрос не найден")

        new_question = Question(
            text=question.text,
            category_id=parent_question.category_id,
            parent_question_id=parent_question_id
        )
        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)
        return new_question
    except Exception as e:
        logger.error(f"Ошибка при создании под-вопроса: {e}")
        raise HTTPException(status_code=500, detail="Не удалось создать под-вопрос")


# Ответ на вопрос
@router_question.post("/questions/{question_id}/answer", response_model=QuestionResponse)
@version(1)
async def answer_question(question_id: int, answer: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        result = await db.execute(
            select(Question).where(Question.id == question_id)
        )
        question = result.scalar_one_or_none()
        if not question:
            raise HTTPException(status_code=404, detail="Вопрос не найден")
        question.answer = answer
        await db.commit()
        await db.refresh(question)
        return question
    except Exception as e:
        logger.error(f"Ошибка при ответе на вопроса: {e}")
        raise FailedTGetDataFromDatabase

