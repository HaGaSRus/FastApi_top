from pydantic import BaseModel, Field, RootModel
from typing import Optional, List


class CategoryBase(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True


class CategoryResponse(CategoryBase):
    subcategories: Optional[List['CategoryResponse']] = Field(default_factory=list)
    edit: bool = Field(default=False)
    number: Optional[int] = None

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str


class CategoryCreateResponse(CategoryBase):
    class Config:
        from_attributes = True


class SubQuestionCreate(BaseModel):
    author: Optional[str] = None
    text: str
    answer: Optional[str] = None
    number: Optional[int] = 0
    count: Optional[int] = 0
    depth: int

    parent_question_id: int
    parent_subquestion_id: Optional[int] = 0
    category_id: Optional[int] = 0
    subcategory_id: Optional[int] = 0


class QuestionCreate(BaseModel):
    author: Optional[str] = None
    text: str
    answer: Optional[str] = None
    number: Optional[int] = 0
    category_id: Optional[int]
    subcategory_id: Optional[int] = 0
    count: Optional[int]
    parent_question_id: Optional[int] = 0
    is_subquestion: bool = False
    parent_subquestion_id: Optional[int] = 0

    class Config:
        from_attributes = True


class SubQuestionResponse(BaseModel):
    id: int
    text: str
    answer: Optional[str] = None
    number: int
    author: Optional[str] = None
    count: Optional[int] = 0
    parent_question_id: int
    depth: int
    parent_subquestion_id: Optional[int] = 0
    category_id: Optional[int] = 0
    subcategory_id: Optional[int] = 0
    sub_questions: List['SubQuestionResponse'] = []

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: int
    text: str
    category_id: int
    subcategory_id: Optional[int] = 0
    answer: Optional[str] = None
    number: int
    author: Optional[str] = None
    depth: int
    count: Optional[int] = 0
    parent_question_id: Optional[int] = 0

    sub_questions: List[SubQuestionResponse] = []

    class Config:
        from_attributes = True


class DeleteCategoryRequest(BaseModel):
    category_id: int


class UpdateCategoryData(BaseModel):
    id: int
    number: int
    name: str


class UpdateCategoriesRequest(RootModel[list[UpdateCategoryData]]):
    pass


class UpdateCategoryData(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    number: int


class UpdateQuestionRequest(BaseModel):
    question_id: int = Field(..., description="ID основного вопроса")
    sub_question_id: Optional[int] = Field(None, description="ID под-вопроса (если указан) ")
    text: Optional[str] = Field(None, description="Новый текст вопроса или под-вопроса")
    answer: Optional[str] = Field(None, description="Новый ответ вопроса или под-вопроса")
    author: Optional[str] = None


class DeleteQuestionRequest(BaseModel):
    question_id: int = Field(..., description="ID основного вопроса")
    sub_question_id: Optional[int] = Field(None, description="ID под-вопроса (если указан)")


class QuestionIDRequest(BaseModel):
    question_id: int


class QuestionResponseForPagination(BaseModel):
    id: int
    text: str
    category_id: int
    subcategory_id: Optional[int] = None
    answer: Optional[str] = None
    number: int
    depth: int
    count: Optional[int] = None
    parent_question_id: Optional[int] = None
    sub_questions: List['QuestionResponse'] = []
    is_depth: bool

    class Config:
        from_attributes = True
