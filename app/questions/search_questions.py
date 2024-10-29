from pydantic import BaseModel, Field
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.questions.models import Question, SubQuestion
from app.questions.schemas import QuestionResponse, SubQuestionResponse, QuestionSearchResponse
from sqlalchemy import or_
from rapidfuzz import fuzz, process


class SearchQuestionRequest(BaseModel):
    query: str = Field(..., description="Текст для поиска")
    category_id: Optional[int] = Field(None, description="ID категории для фильтрации")


class QuestionSearchService:
    @staticmethod
    async def search_questions(
            db: AsyncSession,
            query: str,
    ) -> List[Question]:

        stmt = select(Question).where(
            or_(
                Question.text.ilike(f"%{query}%"),
                Question.answer.ilike(f"%{query}%")
            )
        )

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def search_questions_fts(
            db: AsyncSession, query: str
    ) -> List[Question]:
        stmt = select(Question).where(
            func.to_tsvector(
                'russian', func.coalesce(Question.text, '') + ' ' + func.coalesce(Question.answer, '')
            ).op('@@')(func.plainto_tsquery('russian', query))
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def search_questions_fuzzy_search(
            db: AsyncSession,
            query: str,
            threshold: int = 50
    ) -> List[QuestionSearchResponse]:
        # Запрос для получения всех вопросов
        stmt = select(Question)
        result = await db.execute(stmt)
        questions = result.scalars().all()

        # Словарь для сопоставления: {вопрос: текст вопроса}
        question_map = {q: q.text for q in questions}

        # Поиск совпадений
        matches = process.extract(
            query,
            question_map,
            scorer=fuzz.partial_ratio,
            score_cutoff=threshold
        )

        # Формирование ответа
        response = []
        for match in matches:
            question = match[2]
            response.append(QuestionSearchResponse(
                id=question.id,
                text=question.text,
                answer=question.answer,
                march_percentage=match[1]  # добавляем процент совпадения
            ))

        return response


async def build_question_response_from_search(question: Question,
                                              db: AsyncSession
                                              ) -> QuestionResponse:
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
        sub_questions=[]
    )

    sub_questions = await get_sub_questions_for_question_from_search(db, parent_question_id=question.id)

    response.sub_questions = build_subquestions_hierarchy_from_search(sub_questions)

    return response


async def get_sub_questions_for_question_from_search(db: AsyncSession, parent_question_id: int) -> List[
    SubQuestionResponse]:
    result = await db.execute(select(SubQuestion).where(SubQuestion.parent_question_id == parent_question_id))
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
            category_id=sub_question.category_id,
            subcategory_id=sub_question.subcategory_id,
            parent_subquestion_id=sub_question.parent_subquestion_id,
            sub_questions=[]
        )
        for sub_question in sub_questions
    ]

    return sub_question_responses


def build_subquestions_hierarchy_from_search(sub_questions, parent_question_id=None):
    hierarchy = []
    for sub_question in sub_questions:
        if sub_question.parent_subquestion_id == parent_question_id:
            sub_question.sub_questions = build_subquestions_hierarchy_from_search(sub_questions, sub_question.id)
            hierarchy.append(sub_question)
    return hierarchy


async def perform_fts_search(session: AsyncSession, query: str) -> List[Question]:
    try:
        sql_query = text(""" 
        SELECT * 
        FROM questions 
        WHERE to_tsvector('russian', text || ' ' || tsv_content) 
              @@ plainto_tsquery('russian', :query)
        """)

        result = await session.execute(sql_query, {"query": query})
        questions = result.scalars().all()
        print(f"Found questions: {questions}")  # Для отладки
        return questions
    except Exception as e:
        print(f"Ошибка при выполнении FTS-запроса: {e}")
        raise
