import asyncio
import io
import os
import time
import traceback
from PIL import Image
from typing import List, Optional
from fastapi_versioning import version
from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
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
    SubQuestionSuccessfullyUpdated, QuestionSuccessfullyUpdated, ErrorWhenUpdatingQuestion, ErrorSearchingQuestions, \
    ErrorReceivingDataForDashboard, ErrorWhileSaving, QuestionSearchNotFound
from app.logger.logger import logger
from app.questions.dao_queestion import build_question_response, QuestionService, get_sub_questions, \
    build_subquestions_hierarchy, build_subquestion_response, update_main_question, update_sub_question
from app.questions.models import Question, SubQuestion
from app.questions.schemas import QuestionResponse, QuestionCreate, DeleteQuestionRequest, UpdateQuestionRequest, \
    QuestionIDRequest, QuestionResponseForPagination, QuestionSearchResponse
from pydantic import ValidationError
from sqlalchemy import func
from app.questions.search_questions import build_question_response_from_search, QuestionSearchService

router_question = APIRouter(
    prefix="/question",
    tags=["Вопросы"],
)


@router_question.get("/all-questions", response_model=List[QuestionResponse])
@version(1)
async def get_questions(db: AsyncSession = Depends(get_db),
                        current_user=Depends(get_current_user)):
    try:
        result = await db.execute(select(Question))
        questions = result.scalars().all()

        tasks = [get_sub_questions(db, question.id) for question in questions]
        sub_questions_list = await asyncio.gather(*tasks)

        question_responses = []
        for question, sub_questions in zip(questions, sub_questions_list):
            hierarchical_sub_questions = build_subquestions_hierarchy(sub_questions)

            question_response = QuestionResponse(
                id=question.id,
                author=question.author,
                author_edit=question.author_edit,
                created_at=question.created_at,
                updated_at=question.updated_at,
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
        logger.warning(f"Ошибка в get_questions: {e}")
        raise ErrorInGetQuestions(detail=str(e))


@router_question.get("/pagination-questions",
                     status_code=status.HTTP_200_OK,
                     response_model=Page[QuestionResponseForPagination],
                     summary="Отображение всех вопросов верхнего уровня с пагинацией и поиском")
@version(1)
async def get_all_questions_or_search(params: CustomParams = Depends(),
                                      query: Optional[str] = None,
                                      category_id: Optional[int] = None,
                                      subcategory_id: Optional[int] = None,
                                      current_user=Depends(get_current_user)):
    """Получение всех вопросов верхнего уровня с пагинацией и поиском"""
    try:
        async with async_session_maker() as session:
            stmt = select(Question).filter(Question.parent_question_id.is_(None))
            if query:
                stmt = stmt.filter(Question.text.ilike(f"%{query}%"))

            if category_id is not None:
                stmt = stmt.filter(Question.category_id == category_id)

            if subcategory_id is not None:
                stmt = stmt.filter(Question.subcategory_id == subcategory_id)

            stmt = stmt.options(selectinload(Question.sub_questions))

            result = await session.execute(stmt)
            question_all = result.scalars().all()

        question_responses = [
            QuestionResponseForPagination(
                id=question.id,
                author=question.author,
                author_edit=question.author_edit,
                created_at=question.created_at,
                updated_at=question.updated_at,
                text=question.text,
                category_id=question.category_id,
                subcategory_id=question.subcategory_id,
                answer=question.answer,
                number=question.number,
                depth=question.depth,
                count=question.count,
                parent_question_id=question.parent_question_id,
                sub_questions=[],
                is_depth=True if question.depth > 0 or question.sub_questions else False
            )
            for question in question_all
        ]

        return paginate(question_responses, params=params)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router_question.post("/question_by_id", response_model=QuestionResponse)
@version(1)
async def get_question_with_subquestions(
        request_body: QuestionIDRequest,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    try:
        question_id = request_body.question_id

        if question_id is None:
            raise HTTPException(status_code=400, detail="Отсутствует 'question_id' в запросе")

        question = await db.get(Question, question_id)
        if not question:
            raise QuestionNotFound

        if question.count is None:
            question.count = 1
        else:
            question.count += 1

        await db.commit()

        sub_questions = await get_sub_questions(db, question_id)

        hierarchical_sub_questions = build_subquestions_hierarchy(sub_questions)

        question_response = QuestionResponse(
            id=question.id,
            author=question.author,
            author_edit=question.author_edit,
            created_at=question.created_at,
            updated_at=question.updated_at,
            text=question.text,
            category_id=question.category_id,
            subcategory_id=question.subcategory_id,
            answer=question.answer,
            depth=question.depth,
            number=question.number,
            count=question.count,
            parent_question_id=question.parent_question_id,
            sub_questions=hierarchical_sub_questions
        )

        return question_response

    except Exception as e:
        logger.warning(f"Ошибка в get_question_with_subquestions: {e}")
        raise ErrorInGetQuestionWithSubquestions(detail=str(e))


@router_question.post("/create", summary="Создание вопроса или подвопроса")
@version(1)
async def create_question(
        question: QuestionCreate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_or_moderator_user)
):
    try:

        if question.is_subquestion:
            if not question.parent_question_id:
                raise HTTPException(status_code=400, detail="Для подвопроса нужно указать parent_id")

            new_question = await QuestionService.create_subquestion(
                question=question,
                db=db
            )
            response = await build_subquestion_response(new_question)
        else:
            new_question = await QuestionService.create_question(
                question=question,
                category_id=question.category_id,
                db=db
            )
            response = await build_question_response(new_question)

        return response

    except ValidationError as ve:
        logger.warning(f"Ошибка валидации данных ответа: {ve}")
        raise HTTPException(status_code=422, detail=f"Validation error: {ve.errors()}")
    except IntegrityError as e:
        await db.rollback()
        logger.warning("IntegrityError при создании вопроса: %s", e)
        raise HTTPException(status_code=409, detail="Ошибка целостности данных: возможно, такой вопрос уже существует.")
    except Exception as e:
        logger.warning("Ошибка при создании вопроса: %s", e)
        logger.warning(traceback.format_exc())
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
        id_to_delete = delete_request.sub_question_id
        main_question_id = delete_request.question_id

        if id_to_delete > 0:
            sub_question = await db.get(SubQuestion, id_to_delete)
            if not sub_question:
                raise SubQuestionNotFound
            if sub_question.parent_question_id != main_question_id:
                raise TheSubQuestionDoesNotBelongToTheSpecifiedMainQuestion
            sub_questions_count = await db.execute(
                select(func.count()).where(SubQuestion.parent_subquestion_id == id_to_delete))
            if sub_questions_count.scalar() > 0:
                raise CannotDeleteSubQuestionWithNestedSubQuestions
            await db.delete(sub_question)
        else:
            question = await db.get(Question, main_question_id)
            if not question:
                raise QuestionNotFound
            question_sub_questions_count = await db.execute(
                select(func.count()).where(SubQuestion.parent_question_id == main_question_id))
            if question_sub_questions_count.scalar() > 0:
                raise CannotDeleteSubQuestionWithNestedSubQuestions
            await db.delete(question)

        await db.commit()
        return QuestionOrSubQuestionSuccessfullyDeleted
    except Exception as e:
        await db.rollback()
        logger.warning(f"Ошибка при удалении вопроса: {e}")
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
        if update_request.sub_question_id and update_request.sub_question_id > 0:
            await update_sub_question(update_request, db)
            return SubQuestionSuccessfullyUpdated
        else:
            await update_main_question(update_request, db)
            return QuestionSuccessfullyUpdated

    except Exception as e:
        await db.rollback()
        logger.warning(f"Ошибка при обновлении вопроса: {e}")
        raise ErrorWhenUpdatingQuestion


@router_question.get("/search", response_model=List[QuestionResponse])
@version(1)
async def search_questions(
        query: str,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """Поиск вопросов по тексту"""
    try:
        questions = await QuestionSearchService.search_questions(
            db,
            query,
        )

        if not questions:
            return []

        question_dict = {question.id: question for question in questions}

        question_responses = [
            await build_question_response_from_search(question, db) for question in questions if
            question.parent_question_id is None
        ]

        return question_responses
    except Exception as e:
        logger.warning(f"Ошибка при поиске вопросов: {e}")
        raise HTTPException(status_code=500, detail="Ошибка поиска вопросов")


@router_question.get("/search-fuzzy_search", status_code=status.HTTP_200_OK, response_model=List[QuestionSearchResponse])
@version(1)
async def search_questions(
        query: str,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user)
    ):
    try:
        results = await QuestionSearchService.search_questions_fuzzy_search(db, query)
        if not results:
            raise QuestionSearchNotFound
        return results
    except QuestionSearchNotFound:
        raise
    except Exception as e:
        logger.warning(f"Ошибка при поиске: {e}")
        raise ErrorSearchingQuestions


@router_question.get("/top_question_count", summary="Получить count верхнеуровневых вопросов с количеством запросов")
@version(1)
async def get_top_questions_count(
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_or_moderator_user)
):
    """Возвращает количество верхнеуровневых вопросов и количество их запросов"""
    try:
        result = await db.execute(
            select(Question.id, Question.text, Question.count)
            .where(Question.parent_question_id.is_(None))
        )

        top_questions = result.fetchall()

        if not top_questions:
            return {"top_questions_count": 0, "questions": []}

        questions_data = [
            {"id": question.id, "text": question.text, "count": question.count}
            for question in top_questions
        ]

        return {
            "top_questions_count": len(questions_data),
            "questions": questions_data
        }

    except Exception as e:
        logger.warning(f"Ошибка при получении count верхнеуровневых вопросов: {e}")
        raise ErrorReceivingDataForDashboard


