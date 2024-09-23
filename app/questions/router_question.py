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
from app.questions.dao_queestion import QuestionService
from app.questions.models import Question, Category
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
        subcategory_id: Optional[int] = Query(None, description="ID подкатегории"),
        parent_question_id: Optional[int] = Query(None, description="ID родительского вопроса"),  # Новый параметр
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Форма создания вопроса верхнего уровня"""
    try:
        # Обработка категории
        category = await get_category_by_id(category_id, db)
        if not category:
            raise CategoryNotFound

        # Если указана подкатегория, получить её
        if subcategory_id:
            subcategory = await db.get(Category, subcategory_id)
            if not subcategory or subcategory.parent_id != category_id:
                raise CategoryNotFound  # подкатегория не найдена или не принадлежит родительской

        new_question = await QuestionService.create_question(question,
                                                             subcategory_id if subcategory_id else category_id,
                                                             parent_question_id,
                                                             db)

        return QuestionResponse(
                id=new_question.id,
                text=new_question.text,
                answer=new_question.answer,
                category_id=subcategory_id if subcategory_id else new_question.category_id,
                number=new_question.number,
                count=new_question.count,
                sub_questions=[])
    except IntegrityError:
        await db.rollback()
        logger.error("IntegrityError при создании вопроса")
        raise DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists
    except Exception as e:
        logger.error(f"Ошибка при создании вопроса: {e}")
        logger.error(traceback.format_exc())
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
        new_question = await QuestionService.create_subquestion(question, parent_question_id, db)
        return QuestionResponse(
            id=new_question.id,
            text=new_question.text,
            answer=new_question.answer,
            category_id=new_question.category_id,
            number=new_question.number,
            count=new_question.count,
            sub_questions=[]
        )
    except IntegrityError:
        await db.rollback()
        logger.error("IntegrityError при создании под-вопроса")
        raise DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при создании под-вопроса: {e}")
        logger.error(traceback.format_exc())
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




