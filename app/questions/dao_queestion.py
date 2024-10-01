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
            # Получаем категорию по ID
            category = await get_category_by_id(category_id, db)
            if not category:
                raise CategoryNotFound

            # Если это подвопрос
            if question.is_subquestion:
                if not question.parent_question_id:  # Проверяем наличие parent_question_id
                    raise HTTPException(status_code=400, detail="Для подвопроса нужно указать parent_question_id")

                # Логирование попытки создания подвопроса
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
                parent_question_id=None,  # Это родительский вопрос
                depth=0
            )

            # Добавляем новый вопрос в сессию
            db.add(new_question)
            await db.commit()  # Коммитим изменения
            await db.refresh(new_question)  # Обновляем объект

            # Устанавливаем поле number равным id и коммитим изменения
            new_question.number = new_question.id  # Установка number равного id
            await db.commit()  # Коммитим изменения после установки number

            return new_question

        except CategoryNotFound:
            raise HTTPException(status_code=404, detail="Категория не найдена")

        except Exception as e:
            logger.error(f"Ошибка при создании вопроса: {e}")
            logger.error(traceback.format_exc())  # Логирование полного стека вызовов
            raise HTTPException(status_code=500, detail="Не удалось создать вопрос")

    @staticmethod
    async def create_subquestion(question: SubQuestionCreate, db: AsyncSession) -> SubQuestion:
        try:
            # Проверка наличия родительского вопроса
            parent_question = await db.get(Question, question.parent_question_id)
            if not parent_question:
                logger.error(f"Родительский вопрос с ID {question.parent_question_id} не найден.")
                raise ParentQuestionNotFound

            # Устанавливаем значение depth
            depth = parent_question.depth + 1
            if question.parent_subquestion_id:  # Если есть родительский подвопрос
                parent_subquestion = await db.get(SubQuestion, question.parent_subquestion_id)
                if parent_subquestion:
                    depth = parent_subquestion.depth + 1  # Увеличиваем на 1

            # Создание нового подвопроса
            new_sub_question = SubQuestion(
                text=question.text,
                answer=question.answer,
                parent_question_id=parent_question.id,
                depth=depth,
                number=0,  # Временно устанавливаем number на 0
                parent_subquestion_id=question.parent_subquestion_id if question.parent_subquestion_id > 0 else None
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

        except Exception as e:
            logger.error(f"Ошибка при создании подвопроса: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Не удалось создать подвопрос")


async def build_question_response(question: Question) -> QuestionResponse:
    response = QuestionResponse(
        id=question.id,
        text=question.text,
        answer=question.answer,
        number=question.number,
        count=question.count,
        depth=question.depth,
        parent_question_id=question.parent_question_id,  # Убедитесь, что это поле заполнено
        category_id=question.category_id if question.parent_question_id is not None else 0,  # Добавляем category_id только для родительского вопроса
        sub_questions=[]
    )
    # [если истина] if [выражение] else [если ложь]

    for sub_question in question.sub_questions:
        sub_response = SubQuestionResponse(
            id=sub_question.id,
            text=sub_question.text,
            answer=sub_question.answer,
            number=sub_question.number,
            count=sub_question.count,
            parent_question_id=sub_question.parent_question_id,  # Это ID родительского вопроса
            depth=sub_question.depth,
            sub_questions=[]  # Убираем parent_subquestion_id
        )
        response.sub_questions.append(sub_response)

    return response


# Функция для построения вложенных под-вопросов
async def get_sub_questions(db: AsyncSession, question_id: int) -> List[SubQuestionResponse]:
    try:
        result = await db.execute(select(SubQuestion).where(SubQuestion.parent_question_id == question_id))
        sub_questions = result.scalars().all()

        sub_question_responses = [
            SubQuestionResponse(
                id=sub_question.id,
                text=sub_question.text,
                answer=sub_question.answer,
                number=sub_question.number,
                count=sub_question.count,
                parent_question_id=sub_question.parent_question_id,
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