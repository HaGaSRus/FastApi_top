from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, ForwardRef

QuestionResponseRef = ForwardRef('QuestionResponse')
CategoryResponseRef = ForwardRef('CategoryResponse')


class CategoryBase(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True


class CategoryResponse(CategoryBase):
    subcategories: Optional[List[CategoryResponseRef]] = Field(default_factory=list)
    edit: bool = Field(default=False)
    number: Optional[int] = None

    class Config:
        orm_mode = True


class SubcategoryResponse(BaseModel):
    id: int
    name: str
    subcategories: List['SubcategoryResponse'] = []  # Используйте Forward Reference

    class Config:
        orm_mode = True


class QuestionResponseRef(BaseModel):
    id: int
    text: str
    number: int

class QuestionResponse(BaseModel):
    id: int
    text: str
    answer: Optional[str] = None
    category_id: int
    parent_question_id: Optional[int] = None
    number: int
    sub_questions: List[QuestionResponseRef] = []

    class Config:
        orm_mode = True

class CategoryCreate(BaseModel):
    name: str


class CategoryCreateResponse(CategoryBase):
    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    text: str
    parent_question_id: int = None
    answer: str = None

    class Config:
        orm_mode = True


class SubQuestionCreate(BaseModel):
    text: str
