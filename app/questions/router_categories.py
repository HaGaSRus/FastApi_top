import traceback
from typing import List

from fastapi import APIRouter, Depends, Path, HTTPException
from sqlalchemy import select, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.dao.dependencies import get_current_admin_user
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
    dependencies=[Depends(get_current_admin_user)]
)


# Получение всех категорий с вложенными подкатегориями
@router_categories.get("", response_model=List[CategoryResponse], summary="Получить все категории")
@version(1)
async def get_categories(db: AsyncSession = Depends(get_db)):
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

            # Создаем список подкатегорий с правильным значением edit
            subcategories_data = [
                CategoryResponse(
                    id=subcat.id,
                    name=subcat.name,
                    parent_id=subcat.parent_id,
                    subcategories=[],  # Можно дополнить, если нужно отображать вложенные подкатегории
                    edit=True,  # Здесь указываем значение edit для подкатегорий
                    number=subcat.number  # Устанавливаем значение number для подкатегорий
                )
                for subcat in category.subcategories
            ]

            # Создаем CategoryResponse для основной категории
            category_data = CategoryResponse(
                id=category.id,
                name=category.name,
                parent_id=category.parent_id,
                subcategories=subcategories_data,
                edit=True,  # Здесь устанавливаем значение edit для основной категории
                number=category.number  # Добавляем поле number
            )
            category_responses.append(category_data)

            # Добавляем информацию о подкатегориях для отладки
            logger.debug(f"Подкатегории: {subcategories_data}")

        logger.debug(f"Полученные категории с полем редактирования: {category_responses}")
        return category_responses
    except Exception as e:
        logger.error(f"Ошибка при получении категорий: {e}")
        logger.error(traceback.format_exc())
        raise ErrorGettingCategories


# Создание новой категории (только для админа)
@router_categories.post("/create", response_model=CategoryCreateResponse, summary="Создание новой категории")
@version(1)
async def create_category(
        category: CategoryCreate,
        db: AsyncSession = Depends(get_db),
):
    """Форма создания новой категории вопросов"""
    try:
        # Создаем новую категорию
        new_category = Category(name=category.name)
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)

        # Устанавливаем значение number на основе ID
        new_category.number = new_category.id
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)

        logger.info(f"Создана новая категория: {new_category}")
        return CategoryCreateResponse.model_validate(new_category)
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError при создании категории: {e}")
        raise CategoryWithTheSameNameAlreadyExists
    except Exception as e:
        logger.error(f"Ошибка при создании категории: {e}")
        logger.error(traceback.format_exc())
        raise ErrorCreatingCategory


# Создание подкатегории (только админ)
@router_categories.post("/{parent_id}/subcategories",
                        response_model=CategoryResponse,
                        summary="Создание новой под-категории")
