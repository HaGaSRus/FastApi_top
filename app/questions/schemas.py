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
    answer: Optional[str] = None
    number: Optional[int] = 0
    count: Optional[int] = 0
    depth: int

    parent_question_id: int  # ID родительского вопроса
    parent_subquestion_id: Optional[int] = 0
    category_id: Optional[int] = 0
    subcategory_id: Optional[int] = 0



class QuestionCreate(BaseModel):
    text: str
    answer: Optional[str] = None
    number: Optional[int] = 0
    category_id: Optional[int]
    subcategory_id: Optional[int] = 0
    count: Optional[int]
    parent_question_id: Optional[int] = 0  # Поле для указания родительского вопроса
    is_subquestion: bool = False  # Поле для указания поиска в под-вопросах
    parent_subquestion_id: Optional[int] = 0
    # depth: Optional[int] = 0


    class Config:
        from_attributes = True


# Модель ответа на вопрос
class SubQuestionResponse(BaseModel):
    id: int
    text: str
    answer: Optional[str] = None  # Сделать ответ необязательным, если требуется
    number: int

    count: Optional[int] = 0
    parent_question_id: int
    depth: int  # Обязательно, так как это будет отображать уровень вложенности
    parent_subquestion_id: Optional[int] = 0
    category_id: Optional[int] = 0
    subcategory_id: Optional[int] = 0
    sub_questions: List['SubQuestionResponse'] = []  # Рекурсивная структура

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: int
    text: str
    category_id: int
    subcategory_id: Optional[int] = 0
    answer: Optional[str] = None  # Сделать ответ необязательным, если требуется
    number: int
    depth: int
    count: Optional[int] = 0
    parent_question_id: Optional[int] = 0  # Это поле должно оставаться, если есть родительский вопрос

    sub_questions: List[SubQuestionResponse] = []



    class Config:
        from_attributes = True


class DeleteCategoryRequest(BaseModel):
    category_id: int


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


class UpdateQuestionRequest(BaseModel):
    question_id: int = Field(..., description="ID основного вопроса")
    sub_question_id: Optional[int] = Field(None, description="ID под-вопроса (если указан) ")
    text: Optional[str] = Field(None, description="Новый текст вопроса или под-вопроса")
    answer: Optional[str] = Field(None, description="Новый ответ вопроса или под-вопроса")


class DeleteQuestionRequest(BaseModel):
    question_id: int = Field(..., description="ID основного вопроса")
    sub_question_id: Optional[int] = Field(None, description="ID под-вопроса (если указан)")

class QuestionIDRequest(BaseModel):
    question_id: int