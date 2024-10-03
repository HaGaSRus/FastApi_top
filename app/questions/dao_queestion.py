import traceback
from typing import List
from fastapi import HTTPException
from app.exceptions import CategoryNotFound, ForASubquestionYouMustSpecifyParentQuestionId, \
    FailedToCreateQuestionDynamic, ParentQuestionIDNotFound, IncorrectParentSubquestionIdValueNumberExpected, \
    ErrorCreatingSubquestion
from app.logger.logger import logger
from app.questions.models import Question, SubQuestion
from app.questions.schemas import QuestionCreate, SubQuestionCreate, SubQuestionResponse, QuestionResponse
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
            # Получаем категорию по ID
            category = await get_category_by_id(category_id, db)
            if not category:
                raise CategoryNotFound

            # Проверяем, подвопрос ли это
            if question.is_subquestion:
                if not question.parent_question_id:
                    raise ForASubquestionYouMustSpecifyParentQuestionId(
                        detail="Для подвопроса необходимо указать parent_question_id.")

                # Логируем попытку создания подвопроса
                logger.info(f"Попытка создания подвопроса с parent_question_id: {question.parent_question_id}")
                # Передаём управление на функцию создания подвопроса
                return await QuestionService.create_subquestion(
                    question=question,
                    db=db
                )

            # Создание основного вопроса
            new_question = Question(
                text=question.text,
                answer=question.answer,
                category_id=category_id,
                subcategory_id=question.subcategory_id,
                parent_question_id=None,  # Это родительский вопрос
                depth=0
            )

            # Добавляем новый вопрос в сессию
            db.add(new_question)
            await db.commit()  # Коммитим изменения
            await db.refresh(new_question)  # Обновляем объект

            # Устанавливаем поле number равным id и коммитим изменения
            new_question.number = new_question.id
            await db.commit()

            return new_question

        except Exception as e:
            logger.error(f"Ошибка при создании вопроса: {e}")
            logger.error(traceback.format_exc())  # Логирование полного стека вызовов
            raise FailedToCreateQuestionDynamic(detail=f"Не удалось создать вопрос: {str(e)}")

    @staticmethod
    async def create_subquestion(question: SubQuestionCreate, db: AsyncSession) -> SubQuestion:
        try:
            # Проверка наличия родительского вопроса
            parent_question = await db.get(Question, question.parent_question_id)
            if not parent_question:
                error_message = f"Родительский вопрос с ID {question.parent_question_id} не найден."
                logger.error(error_message)
                raise ParentQuestionIDNotFound(detail=error_message)

            # Устанавливаем значение depth для вложенности
            depth = parent_question.depth + 1

            # Если есть родительский подвопрос
            if question.parent_subquestion_id:
                parent_subquestion = await db.get(SubQuestion, question.parent_subquestion_id)
                if parent_subquestion:
                    depth = parent_subquestion.depth + 1
                else:
                    error_message = f"Родительский подвопрос с ID {question.parent_subquestion_id} не найден."
                    logger.error(error_message)
                    raise ParentQuestionIDNotFound(detail=error_message)

            # Проверка на корректность parent_subquestion_id
            if question.parent_subquestion_id is not None and not isinstance(question.parent_subquestion_id, int):
                error_message = "Некорректное значение parent_subquestion_id, ожидается число."
                logger.error(error_message)
                raise IncorrectParentSubquestionIdValueNumberExpected(detail=error_message)

            # Создание нового подвопроса
            new_sub_question = SubQuestion(
                text=question.text,
                answer=question.answer,
                parent_question_id=parent_question.id,
                depth=depth,
                number=0,  # Временно устанавливаем number на 0
                category_id=question.category_id,
                subcategory_id=question.subcategory_id,
                parent_subquestion_id=question.parent_subquestion_id if question.parent_subquestion_id and question.parent_subquestion_id > 0 else None
            )

            # Добавление нового подвопроса в сессию
            db.add(new_sub_question)
            await db.commit()
            await db.refresh(new_sub_question)

            # Устанавливаем поле number равным id
            new_sub_question.number = new_sub_question.id
            await db.commit()  # Коммитим изменения после установки number

            logger.info(f"Создан новый подвопрос с ID: {new_sub_question.id}")
            return new_sub_question

        except HTTPException as e:
            # Ловим HTTP ошибки, чтобы их передать без изменений
            logger.error(f"HTTP ошибка: {e.detail}")
            raise e

        except Exception as e:
            logger.error(f"Ошибка при создании подвопроса: {e}")
            logger.error(traceback.format_exc())
            raise ErrorCreatingSubquestion(detail=f"Не удалось создать подвопрос: {str(e)}")


async def build_question_response(question: Question) -> QuestionResponse:
    response = QuestionResponse(
        id=question.id,
        text=question.text,
        answer=question.answer,
        number=question.number,
        count=question.count,
        depth=question.depth,
        parent_question_id=question.parent_question_id,
        category_id=question.category_id,
        subcategory_id=question.subcategory_id,
        sub_questions=[]  # Здесь мы начинаем с пустого списка
    )

    for sub_question in question.sub_questions:
        sub_response = await build_subquestion_response(sub_question)
        response.sub_questions.append(sub_response)

    return response


async def build_subquestion_response(sub_question: SubQuestion) -> SubQuestionResponse:
    logger.info(f"Создание ответа для подвопроса: {sub_question}")  # Логируем объект перед возвратом
    return SubQuestionResponse(
        id=sub_question.id,
        text=sub_question.text,
        answer=sub_question.answer,
        number=sub_question.number,
        count=sub_question.count,
        parent_question_id=sub_question.parent_question_id,
        depth=sub_question.depth,
        category_id=sub_question.category_id,
        subcategory_id=sub_question.subcategory_id,
        parent_subquestion_id=sub_question.parent_subquestion_id,  # Проверяем это поле
        sub_questions=[]  # Пустой список для построения иерархии
    )


# Функция для построения вложенных под-вопросов
async def get_sub_questions(db: AsyncSession, parent_question_id: int) -> List[SubQuestionResponse]:
    try:
        result = await db.execute(select(SubQuestion).where(SubQuestion.parent_question_id == parent_question_id))
        sub_questions = result.scalars().all()

        logger.info(f"Найденные под-вопросы для вопроса {parent_question_id}: {[sq.id for sq in sub_questions]}")

        sub_question_responses = [
            SubQuestionResponse(
                id=sub_question.id,
                text=sub_question.text,
                answer=sub_question.answer,
                number=sub_question.number,
                count=sub_question.count,
                parent_question_id=sub_question.parent_question_id,
                depth=sub_question.depth,
                category_id=sub_question.category_id,
                subcategory_id=sub_question.subcategory_id,
                parent_subquestion_id=sub_question.parent_subquestion_id,
                sub_questions=[]
            )
            for sub_question in sub_questions
        ]

        return sub_question_responses
    except Exception as e:
        logger.error(f"Ошибка в get_sub_questions: {e}")
        raise


def build_subquestions_hierarchy(sub_questions, parent_question_id=None):
    hierarchy = []
    for sub_question in sub_questions:
        if sub_question.parent_subquestion_id == parent_question_id:
            sub_question.sub_questions = build_subquestions_hierarchy(sub_questions, sub_question.id)
            hierarchy.append(sub_question)
    return hierarchy
