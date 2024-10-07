import asyncio
import traceback
from typing import List, Optional
from fastapi_versioning import version
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.admin.pagination_and_filtration import CustomParams
from app.dao.dependencies import get_current_admin_or_moderator_user, get_current_user
from app.database import get_db, async_session_maker
from app.exceptions import QuestionNotFound, ErrorInGetQuestions, \
    ErrorInGetQuestionWithSubquestions, SubQuestionNotFound, TheSubQuestionDoesNotBelongToTheSpecifiedMainQuestion, \
    CannotDeleteSubQuestionWithNestedSubQuestions, QuestionOrSubQuestionSuccessfullyDeleted, ErrorWhenDeletingQuestion, \
    SubQuestionSuccessfullyUpdated, QuestionSuccessfullyUpdated, ErrorWhenUpdatingQuestion
from app.logger.logger import logger
from app.questions.ML import search_similar_questions, model, tokenizer
from app.questions.dao_queestion import build_question_response, QuestionService, get_sub_questions, \
    build_subquestions_hierarchy, build_subquestion_response, update_main_question, update_sub_question
from app.questions.models import Question, SubQuestion
from app.questions.schemas import QuestionResponse, QuestionCreate, DeleteQuestionRequest, UpdateQuestionRequest, \
    QuestionIDRequest, QuestionResponseForPagination
from pydantic import ValidationError
from sqlalchemy import func
from app.questions.search_questions import QuestionSearchService, build_question_response_from_search

router_question = APIRouter(
    prefix="/question",
    tags=["Вопросы"],
)


# Эндпоинт для получения всех вопросов с вложенными под-вопросами

@router_question.get("/all-questions", response_model=List[QuestionResponse])
@version(1)
async def get_questions(db: AsyncSession = Depends(get_db),
                        current_user=Depends(get_current_user)):
    try:
        result = await db.execute(select(Question))
        questions = result.scalars().all()

        logger.info(f"Найденные вопросы: {[q.id for q in questions]}")  # Логируем найденные вопросы

        tasks = [get_sub_questions(db, question.id) for question in questions]
        sub_questions_list = await asyncio.gather(*tasks)

        logger.info(f"Найденные под-вопросы: {sub_questions_list}")  # Логируем найденные под-вопросы

        question_responses = []
        for question, sub_questions in zip(questions, sub_questions_list):
            hierarchical_sub_questions = build_subquestions_hierarchy(sub_questions)

            question_response = QuestionResponse(
                id=question.id,
                text=question.text,
                category_id=question.category_id,
                subcategory_id=question.subcategory_id,
                answer=question.answer,
                number=question.number,
                depth=question.depth,
                count=question.count,
                parent_question_id=question.parent_question_id,
                sub_questions=hierarchical_sub_questions
            )
            question_responses.append(question_response)

        return question_responses
    except Exception as e:
        logger.error(f"Ошибка в get_questions: {e}")
        raise ErrorInGetQuestions(detail=str(e))


@router_question.get("/pagination-questions",
                     status_code=status.HTTP_200_OK,
                     response_model=Page[QuestionResponseForPagination],
                     summary="Отображение всех вопросов верхнего уровня с пагинацией и поиском")
