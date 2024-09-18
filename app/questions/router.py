import json
import traceback
from typing import List, Optional
from fastapi_versioning import version
from fastapi import APIRouter, Depends, Path, Query, Request
from pydantic_core._pydantic_core import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.dao.dependencies import get_current_user, get_current_admin_user
from app.database import get_db
from app.exceptions import FailedTGetDataFromDatabase, CategoryWithTheSameNameAlreadyExists, ErrorCreatingCategory, \
    ErrorGettingCategories, CategoryNotFound, DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists, \
    FailedToCreateQuestion, ParentQuestionNotFound, FailedToCreateSubQuestion, \
    CategoryContainsSubcategoriesDeletionIsNotPossible, FailedToDeleteCategory, JSONDecodingError, InvalidDataFormat, \
    CategoryNotFoundException, ValidationErrorException, ErrorUpdatingCategories, FailedToUpdateCategories, \
    QuestionNotFound, CouldNotGetAnswerToQuestion, ParentCategoryNotFound, CategoryWithSameNameAlreadyExists
from app.logger.logger import logger
from app.questions.models import Category, Question
from app.questions.schemas import CategoryResponse, QuestionResponse, CategoryCreate, QuestionCreate, \
    CategoryCreateResponse, DeleteCategoryRequest, UpdateCategoryData, UpdateCategoriesRequest
from app.questions.utils import fetch_parent_category, check_existing_category, create_new_category, get_category_by_id, \
    get_category_data, process_category_updates

router_categories = APIRouter(
    prefix="/categories",
    tags=["Категории"],
)


router_question = APIRouter(
    prefix="/question",
    tags=["Вопросы"],
)


# Получение всех категорий с вложенными подкатегориями
@router_categories.get("/", response_model=List[CategoryResponse], summary="Получить все категории")
@version(1)
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Отобразить все категории имеющиеся в Базе данных"""
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
        raise ErrorGettingCategories


# Создание новой категории (только для админа)
@router_categories.post("/create", response_model=CategoryCreateResponse, summary="Создание новой категории")
@version(1)
async def create_category(
        category: CategoryCreate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_user)
):
    """Форма создания новой категории вопросов"""
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
        raise CategoryWithTheSameNameAlreadyExists
    except Exception as e:
        logger.error(f"Ошибка при создании категории: {e}")
        logger.error(traceback.format_exc())
        raise ErrorCreatingCategory


# Создание подкатегории (только админ)
@router_categories.post("/{parent_id}/subcategories",
                        response_model=CategoryResponse,
                        summary="Создание новой под-категории")
@version(1)
async def create_subcategory(
        category: CategoryCreate,
        parent_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_user)
):
    """Форма создания новой под-категории вопросов"""
    try:
        logger.debug(f"Получение родительской категории с идентификатором: {parent_id}")
        parent_category = await fetch_parent_category(db, parent_id)
        logger.debug(f"Родительская категория: {parent_category}")

        if not parent_category:
            logger.warning(f"Родительская категория с идентификатором {parent_id} не найдена")
            raise ParentCategoryNotFound

        logger.debug(f"Проверка наличия категории с именем {category.name}.")
        existing_category = await check_existing_category(db, category.name)
        logger.debug(f"Существующая категория: {existing_category}")

        if existing_category:
            logger.warning(f"Категория с названием {category.name} уже существует.")
            raise CategoryWithTheSameNameAlreadyExists

        logger.debug(f"Создание новой подкатегории")
        new_category = await create_new_category(db, category, parent_id)
        logger.info(f"Создана новая подкатегория: {new_category}")

        # Используйте dict для преобразования модели в словарь перед созданием Pydantic объекта
        category_data = {column.name: getattr(new_category, column.name) for column in Category.__table__.columns}
        return CategoryResponse(**category_data)

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Ошибка IntegrityError при создании подкатегории: {e}")
        raise CategoryWithTheSameNameAlreadyExists

    except Exception as e:
        logger.error(f"Ошибка при создании подкатегории: {e}")
        logger.error(traceback.format_exc())
        raise FailedTGetDataFromDatabase


# Создание вопроса верхнего уровня
@router_question.post("/{category_id}/questions",
                      response_model=QuestionResponse,
                      summary="Создание вопроса верхнего уровня")
@version(1)
async def create_question(
        question: QuestionCreate,
        category_id: int = Path(..., ge=1),
        parent_question_id: Optional[int] = Query(None, description="ID родительского вопроса"),  # Новый параметр
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Форма создания вопроса верхнего уровня"""
    try:
        logger.debug(f"Получение категории по идентификатору: {category_id}")
        category = await get_category_by_id(category_id, db)
        if not category:
            logger.warning(f"Категория с id {category_id} не найдена")
            raise CategoryNotFound

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
        raise DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists
    except Exception as e:
        logger.error(f"Ошибка при создании вопроса: {e}")
        logger.error(traceback.format_exc())
        await db.rollback()
        raise FailedToCreateQuestion


