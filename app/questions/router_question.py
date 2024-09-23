import traceback
from typing import Optional
from fastapi_versioning import version
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.dao.dependencies import get_current_user
from app.database import get_db
from app.exceptions import CategoryNotFound, DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists, \
    FailedToCreateQuestion, ParentQuestionNotFound, FailedToCreateSubQuestion, \
    QuestionNotFound, CouldNotGetAnswerToQuestion
from app.logger.logger import logger
from app.questions.models import Question
from app.questions.schemas import QuestionResponse, QuestionCreate
from app.questions.utils import get_category_by_id


router_question = APIRouter(
    prefix="/question",
    tags=["Вопросы"],
)


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




