from pydantic import BaseModel


class CategoryResponse(BaseModel):
    id: int
    name: str


class QuestionResponse(BaseModel):
    id: int
    name: str
    answer: str
    sub_question: bool
    category_id: int
    parent_question_id: int


