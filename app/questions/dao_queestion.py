import traceback
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

async def convert_subquestion_to_response(sub_question: SubQuestionResponse, sub_questions: List[SubQuestionResponse]):
    # Фильтруем детей текущего подвопроса
    children = [
        await convert_subquestion_to_response(child, sub_questions)
        for child in sub_questions
        if child.depth == sub_question.depth + 1 and child.question_id == sub_question.question_id
    ]


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

            )
            for sub_question in sub_questions
        ]


        logger.info(f"Получены под-вопросы для вопроса с ID {question_id}: {sub_question_responses}")

        # Построение иерархии
        hierarchical_sub_questions = build_subquestions_hierarchy(sub_question_responses)
        return hierarchical_sub_questions


        return sub_question_responses

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
    """Обновление полей text и answer"""

    if update_request.text is not None:
        question_obj.text = update_request.text

    if update_request.answer is not None:
        question_obj.answer = update_request.answer

