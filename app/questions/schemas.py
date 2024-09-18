from pydantic import BaseModel, Field
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
class QuestionCreate(BaseModel):
    text: str
    answer: Optional[str] = None

    class Config:
        from_attributes = True


# Модель ответа на вопрос
class QuestionResponse(BaseModel):
    id: int
    text: str
    answer: Optional[str] = None
    category_id: int
    number: int
    sub_questions: List['QuestionResponseRef'] = []

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
    id: int  # id категории, которую нужно обновить
    number: int  # number категории, который нельзя изменять
    name: str


class UpdateCategoriesRequest(BaseModel):
    categories: List[UpdateCategoryData]