@version(1)
async def get_all_questions_or_search(params: CustomParams = Depends(),
                                      query: Optional[str] = None,  # Параметр для поиска
                                      category_id: Optional[int] = None,
                                      subcategory_id: Optional[int] = None,
                                      current_user=Depends(get_current_user)):
    """Получение всех вопросов верхнего уровня с пагинацией и поиском"""
    try:
        async with async_session_maker() as session:
            stmt = select(Question).filter(Question.parent_question_id.is_(None))  # Базовый запрос

            # Если передан query, выполняем поиск по тексту
            if query:
                stmt = stmt.filter(Question.text.ilike(f"%{query}%"))

            # Добавляем фильтрацию по category_id, если он указан
            if category_id is not None:
                stmt = stmt.filter(Question.category_id == category_id)

            # Добавляем фильтрацию по subcategory_id, если он указан
            if subcategory_id is not None:
                stmt = stmt.filter(Question.subcategory_id == subcategory_id)

            stmt = stmt.options(selectinload(Question.sub_questions))

            result = await session.execute(stmt)
            question_all = result.scalars().all()

        # Преобразуем вопросы в нужный формат ответа
        question_responses = [
            QuestionResponseForPagination(
                id=question.id,
                text=question.text,
                category_id=question.category_id,
                subcategory_id=question.subcategory_id,
                answer=question.answer,
                number=question.number,
                depth=question.depth,
                count=question.count,
                parent_question_id=question.parent_question_id,
                sub_questions=[],
                is_depth=True if question.depth > 0 or question.sub_questions else False  # Новое поле
            )
            for question in question_all
        ]

        # Применение кастомных параметров пагинации
        return paginate(question_responses, params=params)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router_question.post("/question_by_id", response_model=QuestionResponse)
@version(1)
async def get_question_with_subquestions(
        request_body: QuestionIDRequest,  # Принимаем тело запроса как один объект
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    try:
        question_id = request_body.question_id  # Получаем question_id из тела запроса

        # Проверка наличия question_id
        if question_id is None:
            raise HTTPException(status_code=400, detail="Отсутствует 'question_id' в запросе")

        # Получаем вопрос по ID
        question = await db.get(Question, question_id)
        if not question:
            raise QuestionNotFound

        # Увеличиваеем значение поля count на 1
        if question.count is None:
            question.count = 1
        else:
            question.count += 1

        await db.commit()

        # Получаем все подвопросы
        sub_questions = await get_sub_questions(db, question_id)

        # Формируем иерархию под-вопросов
        hierarchical_sub_questions = build_subquestions_hierarchy(sub_questions)

        # Формируем ответ с иерархией
        question_response = QuestionResponse(
            id=question.id,
            text=question.text,
            category_id=question.category_id,
            subcategory_id=question.subcategory_id,
            answer=question.answer,
            depth=question.depth,
            number=question.number,
            count=question.count,
            parent_question_id=question.parent_question_id,
            sub_questions=hierarchical_sub_questions  # Используем уже построенную иерархию
        )

        return question_response

    except Exception as e:
        logger.error(f"Ошибка в get_question_with_subquestions: {e}")
        raise ErrorInGetQuestionWithSubquestions(detail=str(e))


# Роут для создания вопроса или под вопроса
@router_question.post("/create", summary="Создание вопроса или подвопроса")
@version(1)
async def create_question(
        question: QuestionCreate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_or_moderator_user)
):
    try:
        logger.info("Создание нового вопроса с текстом: %s", question.text)

        if question.is_subquestion:
            if not question.parent_question_id:
                raise HTTPException(status_code=400, detail="Для подвопроса нужно указать parent_id")

            # Создаем подвопрос
            new_question = await QuestionService.create_subquestion(
                question=question,
                db=db
            )
            response = await build_subquestion_response(new_question)  # Изменение здесь
            logger.info(f"Создание подвопроса для родительского вопроса с ID: {question.parent_question_id}")
        else:
            # Создаем родительский вопрос
            new_question = await QuestionService.create_question(
                question=question,
                category_id=question.category_id,
                db=db
            )
            response = await build_question_response(new_question)  # Оставляем как есть
            logger.info("Создание родительского вопроса")

        # Возвращаем ответ
        logger.info("Вопрос успешно создан: %s", response)
        return response

    except ValidationError as ve:
        logger.error(f"Ошибка валидации данных ответа: {ve}")
        raise HTTPException(status_code=422, detail=f"Validation error: {ve.errors()}")
    except IntegrityError as e:
        await db.rollback()
        logger.error("IntegrityError при создании вопроса: %s", e)
        raise HTTPException(status_code=409, detail="Ошибка целостности данных: возможно, такой вопрос уже существует.")
    except Exception as e:
        logger.error("Ошибка при создании вопроса: %s", e)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Не удалось создать вопрос")


