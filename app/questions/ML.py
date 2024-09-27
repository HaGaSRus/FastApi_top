import re
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.logger.logger import logger
from app.questions.models import Question
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select


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