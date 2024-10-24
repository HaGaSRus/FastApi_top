import traceback
from datetime import datetime
from typing import List
from fastapi import HTTPException
from app.exceptions import CategoryNotFound, ForASubquestionYouMustSpecifyParentQuestionId, \
    FailedToCreateQuestionDynamic, ParentQuestionIDNotFound, IncorrectParentSubquestionIdValueNumberExpected, \
    ErrorCreatingSubquestion, SubQuestionNotFound, TheSubQuestionDoesNotBelongToTheSpecifiedMainQuestion, \
    QuestionNotFound
from app.logger.logger import logger
from app.questions.models import Question, SubQuestion
from app.questions.schemas import QuestionCreate, SubQuestionCreate, SubQuestionResponse, QuestionResponse, \
    UpdateQuestionRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.questions.utils import get_category_by_id


class QuestionService:
    @staticmethod
    async def create_question(
            question: QuestionCreate,
            category_id: int,
            db: AsyncSession
    ) -> Question:
        try:
            category = await get_category_by_id(category_id, db)
            if not category:
                raise CategoryNotFound

            if question.is_subquestion:
                if not question.parent_question_id:
                    raise ForASubquestionYouMustSpecifyParentQuestionId(
                        detail="Для подвопроса необходимо указать parent_question_id.")

                return await QuestionService.create_subquestion(
                    question=question,
                    db=db
                )

            new_question = Question(
                text=question.text,
                author=question.author,
                answer=question.answer,
                category_id=category_id,
                subcategory_id=question.subcategory_id,
                parent_question_id=None,
                depth=0
            )

            db.add(new_question)
            await db.commit()
            await db.refresh(new_question)

            new_question.number = new_question.id
            await db.commit()

            return new_question

        except Exception as e:
            logger.warning(f"Ошибка при создании вопроса: {e}")
            logger.warning(traceback.format_exc())
            raise FailedToCreateQuestionDynamic(detail=f"Не удалось создать вопрос: {str(e)}")

    @staticmethod
    async def create_subquestion(question: SubQuestionCreate, db: AsyncSession) -> SubQuestion:
        try:
            parent_question = await db.get(Question, question.parent_question_id)
            if not parent_question:
                error_message = f"Родительский вопрос с ID {question.parent_question_id} не найден."
                logger.warning(error_message)
                raise ParentQuestionIDNotFound(detail=error_message)

            depth = parent_question.depth + 1

            if question.parent_subquestion_id:
                parent_subquestion = await db.get(SubQuestion, question.parent_subquestion_id)
                if parent_subquestion:
                    depth = parent_subquestion.depth + 1
                else:
                    error_message = f"Родительский подвопрос с ID {question.parent_subquestion_id} не найден."
                    logger.warning(error_message)
                    raise ParentQuestionIDNotFound(detail=error_message)

            if question.parent_subquestion_id is not None and not isinstance(question.parent_subquestion_id, int):
                error_message = "Некорректное значение parent_subquestion_id, ожидается число."
                logger.warning(error_message)
                raise IncorrectParentSubquestionIdValueNumberExpected(detail=error_message)

            new_sub_question = SubQuestion(
                author=question.author,
                text=question.text,
                answer=question.answer,
                parent_question_id=parent_question.id,
                depth=depth,
                number=0,
                category_id=question.category_id,
                subcategory_id=question.subcategory_id,
                parent_subquestion_id=question.parent_subquestion_id if question.parent_subquestion_id and question.parent_subquestion_id > 0 else None
            )

            db.add(new_sub_question)
            await db.commit()
            await db.refresh(new_sub_question)

            new_sub_question.number = new_sub_question.id
            await db.commit()

            return new_sub_question

        except HTTPException as e:
            logger.warning(f"HTTP ошибка: {e.detail}")
            raise e

        except Exception as e:
            logger.warning(f"Ошибка при создании подвопроса: {e}")
            logger.warning(traceback.format_exc())
            raise ErrorCreatingSubquestion(detail=f"Не удалось создать подвопрос: {str(e)}")


