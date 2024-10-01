from pydantic import BaseModel, Field, RootModel
from typing import Optional, List


# Базовая модель категории
class CategoryBase(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True


# Модель ответа для категории
class CategoryResponse(CategoryBase):
    subcategories: Optional[List['CategoryResponse']] = Field(default_factory=list)
    edit: bool = Field(default=False)
    number: Optional[int] = None

    class Config:
        from_attributes = True


# Модель создания категории
class CategoryCreate(BaseModel):
    name: str


# Модель ответа при создании категории
class CategoryCreateResponse(CategoryBase):
    class Config:
        from_attributes = True


# Модель для создания вопроса
class SubQuestionCreate(BaseModel):
    text: str
    answer: str
    number: int
    count: int
    depth: int
    parent_question_id: int  # ID родительского вопроса


class QuestionCreate(BaseModel):
    text: str
    answer: Optional[str] = None
    number: int
    category_id: int
    count: Optional[int]
    parent_question_id: Optional[int] = None  # Поле для указания родительского вопроса
    is_subquestion: bool = False  # Поле для указания поиска в под-вопросах
    parent_subquestion_id: Optional[int] = None
    # depth: Optional[int] = 0

    class Config:
        from_attributes = True


# Модель ответа на вопрос
class SubQuestionResponse(BaseModel):
    id: int
    text: str
    answer: Optional[str] = None  # Сделать ответ необязательным, если требуется
    number: int
    count: Optional[int] = None
    parent_question_id: int
    depth: int  # Обязательно, так как это будет отображать уровень вложенности
    parent_subquestion_id: Optional[int] = None
    sub_questions: List['SubQuestionResponse'] = []  # Рекурсивная структура

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: int
    text: str
    category_id: int
    answer: Optional[str] = None  # Сделать ответ необязательным, если требуется
    number: int
    # depth: int
    count: Optional[int] = None
    parent_question_id: Optional[int] = None  # Это поле должно оставаться, если есть родительский вопрос
    sub_questions: List[SubQuestionResponse] = []

    class Config:
        from_attributes = True



# Упрощённый ответ для под-вопросов
class QuestionResponseRef(BaseModel):
    id: int
    text: str
    number: int

    class Config:
        from_attributes = True


class DeleteCategoryRequest(BaseModel):
    category_id: int


class UpdateCategoryRequest(BaseModel):
    category_id: int
    category_data: CategoryCreate


class UpdateCategoryData(BaseModel):
    id: int
    number: int  # Предполагаю, что это поле для номера категории
    name: str


# Модель для запроса на обновление категорий
class UpdateCategoriesRequest(RootModel[list[UpdateCategoryData]]):
    pass


class UpdateCategoryData(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None  # Optional[int] позволяет значениям быть None
    number: int


class UpdateSubcategoryData(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]  # Поле для связи с родительской категорией
    number: Optional[int]


class SimilarQuestionResponse(BaseModel):
    id: int
    question_text: str
    similarity_score: float  # оценить схожесть


class DynamicAnswerResponse(BaseModel):
    id: int
    text: str
    has_answer: bool
    answer: Optional[str] = None
    category_id: int
    number: int
    sub_questions: Optional[List[SimilarQuestionResponse]] = None


class DynamicSubAnswerResponse(BaseModel):
    id: Optional[int]
    text: str
    has_answer: bool
    answer: Optional[str]
    category_id: Optional[int]
    number: Optional[int]
    sub_questions: List[SimilarQuestionResponse]


class DetailedQuestion(BaseModel):
    id: int
    text: str
    category: str
    similarity: Optional[float] = None
    created_at: str
    additional_data: Optional[dict] = None


class DetailedQuestionResponse(BaseModel):
    questions: List[DetailedQuestion]


class QuestionAllResponse(BaseModel):
    id: int
    text: str
    number: int
    answer: Optional[str] = None
    category_id: Optional[int] = None
    count: Optional[int] = None
    sub_questions: List[SubQuestionResponse] = []

    class Config:
        from_attributes = True
