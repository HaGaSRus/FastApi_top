import asyncio
import traceback
from typing import List
from fastapi_versioning import version
from fastapi import APIRouter, Depends, Path, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.dao.dao import QuestionsDAO
from app.dao.dependencies import get_current_user
from app.database import get_db
from app.exceptions import DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists, \
    FailedToCreateQuestion, CouldNotGetAnswerToQuestion, FailedToRetrieveQuestions
from app.logger.logger import logger
from app.questions.dao_queestion import get_similar_questions_cosine, calculate_similarity, \
    convert_question_to_response, build_question_response, QuestionService
from app.questions.models import Question, SubQuestion, Category
from app.questions.schemas import QuestionResponse, QuestionCreate, DynamicAnswerResponse, \
    SimilarQuestionResponse, DynamicSubAnswerResponse, QuestionAllResponse
from sqlalchemy.orm import selectinload
from pydantic import ValidationError

router_question = APIRouter(
    prefix="/question",
    tags=["Вопросы"],
)


# Создание вопроса верхнего уровня
@router_question.get("", response_model=List[QuestionResponse], summary="Получение списка вопросов по категории")
@version(1)
async def get_questions_by_category(
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    try:
        logger.info("Получение списка вопросов")

        # Получаем все родительские вопросы с под-вопросами
        questions_result = await db.execute(
            select(Question)
            .options(selectinload(Question.sub_questions))  # Загружаем под-вопросы
            .where(Question.parent_question_id.is_(None))  # Только корневые вопросы
        )
        parent_questions = questions_result.scalars().all()

        # Используем await для преобразования родительских вопросов
        response = await asyncio.gather(
            *(convert_question_to_response(parent_question, parent_question.sub_questions) for parent_question in parent_questions)
        )

        logger.info("Список вопросов успешно получен: %s", response)
        return response
    except Exception as e:
        logger.error("Ошибка при получении списка вопросов: %s", e)
        logger.error(traceback.format_exc())
        raise FailedToRetrieveQuestions



# Роут для создания вопроса или под вопроса
@router_question.post("/questions", summary="Создание вопроса или подвопроса")
@version(1)
async def create_question(
    question: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        logger.info("Создание нового вопроса с текстом: %s", question.text)

        if question.is_subquestion:
            if not question.parent_question_id:
                raise HTTPException(status_code=400, detail="Для подвопроса нужно указать parent_id")

            # Создаем подвопрос
            new_question = await QuestionService.create_subquestion(
                question=question,
                parent_question_id=question.parent_question_id,
                db=db
            )
            logger.info(f"Создание подвопроса для родительского вопроса с ID: {question.parent_question_id}")
        else:
            # Создаем родительский вопрос
            new_question = await QuestionService.create_question(
                question=question,
                category_id=question.category_id,  # Используем category_id из тела запроса
                db=db
            )
            logger.info("Создание родительского вопроса")

        # Формируем ответ
        response = await build_question_response(new_question)
        logger.info("Вопрос успешно создан: %s", response)
        return response

    except ValidationError as ve:
        logger.error(f"Ошибка валидации данных ответа: {ve}")
        raise HTTPException(status_code=422, detail=f"Validation error: {ve.errors()}")
    except IntegrityError as e:
        await db.rollback()
        logger.error("IntegrityError при создании вопроса: %s", e)
        raise DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists
    except Exception as e:
        logger.error("Ошибка при создании вопроса: %s", e)
        logger.error(traceback.format_exc())  # Логирование полного стека вызовов
        raise HTTPException(status_code=500, detail="Не удалось создать вопрос")


@router_question.get("/answer",
                     response_model=DynamicAnswerResponse,
                     summary="Получение ответа на вопрос по тексту")
@version(1)
async def get_question_answer(
        question_text: str = Query(..., description="Текст вопроса"),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Форма получения ответа на вопрос по тексту"""

    try:
        logger.debug(f"Получение ответа на вопрос: {question_text}")

        # Получаем похожие вопросы с порогом 0.2
        similar_questions = await get_similar_questions_cosine(question_text, db, min_similarity=0.2)

        # Получаем вопрос по тексту
        question_result = await db.execute(select(Question).where(Question.text == question_text))
        question = question_result.scalars().first()

        response_sub_questions = []

        # Формируем базовый список похожих вопросов
        if similar_questions:
            response_sub_questions = [
                SimilarQuestionResponse(
                    id=q.id,
                    question_text=q.text,
                    similarity_score=calculate_similarity(q.text, question_text),
                ) for q in similar_questions
            ]

        if question:
            has_answer = question.answer is not None

            # Если найден вопрос, добавляем его в начало списка
            response_sub_questions.insert(0, SimilarQuestionResponse(
                id=question.id,
                question_text=question.text,
                similarity_score=1.0  # 100% совпадение
            ))

            # Сортируем sub_questions от максимального совпадения к наименьшему
            response_sub_questions = sorted(response_sub_questions, key=lambda x: x.similarity_score, reverse=True)

            response = DynamicAnswerResponse(
                id=question.id,
                text=question.text,
                has_answer=has_answer,
                answer=question.answer if has_answer else None,
                category_id=question.category_id,
                number=question.number,
                sub_questions=response_sub_questions
            )

            logger.info(f"Ответ на вопрос '{question_text}' успешно получен")
            return response
        else:
            logger.warning(f"Вопрос с текстом '{question_text}' не найден")

            if not response_sub_questions:
                raise HTTPException(status_code=404, detail="Нет ответа на такой вопрос.")

            # Сортируем sub_questions от максимального совпадения к наименьшему
            response_sub_questions = sorted(response_sub_questions, key=lambda x: x.similarity_score, reverse=True)

            response = DynamicSubAnswerResponse(
                id=None,
                text=f"Вопрос '{question_text}' не найден, но вот похожие вопросы:",
                has_answer=False,
                answer=None,
                category_id=None,
                number=None,
                sub_questions=response_sub_questions
            )

            return response

    except Exception as e:
        logger.error(f"Ошибка при получении ответа на вопрос: {e}")
        logger.error(traceback.format_exc())
        raise CouldNotGetAnswerToQuestion


@router_question.post("/delete/{question_id}", summary="Удаление вопроса")
async def delete_question(
        question_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Удаление вопроса по ID с каскадным удалением под-вопросов"""
    try:
        question = await db.get(Question, question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Вопрос не найден")

        # Удаляем все под-вопросы, если они есть
        if question.sub_questions:
            for sub_question in question.sub_questions:
                await db.delete(sub_question)

        # Удаление основного вопроса
        await db.delete(question)
        await db.commit()
        return {"detail": "Вопрос и его под-вопросы успешно удалены"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при удалении вопроса: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router_question.post("/update/{question_id}", response_model=QuestionResponse, summary="Обновление вопроса")
@version(1)
async def update_question(
        question_data: QuestionCreate,
        question_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Обновление вопроса по ID"""
    try:
        question = await db.get(Question, question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Вопрос не найден")

        # Обновляем поля вопроса
        for key, value in question_data.dict(exclude_unset=True).items():
            setattr(question, key, value)

        await db.commit()
        return QuestionResponse.model_validate(question)
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при обновлении вопроса: {e}")
        raise HTTPException(status_code=400, detail=str(e))