async def build_question_response(question: Question) -> QuestionResponse:
    response = QuestionResponse(
        id=question.id,
        author=question.author,
        text=question.text,
        answer=question.answer,
        number=question.number,
        count=question.count,
        depth=question.depth,
        parent_question_id=question.parent_question_id,
        category_id=question.category_id,
        subcategory_id=question.subcategory_id,
        created_at=question.created_at,
        updated_at=question.updated_at,
        sub_questions=[]
    )

    for sub_question in question.sub_questions:
        sub_response = await build_subquestion_response(sub_question)
        response.sub_questions.append(sub_response)

    return response


async def build_subquestion_response(sub_question: SubQuestion) -> SubQuestionResponse:
    return SubQuestionResponse(
        id=sub_question.id,
        author=sub_question.author,
        text=sub_question.text,
        answer=sub_question.answer,
        number=sub_question.number,
        count=sub_question.count,
        parent_question_id=sub_question.parent_question_id,
        depth=sub_question.depth,
        category_id=sub_question.category_id,
        subcategory_id=sub_question.subcategory_id,
        parent_subquestion_id=sub_question.parent_subquestion_id,
        created_at=sub_question.created_at,
        updated_at=sub_question.updated_at,
        sub_questions=[]
    )


async def get_sub_questions(db: AsyncSession, parent_question_id: int) -> List[SubQuestionResponse]:
    try:
        result = await db.execute(select(SubQuestion).where(SubQuestion.parent_question_id == parent_question_id))
        sub_questions = result.scalars().all()

        sub_question_responses = [
            SubQuestionResponse(
                id=sub_question.id,
                author=sub_question.author,
                text=sub_question.text,
                answer=sub_question.answer,
                number=sub_question.number,
                count=sub_question.count,
                parent_question_id=sub_question.parent_question_id,
                depth=sub_question.depth,
                created_at=sub_question.created_at,
                updated_at=sub_question.updated_at,
                category_id=sub_question.category_id,
                subcategory_id=sub_question.subcategory_id,
                parent_subquestion_id=sub_question.parent_subquestion_id,
                sub_questions=[]
            )
            for sub_question in sub_questions
        ]

        return sub_question_responses
    except Exception as e:
        logger.warning(f"Ошибка в get_sub_questions: {e}")
        raise


def build_subquestions_hierarchy(sub_questions, parent_question_id=None):
    hierarchy = []
    for sub_question in sub_questions:
        if sub_question.parent_subquestion_id == parent_question_id:
            sub_question.sub_questions = build_subquestions_hierarchy(sub_questions, sub_question.id)
            hierarchy.append(sub_question)
    return hierarchy


async def update_sub_question(update_request: UpdateQuestionRequest, db: AsyncSession):
    """Обновление под-вопроса"""
    sub_question = await db.get(SubQuestion, update_request.sub_question_id)
    if not sub_question:
        raise SubQuestionNotFound

    if sub_question.parent_question_id != update_request.question_id:
        raise TheSubQuestionDoesNotBelongToTheSpecifiedMainQuestion

    update_fields(sub_question, update_request)

    await db.commit()


async def update_main_question(update_request: UpdateQuestionRequest, db: AsyncSession):
    """Обновление вопроса"""
    question = await db.get(Question, update_request.question_id)
    if not question:
        raise QuestionNotFound

    update_fields(question, update_request)

    await db.commit()


def update_fields(question_obj, update_request: UpdateQuestionRequest):
    """Обновление полей text, answer и author"""

    if update_request.text is not None:
        question_obj.text = update_request.text

    if update_request.answer is not None:
        question_obj.answer = update_request.answer

    if update_request.author is not None:
        question_obj.author = update_request.author


def format_datetime(dt: datetime) -> str:
    if dt:
        return dt.strftime("%d %B %Y, %H:%M")  # Пример: 24 October 2024, 15:36
    return None

