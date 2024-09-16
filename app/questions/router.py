from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db  # Убедитесь, что эта функция возвращает AsyncSession
from app.logger.logger import logger
from app.questions.models import Category, Question
from app.questions.schemas import CategoryResponse, QuestionResponse
from fastapi_versioning import version

router_question = APIRouter(
    prefix="/question",
    tags=["Вопросы"],
)


@router_question.get("/answer", response_model=list[CategoryResponse])
@version(1)
async def get_category(db: AsyncSession = Depends(get_db)):
    try:
        # Выполнение асинхронного запроса
        result = await db.execute(select(Category))
        categories = result.scalars().all()  # Извлечение всех результатов
        return categories
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router_question.get("/answer-list/deep", response_model=list[QuestionResponse])
@version(1)
async def get_questions(level: int = 1, db: AsyncSession = Depends(get_db)):
    try:
        # Выполнение асинхронного запроса
        result = await db.execute(select(Question).filter(Question.sub_question == False))
        questions = result.scalars().all()  # Извлечение всех результатов
        return questions
    except Exception as e:
        logger.error(f"Error fetching questions: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router_question.post("/answer-list/deep/{id}", response_model=QuestionResponse)
@version(1)
async def answer_question(id: int, answer: str, db: AsyncSession = Depends(get_db)):
    try:
        # Получение вопроса
        query = select(Question).filter(Question.id == id)
        result = await db.execute(query)
        question = result.scalar_one_or_none()

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Обновление ответа на вопрос
        question.answer = answer
        await db.commit()
        await db.refresh(question)
        return question
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
