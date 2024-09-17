from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.questions.models import Category
from app.questions.schemas import CategoryCreate


async def fetch_parent_category(db: AsyncSession, parent_id: int) -> Category:
    query = select(Category).where(Category.id == parent_id)
    result = await db.execute(query)
    parent_category = result.scalar_one_or_none()
    return parent_category

async def check_existing_category(db: AsyncSession, category_name: str) -> Category:
    query = select(Category).where(Category.name == category_name)
    result = await db.execute(query)
    existing_category = result.scalar_one_or_none()
    return existing_category

async def create_new_category(db: AsyncSession, category: CategoryCreate, parent_id: int) -> Category:
    new_category = Category(name=category.name, parent_id=parent_id)
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category
