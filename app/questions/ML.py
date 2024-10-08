# from transformers import AutoTokenizer, AutoModel
# import torch
# from sklearn.metrics.pairwise import cosine_similarity
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# import numpy as np
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from app.questions.models import Question
#
# # Загрузка модели RUBERT
# tokenizer = AutoTokenizer.from_pretrained("DeepPavlov/rubert-base-cased")
# model = AutoModel.from_pretrained("DeepPavlov/rubert-base-cased")
#
#
# # Функция для создания эмбеддингов и сохранения их в БД
# async def save_question_embeddings(db: AsyncSession, model, tokenizer):
#     questions = await db.execute(select(Question))
#     questions = questions.scalars().all()
#
#     for question in questions:
#         # Получение эмбеддинга вопроса
#         embedding = get_embedding(question.text, model, tokenizer)
#
#         # Сохранение эмбеддинга в базу данных (например, в отдельное поле или таблицу)
#         question.embedding = np.array(embedding).tolist()  # Преобразование в список для сохранения
#
#         # Сохранение обновленного вопроса с эмбеддингом
#         db.add(question)
#     await db.commit()
#
#
# # Функция для генерации эмбеддингов
# def get_embedding(text, model, tokenizer):
#     inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
#     with torch.no_grad():
#         outputs = model(**inputs)
#     return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
#
#
# # Функция поиска схожих вопросов
# def find_similar_questions(query, questions, top_n=5):
#     query_embedding = get_embedding(query)
#     question_embeddings = [get_embedding(question.text) for question in questions]
#
#     similarities = cosine_similarity([query_embedding], question_embeddings).flatten()
#
#     # Сортировка по схожести и возврат топ-N вопросов
#     top_indices = similarities.argsort()[-top_n:][::-1]
#     return [questions[i] for i in top_indices]
#
#
# # Использование функции
# # similar_questions = find_similar_questions("Как создать таблицу в SQL?", all_questions)
#
#
# # Функция для создания эмбеддингов и сохранения их в БД
# async def save_question_embeddings(db: AsyncSession, model, tokenizer):
#     questions = await db.execute(select(Question))
#     questions = questions.scalars().all()
#
#     for question in questions:
#         # Получение эмбеддинга вопроса
#         embedding = get_embedding(question.text, model, tokenizer)
#
#         # Сохранение эмбеддинга в базу данных (например, в отдельное поле или таблицу)
#         question.embedding = np.array(embedding).tolist()  # Преобразование в список для сохранения
#
#         # Сохранение обновленного вопроса с эмбеддингом
#         db.add(question)
#     await db.commit()
#
#
# # Функция для генерации эмбеддингов
# def get_embedding(text, model, tokenizer):
#     inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
#     with torch.no_grad():
#         outputs = model(**inputs)
#     return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
#
#
# async def search_similar_questions(query: str, db: AsyncSession, model, tokenizer, top_n: int = 5):
#     # Получение эмбеддинга для запроса
#     query_embedding = get_embedding(query, model, tokenizer)
#
#     # Загрузка всех вопросов с эмбеддингами
#     questions = await db.execute(select(Question))
#     questions = questions.scalars().all()
#
#     # Если нет сохраненных эмбеддингов, вернуть пустой результат
#     if not questions:
#         return []
#
#     # Вычисление схожести запроса с эмбеддингами вопросов
#     question_embeddings = [np.array(question.embedding) for question in questions]
#     similarities = cosine_similarity([query_embedding], question_embeddings).flatten()
#
#     # Сортировка по схожести и возврат топ-N вопросов
#     top_indices = similarities.argsort()[-top_n:][::-1]
#     return [questions[i] for i in top_indices]
#
#
# # Функция поиска схожих вопросов по эмбеддингам
# async def search_similar_questions(query: str, db: AsyncSession, model, tokenizer, top_n: int = 5):
#     # Получение эмбеддинга для запроса
#     query_embedding = get_embedding(query, model, tokenizer)
#
#     # Загрузка всех вопросов с эмбеддингами
#     questions = await db.execute(select(Question))
#     questions = questions.scalars().all()
#
#     # Если нет сохраненных эмбеддингов, вернуть пустой результат
#     if not questions:
#         return []
#
#     # Вычисление схожести запроса с эмбеддингами вопросов
#     question_embeddings = [np.array(question.embedding) for question in questions]
#     similarities = cosine_similarity([query_embedding], question_embeddings).flatten()
#
#     # Сортировка по схожести и возврат топ-N вопросов
#     top_indices = similarities.argsort()[-top_n:][::-1]
#     return [questions[i] for i in top_indices]
#
#
# # Создаем планировщик
# scheduler = AsyncIOScheduler()
#
# # Функция для обновления эмбеддингов всех вопросов
# async def update_question_embeddings():
#     async with get_db() as db:
#         await save_question_embeddings(db, model, tokenizer)
#
# # Добавляем задачу в планировщик (например, каждые 24 часа)
# scheduler.add_job(update_question_embeddings, "interval", hours=24)
# scheduler.start()