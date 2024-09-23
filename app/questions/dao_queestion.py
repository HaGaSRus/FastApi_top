from typing import Optional, List
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from fastapi import Depends
from app.database import get_db
from app.exceptions import CategoryNotFound, ParentQuestionNotFound
from app.logger.logger import logger
from app.questions.models import Question, Category
from app.questions.schemas import QuestionCreate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.questions.utils import get_category_by_id
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import asyncio


class QuestionService:
    @staticmethod
    async def create_question(
            question: QuestionCreate,
            category_id: int,
            parent_question_id: Optional[int],
            db: AsyncSession
    ) -> Question:
        # Обработка категории
        category = await get_category_by_id(category_id, db)
        if not category:
            raise CategoryNotFound

    # Обработка значения parent_question_id
        if parent_question_id is None:
            parent_question_id = None

    # Создание нового вопроса
        new_question = Question(
            text=question.text,
            answer=question.answer,
            category_id=category_id,
            parent_question_id=parent_question_id,
        )

        # Добавление и сохранение вопроса

        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)

        # Присваивание id в поле number

        new_question.number = new_question.id
        db.add(new_question)
        await db.commit()

        return new_question

    @staticmethod
    async def create_subquestion(
            question: QuestionCreate,
            parent_question_id: int,
            db: AsyncSession,
    ) -> Question:
        parent_question = await db.get(Question, parent_question_id)
        if not parent_question:
            raise ParentQuestionNotFound

        # Создание под-вопроса
        new_question = Question(
            text=question.text,
            category_id=parent_question.category_id,
            parent_question_id=parent_question_id,
        )
        db.add(new_question)
        await db.commit()
        await db.refresh(new_question)

        # Устанавливаем значение number
        new_question.number = new_question.id
        db.add(new_question)
        await db.commit()

        return new_question


async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    category = await db.get(Category, category_id)
    if not category:
        raise CategoryNotFound
    return category


async def get_similar_questions_cosine(question_text: str, db: AsyncSession, min_similarity: float = 0.2) -> List[Question]:
    # Получаем вопросы из базы с ограничением по количеству
    questions = await db.execute(select(Question).limit(1000))
    questions_list = questions.scalars().all()

    if not questions_list:
        logger.warning("Не удалось получить список вопросов из базы данных")
        return []

    # Векторизация вопросов
    all_texts = [q.text for q in questions_list] + [question_text]
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
        vectorizer = TfidfVectorizer().fit_transform([text1, text2])
        vectors = vectorizer.toarray()
        cosine_sim = cosine_similarity(vectors)
        return float(cosine_sim[0][1])
    except Exception as e:
        logger.error(f"Ошибка при расчете сходства между '{text1}' и '{text2}': {e}")
        return 0.0
