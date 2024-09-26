import asyncio
import traceback
from typing import Optional, List
from fastapi import Depends, HTTPException
from app.database import get_db
from app.exceptions import CategoryNotFound, ParentQuestionNotFound
from app.logger.logger import logger
from app.questions.models import Question, Category, SubQuestion
from app.questions.schemas import QuestionCreate, SubQuestionCreate, SubQuestionResponse, QuestionResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.questions.utils import get_category_by_id
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re


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
                parent_id=None  # Это родительский вопрос
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
            # Логирование перед поиском родительского вопроса
            logger.info(f"Попытка найти родительский вопрос с ID: {parent_question_id}")

            # Находим родительский вопрос по ID
            parent_question = await db.get(Question, parent_question_id)
            if not parent_question:
                logger.error(f"Родительский вопрос с ID {parent_question_id} не найден.")
                raise ParentQuestionNotFound

            # Проверяем глубину и родительский подвопрос, если таковой существует
            logger.info(f"Проверка глубины вложенности для вопроса с ID: {parent_question_id}")
            parent_sub_question = await db.execute(
                select(SubQuestion).where(SubQuestion.question_id == parent_question_id)
            )
            parent_sub_question = parent_sub_question.scalars().first()

            # Устанавливаем depth
            depth = 1 if not parent_sub_question else parent_sub_question.depth + 1

            # Создаем новый подвопрос
            logger.info(f"Создание нового подвопроса для родительского вопроса с ID: {parent_question_id}")
            new_sub_question = SubQuestion(
                text=question.text,
                answer=question.answer,
                question_id=parent_question.id,
                depth=depth,
                parent_subquestion_id=question.parent_subquestion_id
                # Убедитесь, что здесь вы правильно передаете значение
            )

            # Сохраняем подвопрос в БД
            db.add(new_sub_question)
            await db.commit()
            await db.refresh(new_sub_question)

            # Устанавливаем поле number равным id и сохраняем снова
            new_sub_question.number = new_sub_question.id
            db.add(new_sub_question)
            await db.commit()

            return new_sub_question

        except ParentQuestionNotFound as e:
            logger.error(f"Ошибка при создании подвопроса: {e}")
            raise HTTPException(status_code=404, detail="Родительский вопрос не найден")
        except Exception as e:
            logger.error(f"Ошибка при создании подвопроса: {e}")
            logger.error(traceback.format_exc())  # Логирование полного стека вызовов
            raise HTTPException(status_code=500, detail="Не удалось создать подвопрос")


async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if not category:
        raise CategoryNotFound
    return category


# Функция для нормализации текста
def normalize_text(text: str) -> str:
    text = text.lower()  # Приведение к нижнему регистру
    text = re.sub(r'\s+', ' ', text)  # Удаление лишних пробелов
    return text.strip()


async def get_similar_questions_cosine(question_text: str, db: AsyncSession, min_similarity: float = 0.2) -> List[
    Question]:
    # Нормализуем текст вопроса
    normalized_question_text = normalize_text(question_text)

    # Получаем вопросы из базы с ограничением по количеству
    questions = await db.execute(select(Question).limit(1000))
    questions_list = questions.scalars().all()

    if not questions_list:
        logger.warning("Не удалось получить список вопросов из базы данных")
        return []

    # Нормализуем текст всех вопросов
    all_texts = [normalize_text(q.text) for q in questions_list] + [normalized_question_text]

    # Векторизация вопросов
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    # Вычисляем косинусное сходство
    cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])

    # Логируем результаты косинусного сходства
    logger.debug(f"Косинусные сходства: {cosine_similarities}")

    # Фильтруем вопросы с учетом минимального порога сходства
    similar_questions = [
        questions_list[i] for i in range(len(questions_list))
        if cosine_similarities[0][i] >= min_similarity
    ]

    # Логируем отфильтрованные вопросы
    logger.debug(f"Похожие вопросы: {[q.text for q in similar_questions]}")
    return similar_questions


def calculate_similarity(text1: str, text2: str) -> float:
    try:
        # Нормализуем текст
        normalized_text1 = normalize_text(text1)
        normalized_text2 = normalize_text(text2)

        vectorizer = TfidfVectorizer().fit_transform([normalized_text1, normalized_text2])
        vectors = vectorizer.toarray()
        cosine_sim = cosine_similarity(vectors)
        return float(cosine_sim[0][1])
    except Exception as e:
        logger.error(f"Ошибка при расчете сходства между '{text1}' и '{text2}': {e}")
        return 0.0


async def build_question_response(question):
    if isinstance(question, SubQuestion):
        response = SubQuestionResponse(
            id=question.id,
            text=question.text,
            answer=question.answer,
            number=question.number,
            count=question.count,
            question_id=question.question_id,
            depth=question.depth,
            parent_subquestion_id=question.parent_subquestion_id  # Убедитесь, что это поле передается
        )
        logger.info(f"Возвращаемая модель для подвопроса: {response}")
        return response
    else:
        response = QuestionResponse(
            id=question.id,
            text=question.text,
            answer=question.answer,
            number=question.number,
            count=question.count,
            category_id=question.category_id,
            parent_question_id=question.parent_question_id,  # Убедитесь, что это поле передается, если нужно
        )
        logger.info(f"Возвращаемая модель для вопроса: {response}")
        return response



async def build_hierarchical_subquestions(sub_questions: List[SubQuestion]) -> List[SubQuestionResponse]:
    question_map = {sub_question.id: {"sub_question": sub_question, "children": []} for sub_question in sub_questions}

    # Построение иерархии
    for sub_question in sub_questions:
        if sub_question.parent_subquestion_id:  # Если есть родительский подвопрос
            parent_id = sub_question.parent_subquestion_id
            if parent_id in question_map:
                question_map[parent_id]["children"].append(question_map[sub_question.id])

    # Преобразование в структуру для ответа, добавляя корневые подвопросы
    return [
        await convert_subquestion_to_response(question_map[sub_question.id]["sub_question"],
                                              question_map[sub_question.id]["children"])
        for sub_question in sub_questions if not sub_question.parent_subquestion_id  # Только корневые
    ]


# Функция для преобразования Question в QuestionResponse
async def convert_question_to_response(question: Question, sub_questions: List[SubQuestion]) -> QuestionResponse:
    sub_question_responses = await build_hierarchical_subquestions(sub_questions)
    return QuestionResponse(
        id=question.id,
        text=question.text,
        answer=question.answer,
        number=question.number,
        count=question.count,
        category_id=question.category_id,
        sub_questions=sub_question_responses
    )



async def convert_subquestion_to_response(sub_question, children) -> SubQuestionResponse:
    sub_question_response = SubQuestionResponse(
        id=sub_question.id,
        text=sub_question.text,
        answer=sub_question.answer,
        number=sub_question.number,
        count=sub_question.count,
        question_id=sub_question.question_id,
        depth=sub_question.depth,
        parent_question_id=sub_question.parent_subquestion_id  # Добавьте это поле
    )

    # Добавляем детей в ответ, если они есть
    if children:
        sub_question_response.children = [
            await convert_subquestion_to_response(child["sub_question"], child["children"]) for child in children
        ]

    return sub_question_response

