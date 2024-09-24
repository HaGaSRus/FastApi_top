from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from app.database import Base


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    number = Column(Integer, nullable=True)
    subcategories = relationship("Category",
                                 backref=backref('parent', remote_side=[id]),
                                 lazy='subquery')
    questions = relationship("Question", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name}, number={self.number})>"


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'))
    number = Column(Integer, nullable=True)
    answer = Column(String, nullable=True)
    count = Column(Integer, nullable=True)

    # Определение отношений
    sub_questions = relationship("SubQuestion", back_populates="question", lazy="subquery")
    category = relationship("Category", back_populates="questions")

    def __repr__(self):
        return f"<Question(id={self.id}, text={self.text}, number={self.number}, answer={self.answer}, category_id={self.category_id}, count={self.count})>"


class SubQuestion(Base):
    __tablename__ = "sub_questions"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey('questions.id'))
    text = Column(String, index=True)
    answer = Column(String, nullable=True)
    depth = Column(Integer, nullable=False)

    # Обратная связь к вопросу
    question = relationship("Question", back_populates="sub_questions")

    def __repr__(self):
        return f"<SubQuestion(id={self.id}, question_id={self.question_id}, text={self.text}, depth={self.depth})>"