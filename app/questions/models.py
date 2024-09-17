from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from app.database import Base


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    parent_id = Column(Integer, ForeignKey('categories.id'))

    # Связь с родительской категорией
    parent = relationship("Category", remote_side=[id], back_populates="subcategories")
    # Связь с подкатегориями
    subcategories = relationship("Category", back_populates="parent")
    # Связь с вопросами
    questions = relationship("Question", back_populates="category")


class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    answer = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'))

    # Связь с категорией
    category = relationship('Category', back_populates='questions')

    # Поле для связи с родительским вопросом
    parent_question_id = Column(Integer, ForeignKey('questions.id'), nullable=True)

    # Под-вопросы (связь с вопросами)
    sub_questions = relationship('Question', backref=backref('parent_question', remote_side=[id]),
                                 cascade='all, delete-orphan')
