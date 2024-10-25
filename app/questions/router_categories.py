import traceback
from typing import List
from fastapi import APIRouter, Depends, Path, HTTPException
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.dao.dependencies import get_current_user, get_current_admin_or_moderator_user, get_current_admin_user
from app.database import get_db
from app.exceptions import ErrorGettingCategories, CategoryWithTheSameNameAlreadyExists, ErrorCreatingCategory, \
    ParentCategoryNotFound, FailedTGetDataFromDatabase, CategoryWithSameNameAlreadyExists, ErrorUpdatingCategories, \
    FailedToUpdateCategories, CategoryNotFound, CategoryContainsSubcategoriesDeletionIsNotPossible, \
    FailedToDeleteCategory
from app.logger.logger import logger
from app.questions.models import Category
from app.questions.schemas import CategoryResponse, CategoryCreateResponse, CategoryCreate, UpdateCategoriesRequest, \
    UpdateCategoryData, DeleteCategoryRequest
from fastapi_versioning import version
from app.questions.utils import fetch_parent_category, create_new_category, \
    process_category_updates, process_subcategory_updates

router_categories = APIRouter(
    prefix="/categories",
    tags=["Категории"],
)


@router_categories.get("", response_model=List[CategoryResponse], summary="Получить все категории")
@version(1)
async def get_categories(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Отобразить все категории имеющиеся в Базе данных"""
    try:
        logger.debug("Выполнение запроса для получения корневых категорий с parent_id == None")
        result = await db.execute(
            select(Category).where(Category.parent_id.is_(None)).options(selectinload(Category.subcategories))
        )
        categories = result.scalars().all()

        category_responses = []
        for category in categories:
            logger.debug(f"Обрабатываем категорию: {category}")

            subcategories_data = [
                CategoryResponse(
                    id=subcat.id,
                    name=subcat.name,
                    parent_id=subcat.parent_id,
                    subcategories=[],
                    edit=True,
                    number=subcat.number
                )
                for subcat in category.subcategories
            ]

            category_data = CategoryResponse(
                id=category.id,
                name=category.name,
                parent_id=category.parent_id,
                subcategories=subcategories_data,
                edit=True,
                number=category.number
            )
            category_responses.append(category_data)

            logger.debug(f"Подкатегории: {subcategories_data}")

        logger.debug(f"Полученные категории с полем редактирования: {category_responses}")
        return category_responses
    except Exception as e:
        logger.warning(f"Ошибка при получении категорий: {e}")
        logger.warning(traceback.format_exc())
        raise ErrorGettingCategories


@router_categories.post("/create", response_model=CategoryCreateResponse, summary="Создание новой категории")
@version(1)
async def create_category(
        category: CategoryCreate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_or_moderator_user)
):
    """Форма создания новой категории вопросов"""
    try:
        new_category = Category(name=category.name)
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)

        new_category.number = new_category.id
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)

        return CategoryCreateResponse.model_validate(new_category)
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"IntegrityError при создании категории: {e}")
        raise CategoryWithTheSameNameAlreadyExists
    except Exception as e:
        logger.warning(f"Ошибка при создании категории: {e}")
        logger.warning(traceback.format_exc())
        raise ErrorCreatingCategory


@router_categories.post("/{parent_id}/subcategories",
                        response_model=CategoryResponse,
                        summary="Создание новой под-категории")
@version(1)
async def create_subcategory(
        category: CategoryCreate,
        parent_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_or_moderator_user),
):
    """Форма создания новой под-категории вопросов"""
    try:
        logger.debug(f"Получение родительской категории с идентификатором: {parent_id}")
        parent_category = await fetch_parent_category(db, parent_id)
        logger.debug(f"Родительская категория: {parent_category}")

        if not parent_category:
            logger.warning(f"Родительская категория с идентификатором {parent_id} не найдена")
            raise ParentCategoryNotFound

        logger.debug(f"Проверка наличия категории с именем {category.name}.")

        logger.debug("Создание новой подкатегории")
        new_category = await create_new_category(db, category, parent_id)

        mapper = inspect(Category)
        category_data = {column.name: getattr(new_category, column.name) for column in mapper.columns}
        return CategoryResponse(**category_data)

    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"Ошибка IntegrityError при создании подкатегории: {e}")
        raise CategoryWithTheSameNameAlreadyExists

    except Exception as e:
        logger.warning(f"Ошибка при создании подкатегории: {e}")
        logger.warning(traceback.format_exc())
        raise FailedTGetDataFromDatabase


@router_categories.post("/update", response_model=List[CategoryResponse], summary="Обновление категории")
@version(1)
async def update_categories(
        category_data_list: UpdateCategoriesRequest,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_or_moderator_user)
):
    try:
        logger.debug(f"Полученные данные для обновления: {category_data_list}")

        validated_data = category_data_list.root
        logger.debug(f"Преобразованные данные: {validated_data}")

        updated_categories = await process_category_updates(db, validated_data)

        logger.debug(f"Данные, отправляемые на фронт: {updated_categories}")

        return updated_categories

    except CategoryWithSameNameAlreadyExists as e:
        logger.warning(f"Ошибка при обновлении категорий: {e.detail}")
        raise e
    except IntegrityError as e:
        await db.rollback()
        logger.warning(f"Ошибка IntegrityError при обновлении категорий: {e}")
        raise ErrorUpdatingCategories
    except Exception as e:
        logger.warning(f"Ошибка при обновлении категорий: {e}")
        logger.warning(traceback.format_exc())
        raise FailedToUpdateCategories


@router_categories.post("/update-subcategory", response_model=List[CategoryResponse], summary="Обновление подкатегории")
@version(1)
async def update_subcategory(
        subcategories: List[UpdateCategoryData],
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_or_moderator_user)
):
    """Форма обновления подкатегории"""
    try:
        logger.debug(f"Полученные данные для обновления: {subcategories}")
        updated_subcategories = await process_subcategory_updates(db, subcategories)
        return updated_subcategories

    except HTTPException as e:
        logger.warning(f"Ошибка при обновлении подкатегорий: {e.detail}")
        raise e

    except Exception as e:
        logger.warning(f"Ошибка при обновлении подкатегорий: {e}")
        raise HTTPException(status_code=500, detail="Неизвестная ошибка.")


@router_categories.post("/delete", response_model=CategoryResponse, summary="Удаление категории")
@version(1)
async def delete_category(
        request: DeleteCategoryRequest,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_admin_user)
):
    """Форма удаления по id категории, при условии отсутствия подкатегории"""
    category_id = request.category_id
    try:
        logger.debug(f"Удаление категории с id: {category_id}")

        category = await db.get(Category, category_id)
        if not category:
            logger.warning(f"Категория с id {category_id} не найдена")
            raise CategoryNotFound

        subcategories = await db.execute(
            select(Category).where(Category.parent_id == category_id)
        )
        if subcategories.scalars().first():
            logger.warning(f"Категория с id {category_id} содержит подкатегории, удаление невозможно")
            raise CategoryContainsSubcategoriesDeletionIsNotPossible

        await db.delete(category)
        await db.commit()

        return CategoryResponse.model_validate(category)

    except Exception as e:
        logger.warning(f"Ошибка при удалении категории: {e}")
        logger.warning(traceback.format_exc())
        await db.rollback()
        raise FailedToDeleteCategory

