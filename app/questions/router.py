import traceback
from typing import List, Optional
from fastapi_versioning import version
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.dao.dependencies import get_current_user, get_current_admin_user
from app.database import get_db
from app.exceptions import FailedTGetDataFromDatabase
from app.logger.logger import logger
from app.questions.models import Category, Question
from app.questions.schemas import CategoryResponse, QuestionResponse, CategoryCreate, QuestionCreate, \
    CategoryCreateResponse
from app.questions.utils import fetch_parent_category, check_existing_category, create_new_category, get_category_by_id

router_categories = APIRouter(
    prefix="/categories",
    tags=["Категории"],
)


router_question = APIRouter(
    prefix="/question",
    tags=["Вопросы"],
)


# Получение всех категорий с вложенными подкатегориями
@router_categories.get("/categories", response_model=List[CategoryResponse])
@version(1)
async def get_categories(db: AsyncSession = Depends(get_db)):
    try:
        logger.debug("Выполнение запроса для получения корневых категорий с родительским_id == Нет")
        result = await db.execute(
            select(Category).where(Category.parent_id == None).options(selectinload(Category.subcategories))
        )
        categories = result.scalars().all()

        category_responses = []
        for category in categories:
            logger.debug(f"Категория обработки: {category}")

            # Создаем список подкатегорий с правильным значением edit
            subcategories_data = [{
                'id': subcat.id,
                'name': subcat.name,
                'parent_id': subcat.parent_id,
                'subcategories': [],  # Можно дополнить, если нужно отображать вложенные подкатегории
                'edit': True,  # Здесь указываем значение edit для подкатегорий
                'number': subcat.id  # Устанавливаем значение number для подкатегорий
            } for subcat in category.subcategories]

            # Создаем CategoryResponse для основной категории
            category_data = CategoryResponse(
                id=category.id,
                name=category.name,
                parent_id=category.parent_id,
                subcategories=subcategories_data,
                edit=True,  # Здесь устанавливаем значение edit для основной категории
                number=category.number  # Добавляем поле number
            )
            category_responses.append(category_data)

            # Добавляем информацию о подкатегориях для отладки
            logger.debug(f"Подкатегории: {subcategories_data}")

        logger.debug(f"Полученные категории с полем редактирования: {category_responses}")
        return category_responses
    except Exception as e:
        logger.error(f"Ошибка при получении категорий: {e}")
        logger.error(traceback.format_exc())
        raise FailedTGetDataFromDatabase


# Создание новой категории (только для админа)
@router_categories.post("/categories", response_model=CategoryCreateResponse)
@version(1)
async def create_category(
        category: CategoryCreate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_user)
):
    try:
        # Создаем новую категорию
        new_category = Category(name=category.name)
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)

        # Устанавливаем значение number на основе ID
        new_category.number = new_category.id
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
@router_categories.post("/categories/{parent_id}/subcategories", response_model=CategoryResponse)
@version(1)
async def create_subcategory(
        category: CategoryCreate,
        parent_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_user)
):
    try:
        logger.debug(f"Получение родительской категории с идентификатором: {parent_id}")
        parent_category = await fetch_parent_category(db, parent_id)
        logger.debug(f"Родительская категория: {parent_category}")

        if not parent_category:
            logger.warning(f"Родительская категория с идентификатором {parent_id} не найдена")
            raise HTTPException(status_code=404, detail="Родительская категория не найдена")

        logger.debug(f"Проверка наличия категории с именем {category.name}.")
        existing_category = await check_existing_category(db, category.name)
        logger.debug(f"Существующая категория: {existing_category}")

        if existing_category:
            logger.warning(f"Категория с названием {category.name} уже существует.")
            raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")

        logger.debug(f"Создание новой подкатегории")
        new_category = await create_new_category(db, category, parent_id)
        logger.info(f"Создана новая подкатегория: {new_category}")

        # Используйте dict для преобразования модели в словарь перед созданием Pydantic объекта
        category_data = {column.name: getattr(new_category, column.name) for column in Category.__table__.columns}
        return CategoryResponse(**category_data)

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Ошибка IntegrityError при создании подкатегории: {e}")
        raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")

    except Exception as e:
        logger.error(f"Ошибка при создании подкатегории: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Не удалось получить данные из базы")


# Создание вопроса верхнего уровня
@router_question.post("/categories/{category_id}/questions", response_model=QuestionResponse)
@version(1)
async def create_question(
        question: QuestionCreate,
        category_id: int = Path(..., ge=1),
        parent_question_id: Optional[int] = Query(None, description="ID родительского вопроса"),  # Новый параметр
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    try:
        logger.debug(f"Получение категории по идентификатору: {category_id}")
        category = await get_category_by_id(category_id, db)
        if not category:
            logger.warning(f"Категория с id {category_id} не найдена")
            raise HTTPException(status_code=404, detail="Категория не найдена")

        # Обрабатываем значение parent_question_id
        if parent_question_id == 0:
            parent_question_id = None

        new_question = Question(
            text=question.text,
            category_id=category_id,
            parent_question_id=parent_question_id,  # Используем None, если parent_question_id == 0
            number=None,  # Установка значения по умолчанию
            answer=question.answer  # Установка значения для нового поля
        )

        # Добавление вопроса в базу данных
        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)  # Обновление нового вопроса после коммита

        # Устанавливаем значение number на основе ID
        new_question.number = new_question.id
        db.add(new_question)
        await db.commit()

        # Преобразуем новый вопрос в словарь для ответа
        question_data = {
            'id': new_question.id,
            'text': new_question.text,
            'answer': new_question.answer,
            'category_id': new_question.category_id,
            'parent_question_id': new_question.parent_question_id,
            'number': new_question.number,
            'sub_questions': []  # Здесь можно добавить под-вопросы, если это необходимо
        }

        logger.info(f"Создан новый вопрос: {question_data}")
        return QuestionResponse(**question_data)

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError при создании вопроса: {e}")
        raise HTTPException(status_code=400, detail="Ошибка целостности данных. Возможно, вопрос с таким текстом уже существует.")
    except Exception as e:
        logger.error(f"Ошибка при создании вопроса: {e}")
        logger.error(traceback.format_exc())
        await db.rollback()
        raise HTTPException(status_code=500, detail="Не удалось создать вопрос")


# Создание под-вопроса
@router_question.post("/questions/{parent_question_id}/subquestions", response_model=QuestionResponse)
@version(1)
async def create_subquestion(
        question: QuestionCreate,
        parent_question_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    try:
        logger.debug(f"Получение родительского вопроса с идентификатором: {parent_question_id}")
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

        # Устанавливаем значение number на основе ID
        new_question.number = new_question.id
        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)

        # Преобразуем новый под-вопрос в Pydantic модель
        response = QuestionResponse(
            id=new_question.id,
            text=new_question.text,
            answer=new_question.answer,
            category_id=new_question.category_id,
            parent_question_id=new_question.parent_question_id,
            number=new_question.number,
            sub_questions=[]
        )

        logger.info(f"Создан новый под-вопрос: {response}")
        return response

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError при создании под-вопроса: {e}")
        raise HTTPException(status_code=400, detail="Ошибка целостности данных. Возможно, под-вопрос с таким текстом уже существует.")
    except Exception as e:
        logger.error(f"Ошибка при создании под-вопроса: {e}")
        logger.error(traceback.format_exc())
        await db.rollback()
        raise HTTPException(status_code=500, detail="Не удалось создать под-вопрос")