@router_question.post('/upload-binary')
@version(1)
async def add_photo_router(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    os.makedirs("public", exist_ok=True)
    unix_time = int(time.time())

    try:
        image = Image.open(io.BytesIO(await file.read()))

        file_extension = file.filename.split(".")[-1].lower()

        if file_extension in ["jpeg", "jpg"]:
            compressed_image = io.BytesIO()
            image.save(compressed_image, format="JPEG", quality=70)
            file_location = f"public/{unix_time}_{file.filename.split('.')[0]}.jpg"

        elif file_extension in ["png"]:
            compressed_image = io.BytesIO()
            image.save(compressed_image, format="WebP", quality=80)
            file_location = f"public/{unix_time}_{file.filename.split('.')[0]}.webp"

        else:
            compressed_image = io.BytesIO()
            image.save(compressed_image, format="WebP", quality=80)
            file_location = f"public/{unix_time}_{file.filename.split('.')[0]}.webp"

        with open(file_location, "wb") as photo_obj:
            photo_obj.write(compressed_image.getvalue())

        return {"url": f"https://ht-server.dz72.ru/{file_location}"}

    except Exception as e:
        logger.warning(f"Ошибка при сохранении: {str(e)}")
        raise ErrorWhileSaving(f"Ошибка сохранения: {str(e)}")
