from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    number = Column(Integer, nullable=True)

    # Отношение к подкатегориям
    subcategories = relationship(
        "Category",
        backref=backref('parent', remote_side=[id]),
        lazy='selectin'  # Измените на 'selectin' для более эффективной загрузки
    )

    # Отношение к вопросам
    questions = relationship("Question", back_populates="category", lazy='selectin')

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name}, number={self.number})>"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    category_id = Column(Integer, ForeignKey('categories.id', name='fk_questions_category_id'))
    number = Column(Integer, nullable=True)
    answer = Column(String, nullable=True)
    count = Column(Integer, nullable=True)
    parent_question_id = Column(Integer, ForeignKey('questions.id', name='fk_questions_parent_id'), nullable=True)  # Изменено на parent_question_id

    # Отношение к родительскому вопросу
    parent = relationship("Question", remote_side=[id], backref="children")  # Оставляем как есть

    # Отношение к категории
    category = relationship("Category", back_populates="questions")

    # Отношение к под-вопросам
    sub_questions = relationship("SubQuestion", back_populates="question", lazy='selectin')

    def __repr__(self):
        return f"<Question(id={self.id}, text={self.text}, number={self.number}, answer={self.answer}, category_id={self.category_id}, count={self.count})>"


class SubQuestion(Base):
    __tablename__ = "sub_questions"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey('questions.id', name='fk_subquestions_question_id'))
    text = Column(String, index=True)
    answer = Column(String, nullable=False)
    count = Column(Integer, nullable=True)
    depth = Column(Integer, nullable=False)
    number = Column(Integer, nullable=True)

    # Связь с родительским подвопросом (если есть)
    parent_subquestion_id = Column(Integer, ForeignKey('sub_questions.id', name='fk_subquestions_parent_subquestion_id'), nullable=True)

    # Обратная связь к вопросу
    question = relationship("Question", back_populates="sub_questions")
    parent_subquestion = relationship("SubQuestion", remote_side=[id], backref="children")

    def __repr__(self):
        return f"<SubQuestion(id={self.id}, question_id={self.question_id}, text={self.text}, depth={self.depth})>"
