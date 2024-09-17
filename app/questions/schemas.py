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

    class Config:
        orm_mode = True


class QuestionBase(BaseModel):
    id: int
    text: str
    answer: Optional[str] = None
    category_id: int
    parent_question_id: Optional[int] = None


class QuestionResponse(QuestionBase):
    sub_questions: List[QuestionResponseRef] = []

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str


class CategoryCreateResponse(CategoryBase):
    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    text: str


class SubQuestionCreate(BaseModel):
    text: str
