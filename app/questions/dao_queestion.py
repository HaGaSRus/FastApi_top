import traceback
from typing import List
from fastapi import HTTPException
from app.exceptions import CategoryNotFound, ParentQuestionNotFound
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
            category = await get_category_by_id(category_id, db)
            if not category:
                raise CategoryNotFound

            # Если это подвопрос, перенаправляем на создание подвопроса
            if question.is_subquestion:
                if not question.parent_question_id:  # Изменено на parent_question_id
                    raise HTTPException(status_code=400, detail="Для подвопроса нужно указать parent_question_id")

                logger.info(f"Попытка создания подвопроса с parent_question_id: {question.parent_question_id}")
                return await QuestionService.create_subquestion(
                    question=question,
                    parent_question_id=question.parent_question_id,  # Изменено на parent_question_id
                    db=db
                )

            # Создание родительского вопроса
            new_question = Question(
                text=question.text,
                answer=question.answer,
                category_id=category_id,
                parent_question_id=None  # Это родительский вопрос
            )

            db.add(new_question)
            await db.commit()
            await db.refresh(new_question)

            # Устанавливаем поле number равным id и сохраняем снова
            new_question.number = new_question.id
            db.add(new_question)
            await db.commit()

            return new_question

        except Exception as e:
            logger.error(f"Ошибка при создании вопроса: {e}")
            logger.error(traceback.format_exc())  # Логирование полного стека вызовов
            raise HTTPException(status_code=500, detail="Не удалось создать вопрос")

    @staticmethod
    async def create_subquestion(
            question: SubQuestionCreate,
            parent_question_id: int,
            db: AsyncSession,
    ) -> SubQuestion:
        try:
            logger.info(f"Попытка найти родительский вопрос с ID: {parent_question_id}")
            parent_question = await db.get(Question, parent_question_id)
            if not parent_question:
                logger.error(f"Родительский вопрос с ID {parent_question_id} не найден.")
                raise ParentQuestionNotFound

            # Устанавливаем глубину
            depth = question.depth
            if question.is_deeper:  # Если нужно углубить вложенность
                depth += 1

            logger.info(
                f"Создание нового подвопроса для родительского вопроса с ID: {parent_question_id} и глубиной: {depth}"
            )
            new_sub_question = SubQuestion(
                text=question.text,
                answer=question.answer,
                question_id=parent_question.id,
                depth=depth,
                number=question.number,
                # parent_subquestion_id=None  # Это поле мы установим позже
            )

            # Находим последний созданный подвопрос для родительского вопроса
            if depth > 1:  # Проверка на глубину
                last_subquestion = await db.execute(
                    select(SubQuestion).filter(
                        SubQuestion.question_id == parent_question.id,
                        SubQuestion.depth == depth - 1
                    ).order_by(SubQuestion.id.desc())
                )
                last_subquestion = last_subquestion.scalars().first()

                if last_subquestion:
                    new_sub_question.parent_subquestion_id = last_subquestion.id  # Автоматически устанавливаем parent_subquestion_id

            db.add(new_sub_question)
            await db.commit()
            await db.refresh(new_sub_question)

            new_sub_question.number = new_sub_question.id
            db.add(new_sub_question)
            await db.commit()

            return new_sub_question

        except ParentQuestionNotFound as e:
            logger.error(f"Ошибка при создании подвопроса: {e}")
            raise HTTPException(status_code=404, detail="Родительский вопрос не найден")
        except Exception as e:
            logger.error(f"Ошибка при создании подвопроса: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Не удалось создать подвопрос")


async def build_question_response(question: Question) -> QuestionResponse:
    response = QuestionResponse(
        id=question.id,
        text=question.text,
        category_id=question.category_id,
        answer=question.answer,
        number=question.number,
        count=question.count,
        parent_question_id=question.parent_question_id,
        sub_questions=[]
    )

    # Заполнение подвопросов без parent_subquestion_id
    for sub_question in question.sub_questions:
        sub_response = SubQuestionResponse(
            id=sub_question.id,
            text=sub_question.text,
            answer=sub_question.answer,
            number=sub_question.number,
            count=sub_question.count,
            question_id=sub_question.question_id,
            depth=sub_question.depth,
            sub_questions=[]  # Убираем parent_subquestion_id
        )
        response.sub_questions.append(sub_response)

    return response




# Функция для построения вложенных под-вопросов
async def get_sub_questions(db: AsyncSession, question_id: int) -> List[SubQuestionResponse]:
    try:
        result = await db.execute(select(SubQuestion).where(SubQuestion.question_id == question_id))
        sub_questions = result.scalars().all()

        sub_question_responses = [
            SubQuestionResponse(
                id=sub_question.id,
                text=sub_question.text,
                answer=sub_question.answer,
                number=sub_question.number,
                count=sub_question.count,
                question_id=sub_question.question_id,
                depth=sub_question.depth,
                parent_subquestion_id=sub_question.parent_subquestion_id,
                sub_questions=[]  # Пустой список, т.к. иерархию мы построим позже
            )
            for sub_question in sub_questions
        ]

        logger.info(f"Получено sub_questions для вопроса_id. {question_id}: {sub_question_responses}")
        return sub_question_responses
    except Exception as e:
        logger.error(f"Ошибка в get_sub_questions: {e}")
        raise


def build_subquestions_hierarchy(sub_questions, parent_id=None):
    hierarchy = []
    for sub_question in sub_questions:
        if sub_question.parent_subquestion_id == parent_id:
            # Рекурсивно строим вложенность
            sub_question.sub_questions = build_subquestions_hierarchy(sub_questions, sub_question.id)
            hierarchy.append(sub_question)
    return hierarchy