@version(1)
async def create_subcategory(
        category: CategoryCreate,
        parent_id: int = Path(..., ge=1),
        db: AsyncSession = Depends(get_db),
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
        # existing_category = await check_existing_category(db, category.name)
        # logger.debug(f"Существующая категория: {existing_category}")

        # if existing_category:
        #     logger.warning(f"Категория с названием {category.name} уже существует.")
        #     raise CategoryWithTheSameNameAlreadyExists

        logger.debug("Создание новой подкатегории")
        new_category = await create_new_category(db, category, parent_id)
        logger.info(f"Создана новая подкатегория: {new_category}")

        # Получение данных из новой категории и создание Pydantic ответа
        mapper = inspect(Category)
        category_data = {column.name: getattr(new_category, column.name) for column in mapper.columns}
        return CategoryResponse(**category_data)

    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Ошибка IntegrityError при создании подкатегории: {e}")
        raise CategoryWithTheSameNameAlreadyExists

    except Exception as e:
        logger.error(f"Ошибка при создании подкатегории: {e}")
        logger.error(traceback.format_exc())
        raise FailedTGetDataFromDatabase


@router_categories.post("/update", response_model=List[CategoryResponse], summary="Обновление категории")
@version(1)
async def update_categories(
        category_data_list: UpdateCategoriesRequest,
        db: AsyncSession = Depends(get_db),
):
    try:
        logger.debug(f"Полученные данные для обновления: {category_data_list}")

        validated_data = category_data_list.root
        logger.debug(f"Преобразованные данные: {validated_data}")

        # Получаем текущие данные из базы данных и проверяем уникальность
        # for category_data in validated_data:
        #     existing_category = await db.execute(
        #         select(Category).where(Category.id == category_data.id)
        #     )
        #     current_category = existing_category.scalars().first()
        #
        #     if current_category:
        #         # Проверка на уникальность, если данные изменены
        #         if (current_category.name != category_data.name or
        #             current_category.number != category_data.number):
        #             # Проверка уникальности имени категории
        #             existing_category_with_same_name = await db.execute(
        #                 select(Category).where(Category.name == category_data.name)
        #             )
        #             if existing_category_with_same_name.scalars().first():
        #                 raise CategoryWithSameNameAlreadyExists(category_data.name)

        updated_categories = await process_category_updates(db, validated_data)
        logger.info(f"Успешно обновлено {len(updated_categories)} категорий")

        # Логирование полного списка данных перед отправкой на фронт
        logger.debug(f"Данные, отправляемые на фронт: {updated_categories}")

        return updated_categories

    except CategoryWithSameNameAlreadyExists as e:
        logger.error(f"Ошибка при обновлении категорий: {e.detail}")
        raise e
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Ошибка IntegrityError при обновлении категорий: {e}")
        raise ErrorUpdatingCategories
    except Exception as e:
        logger.error(f"Ошибка при обновлении категорий: {e}")
        logger.error(traceback.format_exc())
        raise FailedToUpdateCategories


@router_categories.post("/update-subcategory", response_model=List[CategoryResponse], summary="Обновление подкатегории")
@version(1)
async def update_subcategory(
        subcategories: List[UpdateCategoryData],
        db: AsyncSession = Depends(get_db),
):
    """Форма обновления подкатегории"""
    try:
        logger.debug(f"Полученные данные для обновления: {subcategories}")
        updated_subcategories = await process_subcategory_updates(db, subcategories)
        logger.info(f"Успешно обновлено {len(updated_subcategories)} подкатегорий")
        return updated_subcategories

    except HTTPException as e:
        logger.error(f"Ошибка при обновлении подкатегорий: {e.detail}")
        raise e

    except Exception as e:
        logger.error(f"Ошибка при обновлении подкатегорий: {e}")
        raise HTTPException(status_code=500, detail="Неизвестная ошибка.")


@router_categories.post("/delete", response_model=CategoryResponse, summary="Удаление категории")
@version(1)
async def delete_category(
        request: DeleteCategoryRequest,
        db: AsyncSession = Depends(get_db),
):
    """Форма удаления по id категории, при условии отсутствия подкатегории"""
    category_id = request.category_id
    try:
        logger.debug(f"Удаление категории с id: {category_id}")

        # Поиск категории
        category = await db.get(Category, category_id)
        if not category:
            logger.warning(f"Категория с id {category_id} не найдена")
            raise CategoryNotFound

        # Проверка на наличие подкатегорий
        subcategories = await db.execute(
            select(Category).where(Category.parent_id == category_id)
        )
        if subcategories.scalars().first():
            logger.warning(f"Категория с id {category_id} содержит подкатегории, удаление невозможно")
            raise CategoryContainsSubcategoriesDeletionIsNotPossible

        # Удаление категории
        await db.delete(category)
        await db.commit()

        logger.info(f"Категория с id {category_id} успешно удалена")

        # Используем model_validate для валидации объекта через атрибуты модели
        return CategoryResponse.model_validate(category)

    except Exception as e:
        logger.error(f"Ошибка при удалении категории: {e}")
        logger.error(traceback.format_exc())
        await db.rollback()  # Откат транзакции при ошибке
        raise FailedToDeleteCategory

