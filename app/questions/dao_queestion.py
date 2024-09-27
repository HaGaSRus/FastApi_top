import traceback
from typing import List
from fastapi import Depends, HTTPException
from app.database import get_db
from app.exceptions import CategoryNotFound, ParentQuestionNotFound
from app.logger.logger import logger
from app.questions.models import Question, Category, SubQuestion
from app.questions.schemas import QuestionCreate, SubQuestionResponse, QuestionResponse
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
            question: QuestionCreate,
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
            depth = 1  # По умолчанию для первого подвопроса

            logger.info(
                f"Создание нового подвопроса для родительского вопроса с ID: {parent_question_id} и глубиной: {depth}")
            new_sub_question = SubQuestion(
                text=question.text,
                answer=question.answer,
                question_id=parent_question.id,
                depth=depth,  # Устанавливаем глубину
            )

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

    @staticmethod
    async def get_all_questions(db: AsyncSession) -> List[Question]:
        try:
            # Получаем все вопросы
            result = await db.execute(select(Question))
            questions = result.scalars().all()

            # Получаем под-вопросы для каждого вопроса
            for question in questions:
                result = await db.execute(select(SubQuestion).where(SubQuestion.question_id == question.id))
                question.sub_questions = result.scalars().all()

            return questions

        except Exception as e:
            logger.error(f"Ошибка при получении всех вопросов: {e}")
            raise HTTPException(status_code=500, detail="Не удалось получить вопросы")


async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if not category:
        raise CategoryNotFound
    return category


# Используем эту функцию для построения ответа на вопрос
async def build_question_response(question):
    # Если это подвопрос, конвертируем через SubQuestionResponse
    response = QuestionResponse(
        id=question.id,
        text=question.text,
        answer=question.answer,
        number=question.number,
        count=question.count,
        depth=question.depth,
        category_id=question.category_id,
        sub_questions=[]  # Строим иерархию для под-вопросов
    )
    logger.info(f"Возвращаемая модель для вопроса: {response}")

    # Добавляем под-вопросы
    for sub_question in question.sub_questions:
        response.sub_questions.append(build_question_response(sub_question))

    return response


async def fetch_all_questions(db: AsyncSession):
    questions = await QuestionService.get_all_questions(db)

    response_list = [await build_question_response(question) for question in questions]
    return response_list


async def build_hierarchical_subquestions(sub_questions):
    hierarchical_subquestions = []
    for sub in sub_questions:
        hierarchical_subquestions.append(
            SubQuestionResponse(
                id=sub.id,
                text=sub.text,
                answer=sub.answer,
                number=sub.number,
                count=sub.count,
                question_id=sub.question_id,
                depth=sub.depth,
                sub_questions=[]  # Здесь можно добавлять вложенные под-вопросы
            )
        )
    return hierarchical_subquestions


async def convert_subquestion_to_response(sub_question: SubQuestionResponse, sub_questions: List[SubQuestionResponse]):
    # Фильтруем детей текущего подвопроса
    children = [
        await convert_subquestion_to_response(child, sub_questions)
        for child in sub_questions
        if child.depth == sub_question.depth + 1 and child.question_id == sub_question.question_id
    ]

    # Возвращаем объект SubQuestionResponse с детьми
    return SubQuestionResponse(
        id=sub_question.id,
        text=sub_question.text,
        answer=sub_question.answer,
        number=sub_question.number,
        count=sub_question.count,
        question_id=sub_question.question_id,
        depth=sub_question.depth,
        sub_questions=children  # Добавляем вложенные под-вопросы
    )


    # Добавляем детей в ответ, если они есть
    # if children:
    #     sub_question_response.children = [
    #         await convert_subquestion_to_response(child["sub_question"], child["children"]) for child in children
    #     ]
    # logger.info(f"Под-вопрос {sub_question.id} имеет parent_subquestion_id: {sub_question.depth}")
    #
    # return sub_question_response


# Обновляем функцию для получения всех подвопросов и построения иерархии
async def get_sub_questions(db: AsyncSession, question_id: int) -> List[SubQuestionResponse]:
    try:
        # Получаем все подвопросы по question_id, сортируя по глубине
        result = await db.execute(
            select(SubQuestion).where(SubQuestion.question_id == question_id).order_by(SubQuestion.depth)
        )
        sub_questions = result.scalars().all()

        # Преобразуем в SubQuestionResponse объекты
        sub_question_responses = [
            SubQuestionResponse(
                id=sub_question.id,
                text=sub_question.text,
                answer=sub_question.answer,
                number=sub_question.number,
                count=sub_question.count,
                question_id=sub_question.question_id,
                depth=sub_question.depth,
                sub_questions=[]  # Инициализируем пустым списком
            )
            for sub_question in sub_questions
        ]

        logger.info(f"Получены под-вопросы для вопроса с ID {question_id}: {sub_question_responses}")

        # Построение иерархии
        hierarchical_sub_questions = build_subquestions_hierarchy(sub_question_responses)
        return hierarchical_sub_questions

    except Exception as e:
        logger.error(f"Ошибка в get_sub_questions: {e}")
        raise HTTPException(status_code=500, detail="Не удалось получить подвопросы")


# Обновленная функция для создания иерархии подвопросов
def build_subquestions_hierarchy(sub_questions, parent_id=None):
    hierarchy = []
    for sub_question in sub_questions:
        if sub_question.question_id == parent_id:
            # Рекурсивно строим иерархию
            children = build_subquestions_hierarchy(sub_questions, sub_question.id)
            hierarchy.append({
                'id': sub_question.id,
                'text': sub_question.text,
                'answer': sub_question.answer,
                'depth': sub_question.depth,
                'sub_questions': children  # Вложенные подвопросы
            })
    return hierarchy




async def get_hierarchical_questions(db: AsyncSession):
    result = await db.execute(select(Question))
    questions = result.scalars().all()

    result = await db.execute(select(SubQuestion))
    sub_questions = result.scalars().all()

    # Преобразуем вопросы в формат ответа
    question_responses = [
        QuestionResponse(
            id=question.id,
            text=question.text,
            answer=question.answer,
            number=question.number,
            count=question.count,
            category_id=question.category_id,
            sub_questions=[]  # Будем добавлять подвопросы позже
        )
        for question in questions
    ]

    # Преобразуем подвопросы в формат ответа
    sub_question_responses = [
        SubQuestionResponse(
            id=sub_question.id,
            text=sub_question.text,
            answer=sub_question.answer,
            number=sub_question.number,
            count=sub_question.count,
            question_id=sub_question.question_id,
            depth=sub_question.depth,
            sub_questions=[]
        )
        for sub_question in sub_questions
    ]

    # Строим иерархию
    hierarchical_questions = build_subquestions_hierarchy(sub_question_responses)

    return hierarchical_questions


async def create_subquestions(sub_questions_data, parent_question_id, current_depth, db):
    if current_depth > 10:
        raise HTTPException(status_code=400, detail="Глубина вложенности не должна превышать 10")

    for sub_question_data in sub_questions_data:
        # Создаем под вопрос
        sub_question = SubQuestion(
            text=sub_question_data['text'],
            answer=sub_question_data.get('answer'),
            number=sub_question_data['number'],
            question_id=parent_question_id,
            depth=current_depth
        )
        db.add(sub_question)
        await db.commit()  # Сохраняем в базе данных

        # Если есть вложенные подвопросы, вызываем функцию рекурсивно
        if 'sub_questions' in sub_question_data:
            await create_subquestions(
                sub_question_data['sub_questions'],
                sub_question.id,
                current_depth + 1,
                db
            )