# Создание под-вопроса
@router_question.post("/{parent_question_id}/subquestions",
                      response_model=QuestionResponse,
                      summary="Создание под-вопроса")
@version(1)
async def create_subquestion(
        question: QuestionCreate,
        parent_question_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Форма создания Создание под-вопроса"""
    try:
        logger.debug(f"Получение родительского вопроса с идентификатором: {parent_question_id}")
        parent_question = await db.get(Question, parent_question_id)
        if not parent_question:
            logger.warning(f"Родительский вопрос с id {parent_question_id} не найден")
            raise ParentQuestionNotFound

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
            number=new_question.number,
            sub_questions=[]
        )

        logger.info(f"Создан новый под-вопрос: {response}")
        return response

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError при создании под-вопроса: {e}")
        raise DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists
    except Exception as e:
        logger.error(f"Ошибка при создании под-вопроса: {e}")
        logger.error(traceback.format_exc())
        await db.rollback()
        raise FailedToCreateSubQuestion


@router_categories.post("/delete", response_model=CategoryResponse, summary="Удаление категории")
@version(1)
async def delete_category(
        request: DeleteCategoryRequest,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_user)
):
    "Форма удаления по id категории, при условии отсутствия подкатегории"
    category_id = request.category_id
    try:
        logger.debug(f"Удаление категории с id: {category_id}")

        # Поиск категории
        category = await db.get(Category, category_id)
        if not category:
            logger.warning(f"Категория с id {category_id} не найдена")
            raise CategoryNotFound

        # Проверка на наличие подкатегорий
        subcategories = await db.execute(
            select(Category).where(Category.parent_id == category_id)
        )
        if subcategories.scalars().first():
            logger.warning(f"Категория с id {category_id} содержит подкатегории, удаление невозможно")
            raise CategoryContainsSubcategoriesDeletionIsNotPossible

        # Удаление категории
        await db.delete(category)
        await db.commit()

        logger.info(f"Категория с id {category_id} успешно удалена")

        # Используем model_validate для валидации объекта через атрибуты модели
        return CategoryResponse.model_validate(category)

    except Exception as e:
        logger.error(f"Ошибка при удалении категории: {e}")
        logger.error(traceback.format_exc())
        await db.rollback()  # Откат транзакции при ошибке
        raise FailedToDeleteCategory


@router_categories.post("/update",
                        response_model=List[CategoryResponse],
                        summary="Обновление категории или подкатегории")
@version(1)
async def update_categories(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_user)
):
    """Форма обновления категории или подкатегории"""
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        logger.debug(f"Полученные данные: {body_str}")

        try:
            category_data_list = json.loads(body_str)
            if not isinstance(category_data_list, list):
                raise InvalidDataFormat
            logger.debug(f"Преобразованные данные: {category_data_list}")
        except json.JSONDecodeError:
            logger.error(f"Ошибка декодирования JSON: {body_str}")
            raise JSONDecodingError

        updated_categories = await process_category_updates(db, category_data_list)

        logger.info(f"Успешно обновлено {len(updated_categories)} категорий")
        return updated_categories

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Ошибка IntegrityError при обновлении категорий: {e}")
        raise ErrorUpdatingCategories
    except Exception as e:
        logger.error(f"Ошибка при обновлении категорий: {e}")
        logger.error(traceback.format_exc())
        raise FailedToUpdateCategories




@router_question.get("/{question_id}/answer",
                     response_model=QuestionResponse,
                     summary="Создание ответа на поставленный вопрос")
@version(1)
async def get_question_answer(
        question_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Форма создания ответа на вопрос"""
    try:
        logger.debug(f"Получение вопроса с id: {question_id}")
        question = await db.get(Question, question_id)

        if not question:
            logger.warning(f"Вопрос с id {question_id} не найден")
            raise QuestionNotFound

        # Преобразуем вопрос в Pydantic модель для ответа
        response = QuestionResponse(
            id=question.id,
            text=question.text,
            answer=question.answer,
            category_id=question.category_id,
            number=question.number,
            sub_questions=[]  # Можно дополнить под-вопросами, если это необходимо
        )

        logger.info(f"Ответ на вопрос с id {question_id} успешно получен")
        return response

    except Exception as e:
        logger.error(f"Ошибка при получении ответа на вопрос: {e}")
        logger.error(traceback.format_exc())
        raise CouldNotGetAnswerToQuestion

