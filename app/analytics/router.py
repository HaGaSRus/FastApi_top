from fastapi import APIRouter, status, Depends
from fastapi_versioning import version
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from app.analytics.models import Analytics
from app.analytics.schemas import AnalyticsCreate
from app.database import get_db
from app.exceptions import QuestionNotFound, AuthorIsNotPresentException, FailedToCreateAnalyticsEntry
from app.logger.logger import logger
from app.questions.models import Question
from app.users.models import Users

router_analytics = APIRouter(
    prefix="/analytics",
    tags=["Аналитика"],
)


@router_analytics.post("/write", status_code=status.HTTP_201_CREATED, summary="Запись в бд данных для анализа")
@version(1)
async def create_analytics_entry(
        analytics_data: AnalyticsCreate,
        db: Session = Depends(get_db),
):
    try:
        # Логируем входящие данные
        logger.info(f"Получены данные аналитики: {analytics_data}")

        # Проверка существования вопроса
        query = select(Question).where(Question.id == analytics_data.question_id)
        result = await db.execute(query)
        question = result.scalars().first()
        if not question:
            logger.warning(f"Вопрос с id {analytics_data.question_id} не обнаружен")
            raise QuestionNotFound

        # Проверка существования автора
        query = select(Users).where(Users.id == analytics_data.author_id)
        result = await db.execute(query)
        author = result.scalars().first()
        if not author:
            logger.warning(f"Автор с id {analytics_data.author_id} не обнаружен")
            raise AuthorIsNotPresentException

        # Создание новой записи
        new_entry = Analytics(
            question_id=analytics_data.question_id,
            author=author.username,
        )
        logger.info(f"Создание новой записи аналитики: {new_entry}")

        db.add(new_entry)
        await db.commit()  # Не забудьте использовать await для коммита
        await db.refresh(new_entry)

        logger.info(f"Запись Аналитики успешно создана: {new_entry}")
        return new_entry

    except Exception as e:
        logger.warning(f"Не удалось создать запись аналитики: {e}")
        await db.rollback()
        raise FailedToCreateAnalyticsEntry



