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


class SubQuestionCreate(BaseModel):
    answer: str
    text: str
    depth: int


# Модель для создания вопроса
class QuestionCreate(BaseModel):
    text: str
    answer: str
    number: int
    count: int
    subcategory_id: Optional[int] = Field(None, exclude=True)
    sub_questions: Optional[List[SubQuestionCreate]] = None

    class Config:
        from_attributes = True


class SubQuestionResponse(BaseModel):
    id: int
    question_id: int
    text: str
    answer: Optional[str]
    depth: int


# Модель ответа на вопрос
class QuestionResponse(BaseModel):
    id: int
    text: str
    answer: str
    category_id: int
    number: int
    count: Optional[int] = None
    sub_questions: List[SubQuestionResponse] = []  # Сделайте поле необязательным

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

    class Config:
        from_attributes = True
