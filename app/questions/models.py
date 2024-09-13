from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)


class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    answer = Column(String, nullable=True)
    sub_question = Column(Boolean, default=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship('Category', back_populates='questions')
    parent_question_id = Column(Integer, ForeignKey('questions.id'), nullable=True)
    sub_questions = relationship('questions', backref='parent', remote_side=[id])


Category.questions = relationship('Question', back_populates='category')

