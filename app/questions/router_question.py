import traceback
from typing import Optional, List
from fastapi_versioning import version
from fastapi import APIRouter, Depends, Path, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload, Session
from app.dao.dao import QuestionsDAO
from app.dao.dependencies import get_current_user
from app.database import get_db
from app.exceptions import CategoryNotFound, DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists, \
    FailedToCreateQuestion, ParentQuestionNotFound, FailedToCreateSubQuestion, \
    QuestionNotFound, CouldNotGetAnswerToQuestion
from app.logger.logger import logger
from app.questions.dao_queestion import QuestionService, get_similar_questions_cosine, calculate_similarity
from app.questions.models import Question, Category, SubQuestion
from app.questions.schemas import QuestionResponse, QuestionCreate, DynamicAnswerResponse, SubQuestionResponse, \
    SimilarQuestionResponse, DynamicSubAnswerResponse, QuestionAllResponse
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
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    try:
        logger.info("Создание нового вопроса")
        new_question = Question(text=question.text, category_id=category_id, answer=question.answer)
        db.add(new_question)
        await db.commit()

        # Устанавливаем значение number на основе ID
        new_question.number = new_question.id
        await db.commit()  # Коммитим изменения

        if question.sub_questions:
            logger.info("Создание под-вопросов")
            for sub in question.sub_questions:
                new_sub_question = SubQuestion(
                    question_id=new_question.id,
                    text=sub.text,
                    answer=sub.answer,
                    depth=sub.depth
                )
                db.add(new_sub_question)
            await db.commit()
            logger.info("Под-вопросы успешно созданы")

        # Обновляем sub_questions в new_question
        await db.refresh(new_question)  # Обновляем состояние new_question

        # Получаем список под-вопросов
        sub_questions_result = await db.execute(select(SubQuestion).filter_by(question_id=new_question.id))
        new_question.sub_questions = sub_questions_result.scalars().all()  # Преобразуем в список

        return new_question
    except IntegrityError:
        await db.rollback()
        logger.error("IntegrityError при создании вопроса")
        raise DataIntegrityErrorPerhapsQuestionWithThisTextAlreadyExists
    except Exception as e:
        logger.error(f"Ошибка при создании вопроса: {e}")
        logger.error(traceback.format_exc())
        raise FailedToCreateQuestion


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


@router_question.get("", response_model=List[QuestionAllResponse], summary="Получение всех вопросов")
@version(1)
async def get_all_questions(db: AsyncSession = Depends(get_db)):
    try:
        questions = await QuestionsDAO.get_all_questions(db)
        logger.info(f"Отправка ответа: {questions}")
        return questions
    except Exception as e:
        logger.error("Ошибка при получении вопросов: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


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
        current_user = Depends(get_current_user)
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

