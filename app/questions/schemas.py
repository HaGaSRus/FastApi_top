from pydantic import BaseModel, Field
from typing import Optional, List, ForwardRef

CategoryResponseRef = ForwardRef('CategoryResponse')
QuestionResponseRef = ForwardRef('QuestionResponse')


class CategoryBase(BaseModel):
    id: str
    name: str
    parent_id: Optional[int]


class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    subcategories: Optional[List[CategoryResponseRef]] = Field(default_factory=list)

    class Config:
        orm_mode = True
        from_attributes = True


class QuestionBase(BaseModel):
    id: int
    text: str
    answer: Optional[str] = None
    category_id: int
    parent_question_id: Optional[int] = None


class QuestionResponse(BaseModel):
    id: int
    text: str
    answer: Optional[str] = None
    category_id: int
    parent_question_id: Optional[int] = None
    sub_questions: List['QuestionResponse'] = []

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str


class SubCategoryCreate(BaseModel):
    name: str


class QuestionCreate(BaseModel):
    text: str


class SubQuestionCreate(BaseModel):
    text: str


class CategoryCreateResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None

    class Config:
        orm_mode = True
        from_attributes = True


CategoryResponse.model_rebuild()
QuestionResponse.model_rebuild()

