import re
import torch
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.logger.logger import logger
from app.questions.models import Question, SubQuestion
from app.questions.schemas import QuestionResponse, SubQuestionResponse, QuestionSearchResponse
from sqlalchemy import or_
from rapidfuzz import fuzz, process
from transformers import AutoTokenizer, AutoModel

# tokenizer = AutoTokenizer.from_pretrained("DeepPavlov/rubert-base-cased-sentence")
# model = AutoModel.from_pretrained("DeepPavlov/rubert-base-cased-sentence")


class SearchQuestionRequest(BaseModel):
    query: str = Field(..., description="Текст для поиска")
    category_id: Optional[int] = Field(None, description="ID категории для фильтрации")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


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
    async def search_questions_fuzzy_search(
            db: AsyncSession,
            query: str,
            threshold: int = 75,
            top_n: int = 5
    ) -> List[QuestionSearchResponse]:

        normalized_query = normalize(query)

        stmt = select(Question)
        result = await db.execute(stmt)
        questions = result.scalars().all()

        question_map = {q: normalize(f"{q.text} {q.answer}") for q in questions}

        def find_best_match_positions(text: str, query: str, field_name: str) -> Optional[dict]:
            parts = [query[:i] for i in range(len(query), 2, -1)]
            for part in parts:
                start = text.find(part)
                if start != -1:
                    return {"field": field_name, "start": start, "end": start + len(part)}
            return None

        matches = process.extract(
            normalized_query,
            question_map,
            scorer=fuzz.partial_ratio,
            score_cutoff=threshold,
            limit=top_n
        )

        response = []
        for match in matches:
            question = match[2]
            match_score = match[1]

            match_positions = []

            match_position_text = find_best_match_positions(normalize(question.text), normalized_query, "text")
            if match_position_text:
                match_positions.append(match_position_text)

            match_position_answer = find_best_match_positions(normalize(question.answer), normalized_query, "answer")
            if match_position_answer:
                match_positions.append(match_position_answer)

            # Извлекаем под-вопросы для текущего вопроса
            sub_questions = await get_sub_questions_for_question_from_search(db, parent_question_id=question.id)

            # Создаем объект ответа с полными деталями вопроса
            question_response = QuestionSearchResponse(
                id=question.id,
                text=question.text,
                answer=question.answer,
                march_percentage=match_score,
                match_positions=match_positions,
                author=question.author,
                created_at=question.created_at,
                updated_at=question.updated_at,
                category_id=question.category_id,
                subcategory_id=question.subcategory_id,
                number=question.number,
                depth=question.depth,
                sub_questions=build_subquestions_hierarchy_from_search(sub_questions)  # Добавляем под-вопросы
            )

            response.append(question_response)

        return response

    # @staticmethod
    # def encode_text(text: str):
    #     inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    #     with torch.no_grad():
    #         embeddings = model(**inputs).last_hidden_state.mean(dim=1)
    #     return embeddings
    #
    # @staticmethod
    # async def search_questions_vectorized(
    #         db: AsyncSession,
    #         query: str,
    #         top_n: int = 5,
    #         threshold: float = 0.73
    # ) -> List[QuestionSearchResponse]:
    #     normalized_query = normalize(query)
    #     query_embedding = QuestionSearchService.encode_text(normalized_query)
    #     logger.warning(f"Query embedding: {query_embedding}")
    #
    #     stmt = select(Question)
    #     result = await db.execute(stmt)
    #     questions = result.scalars().all()
    #
    #     questions_map = {q: normalize(q.text) for q in questions}
    #     question_embeddings = {q: QuestionSearchService.encode_text(text) for q, text in questions_map.items()}
    #
    #     scores = [
    #         (q, torch.cosine_similarity(query_embedding, emb).item())
    #         for q, emb in question_embeddings.items()
    #     ]
    #     logger.warning(f"Scores: {scores}")
    #     top_matches = sorted(
    #         [(q, score) for q, score in scores if score >= threshold],
    #         key=lambda x: x[1],
    #         reverse=True
    #     )[:top_n]
    #
    #     return [
    #         QuestionSearchResponse(
    #             id=match[0].id,
    #             text=match[0].text,
    #             answer=match[0].answer,
    #             march_percentage=match[1] * 100,
    #         )
    #         for match in top_matches if match[1]
    #     ]


async def build_question_response_from_search(question: Question,
                                              db: AsyncSession
                                              ) -> QuestionResponse:
    response = QuestionResponse(
        id=question.id,
        text=question.text,
        author=question.author,
        author_edit=question.author_edit,
        answer=question.answer,
        number=question.number,
        count=question.count,
        depth=question.depth,
        created_at=question.created_at,
        updated_at=question.updated_at,
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
            author=sub_question.author,
            author_edit=sub_question.author_edit,
            created_at=sub_question.created_at,
            updated_at=sub_question.updated_at,
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

