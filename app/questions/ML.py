import re
import torch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from bs4 import BeautifulSoup
from fastapi import HTTPException, Query, Depends
import numpy as np
import traceback
from app.logger.logger import logger
from app.questions.models import Question

# Загружаем модель и токенайзер
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")


def clean_html(raw_html: str) -> str:
    """Удаляет HTML-теги и возвращает чистый текст."""
    return BeautifulSoup(raw_html, "html.parser").get_text()


def get_embedding(text: str) -> np.ndarray:
    """Получает эмбеддинг для заданного текста."""
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        embedding = model(**inputs).last_hidden_state.mean(dim=1).cpu().numpy()
    return embedding


def normalize_text(text: str) -> str:
    """Нормализует текст: приводит к нижнему регистру и удаляет лишние пробелы."""
    text = text.lower()  # Приведение к нижнему регистру
    return re.sub(r'\s+', ' ', text).strip()  # Удаление лишних пробелов


async def get_similar_questions_cosine(query: str, db: AsyncSession, min_similarity: float = 0.2):
    """Находит схожие вопросы на основе косинусного сходства."""
    logger.info(f"Поиск схожих вопросов для запроса: {query}")

    questions_result = await db.execute(select(Question))
    all_questions = questions_result.scalars().all()
    logger.info(f"Найдено вопросов в базе данных: {len(all_questions)}")

    if not all_questions:
        logger.warning("В базе данных нет вопросов.")
        return []

    try:
        query_embedding = get_embedding(query)
        similar_questions = []

        for question in all_questions:
            if question.text:
                question_embedding = get_embedding(question.text)
                similarity = cosine_similarity(query_embedding, question_embedding)[0][0]
                logger.info(f"Сходство с вопросом '{question.text}': {similarity}")

                if similarity >= min_similarity:
                    similar_questions.append({
                        'question': question,
                        'similarity': similarity
                    })

        logger.info(f"Найдено похожих вопросов: {len(similar_questions)}")
        return sorted(similar_questions, key=lambda x: x['similarity'], reverse=True)

    except Exception as e:
        logger.error(f"Ошибка при нахождении похожих вопросов: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Ошибка при поиске похожих вопросов.")