@router_question.post("/delete", summary="Удаление вопроса или под-вопроса")
@version(1)
async def delete_question(
        delete_request: DeleteQuestionRequest,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_or_moderator_user)
):
    """Удаление вопроса или под-вопроса по ID, если у него нет вложенных под-вопросов"""
    try:
        # Извлекаем ID основного вопроса и под-вопроса
        id_to_delete = delete_request.sub_question_id
        main_question_id = delete_request.question_id

        if id_to_delete > 0:  # Удаляем под-вопрос, если он указан
            # Удаляем под-вопрос
            sub_question = await db.get(SubQuestion, id_to_delete)
            if not sub_question:
                raise SubQuestionNotFound
            # Проверяем, принадлежит ли под-вопрос основному вопросу
            if sub_question.parent_question_id != main_question_id:
                raise TheSubQuestionDoesNotBelongToTheSpecifiedMainQuestion
            # Проверяем наличие вложенных под-вопросов в базе данных
            sub_questions_count = await db.execute(
                select(func.count()).where(SubQuestion.parent_subquestion_id == id_to_delete))
            if sub_questions_count.scalar() > 0:
                raise CannotDeleteSubQuestionWithNestedSubQuestions
            # Удаляем под-вопрос
            await db.delete(sub_question)
        else:  # Удаляем основной вопрос, если sub_question_id не указан или равен 0
            # Удаляем основной вопрос
            question = await db.get(Question, main_question_id)
            if not question:
                raise QuestionNotFound
            # Проверяем наличие под-вопросов у основного вопроса
            question_sub_questions_count = await db.execute(
                select(func.count()).where(SubQuestion.parent_question_id == main_question_id))
            if question_sub_questions_count.scalar() > 0:
                raise CannotDeleteSubQuestionWithNestedSubQuestions
            # Удаляем основной вопрос
            await db.delete(question)

        await db.commit()
        return QuestionOrSubQuestionSuccessfullyDeleted
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при удалении вопроса: {e}")
        raise ErrorWhenDeletingQuestion


@router_question.post("/update", summary="Обновление вопроса или под-вопроса")
@version(1)
async def update_question(
        update_request: UpdateQuestionRequest,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_or_moderator_user)
):
    """Обновление текста и ответа вопроса или под-вопроса"""
    try:
        # Определяем, обновляем основной вопрос или под-вопрос
        if update_request.sub_question_id and update_request.sub_question_id > 0:
            await update_sub_question(update_request, db)
            return SubQuestionSuccessfullyUpdated
        else:
            await update_main_question(update_request, db)
            return QuestionSuccessfullyUpdated

    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при обновлении вопроса: {e}")
        raise ErrorWhenUpdatingQuestion


@router_question.get("/search", response_model=List[QuestionResponse])
@version(1)
async def search_questions(
        query: str,
        db: AsyncSession = Depends(get_db)
):
    """Поиск вопросов по тексту"""
    try:
        questions = await QuestionSearchService.search_questions(
            db,
            query,
        )

        if not questions:
            logger.info("Вопросы не найдены")
            return []

        # Словарь для вопросов по id
        question_dict = {question.id: question for question in questions}

        # Создание иерархии под-вопросов для каждого основного вопроса
        question_responses = [
            await build_question_response_from_search(question, db) for question in questions if question.parent_question_id is None
        ]

        return question_responses
    except Exception as e:
        logger.error(f"Ошибка при поиске вопросов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка поиска вопросов")


@router_question.get("/similar", response_model=List[QuestionResponse])
async def get_similar_questions(query: str, db: AsyncSession = Depends(get_db)):
    """Поиск похожих вопросов по тексту запроса"""
    try:
        similar_questions = await search_similar_questions(query, db, model, tokenizer)

        if not similar_questions:
            return []

        # Преобразование результатов поиска в формат ответа
        response = [QuestionResponse.model_validate(question) for question in similar_questions]
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))