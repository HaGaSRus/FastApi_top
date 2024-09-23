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
class QuestionCreate(BaseModel):
    text: str
    answer: Optional[str] = None
    subcategory_id: Optional[int] = None

    class Config:
        from_attributes = True


# Модель ответа на вопрос
class QuestionResponse(BaseModel):
    id: int
    text: str
    answer: Optional[str] = None
    category_id: int
    number: int
    count: Optional[int] = None
    sub_questions: Optional[List['QuestionResponseRef']] = None  # Сделайте поле необязательным

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

