import asyncio
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
            parent_question_id: Optional[int],
            db: AsyncSession
    ) -> Question:
        try:
            category = await get_category_by_id(category_id, db)
            if not category:
                raise CategoryNotFound

            if parent_question_id:
                return await QuestionService.create_question(
                    question=question,
                    parent_question_id=parent_question_id,
                    db=db
                )

            new_question = Question(
                text=question.text,
                answer=question.answer,
                category_id=category_id,
                parent_id=None  # Это родительский вопрос
            )

            db.add(new_question)
            await db.commit()
            await db.refresh(new_question)

            new_question.number = new_question.id
            db.add(new_question)
            await db.commit()

            return new_question
        except Exception as e:
            logger.error(f"Ошибка при создании вопроса: {e}")
            raise HTTPException(status_code=500, detail="Не удалось создать вопрос")

    @staticmethod
    async def create_subquestion(
            question: SubQuestionCreate,
            parent_question_id: int,
            db: AsyncSession,
    ) -> SubQuestion:
        try:
            # Проверяем существование родительского подвопроса
            parent_sub_question = await db.get(SubQuestion, parent_question_id)

            # Если родительский подвопрос не найден, выбрасываем исключение
            if not parent_sub_question:
                raise ParentQuestionNotFound

            # Проверяем существование родительского вопроса в таблице questions
            parent_question = await db.get(Question, parent_sub_question.question_id)

            # Если родительский вопрос не найден, выбрасываем исключение
            if not parent_question:
                raise ParentQuestionNotFound

            # Создаем новый подвопрос
            new_sub_question = SubQuestion(
                text=question.text,
                answer=question.answer,
                question_id=parent_question.id,  # Используем id найденного родительского вопроса
                depth=parent_sub_question.depth + 1  # Увеличиваем глубину на 1
            )

            # Логируем информацию о новом подвопросе
            logger.info(f"Создание подвопроса для родительского вопроса ID: {parent_question.id}")

            # Сохраняем новый подвопрос в БД
            db.add(new_sub_question)
            await db.commit()
            await db.refresh(new_sub_question)

            new_sub_question.number = new_sub_question.id
            db.add(new_sub_question)
            await db.commit()

            logger.info(f"Создан подвопрос: {new_sub_question}")

            return new_sub_question
        except Exception as e:
            logger.error(f"Ошибка при создании подвопроса: {e}")
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
            depth=question.depth
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
        )
        logger.info(f"Возвращаемая модель для вопроса: {response}")
        return response


# Функция для преобразования Question в QuestionResponse
async def convert_question_to_response(question, sub_questions) -> QuestionResponse:
    try:
        return QuestionResponse(
            id=question.id,
            text=question.text,
            answer=question.answer,
            number=question.number,
            count=question.count,
            category_id=question.category_id,
            sub_questions=[await build_question_response(q) for q in sub_questions]  # Преобразуем под-вопросы
        )
    except Exception as e:
        logger.error(f"Ошибка при преобразовании вопроса в ответ: {e}")
        raise  # Выбрасываем исключение, чтобы обработать его в вызывающем коде

