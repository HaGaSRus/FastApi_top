from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship, backref
from datetime import datetime, timezone
from app.database import Base
import pytz

Yekaterinburg_tz = pytz.timezone('Asia/Yekaterinburg')


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    number = Column(Integer, nullable=True)

    subcategories = relationship(
        "Category",
        backref=backref('parent', remote_side=[id]),
        lazy='selectin'
    )

    questions = relationship(
        "Question",
        back_populates="category",
        foreign_keys="[Question.category_id]"
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name}, number={self.number})>"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    category_id = Column(Integer, ForeignKey('categories.id', name='fk_questions_category_id'))
    subcategory_id = Column(Integer, ForeignKey('categories.id', name='fk_questions_subcategory_id'), nullable=True)
    number = Column(Integer, nullable=True)
    answer = Column(String, nullable=True)
    count = Column(Integer, nullable=True)
    parent_question_id = Column(Integer, ForeignKey('questions.id', name='fk_questions_parent_id'), nullable=True)
    depth = Column(Integer, nullable=False, default=0)

    author = Column(String, nullable=True)
    author_edit = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(Yekaterinburg_tz), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(Yekaterinburg_tz),
                        onupdate=lambda: datetime.now(Yekaterinburg_tz), nullable=True)

    parent = relationship("Question", remote_side=[id], backref="children")

    category = relationship("Category", back_populates="questions", foreign_keys=[category_id])
    subcategory = relationship("Category", foreign_keys=[subcategory_id])
    sub_questions = relationship("SubQuestion", back_populates="question", lazy='selectin')

    def __repr__(self):
        return f"<Question(id={self.id}, text={self.text}, number={self.number}, answer={self.answer}, category_id={self.category_id}, count={self.count})>"


class SubQuestion(Base):
    __tablename__ = "sub_questions"

    id = Column(Integer, primary_key=True, index=True)
    parent_question_id = Column(Integer, ForeignKey('questions.id', name='fk_subquestions_question_id'))
    category_id = Column(Integer, ForeignKey('categories.id', name='fk_subquestions_category_id'), nullable=True)
    subcategory_id = Column(Integer, ForeignKey('categories.id', name='fk_subquestions_subcategory_id'), nullable=True)
    text = Column(String, index=True)
    answer = Column(String, nullable=False)
    count = Column(Integer, nullable=True)
    depth = Column(Integer, nullable=False)
    number = Column(Integer, nullable=True)

    author = Column(String, nullable=True)
    author_edit = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(Yekaterinburg_tz), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(Yekaterinburg_tz),
                        onupdate=lambda: datetime.now(Yekaterinburg_tz), nullable=True)

    parent_subquestion_id = Column(Integer,
                                   ForeignKey('sub_questions.id', name='fk_subquestions_parent_subquestion_id'),
                                   nullable=True)

    question = relationship("Question", back_populates="sub_questions")

    # parent_subquestion = relationship("SubQuestion", remote_side=[id], backref="children")

    def __repr__(self):
        return f"<SubQuestion(id={self.id}, parent_question_id={self.parent_question_id}, text={self.text}, depth={self.depth}, parent_subquestion_id={self.parent_subquestion_id})>"



