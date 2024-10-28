import pytz
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

Yekaterinburg_tz = pytz.timezone('Asia/Yekaterinburg')


class Analytics(Base):
    __tablename__ = 'analytics'

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, nullable=True)
    subquestion_id = Column(Integer, nullable=True)
    author = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(Yekaterinburg_tz), nullable=True)
