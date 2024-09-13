# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
#
# from app.database import get_db
# from app.questions.models import Category, Question
# from app.questions.schemas import CategoryResponse, QuestionResponse
# from fastapi_versioning import version
#
# router_question = APIRouter(
#     prefix="/question",
#     tags=["Вопросы"],
# )
#
#
# @router_question.get("/answer", response_model=list[CategoryResponse])
# @version(1)
# async def get_category(db: Session = Depends(get_db)):
#     categories = db.query(Category).all()
#     return categories
#
#
# @router_question.get("/answer-list/deep", response_model=list[QuestionResponse])
# @version(1)
# async def get_questions(level: int = 1, db: Session = Depends(get_db)):
#     questions = db.query(Question).filter(Question.sub_question == False).all()
#     return questions
#
#
# @router_question.post("/answer-list/deep/{id}", response_model=QuestionResponse)
# @version(1)
# async def answer_question(id: int, answer: str, db: Session = Depends(get_db)):
#     question = db.query(Question).filter(Question.id == id).first()
#     if not question:
#         raise HTTPException(status_code=404, detail="Question not found")
#     question.answer = answer
#     db.commit()
#     db.refresh(question)
#     return question
#
#
