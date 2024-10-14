"""truncate category table1

Revision ID: 311b834f479f
Revises: 2622b4bfda7d
Create Date: 2024-09-19 16:39:36.545311

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "311b834f479f"
down_revision = "2622b4bfda7d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Используем команду TRUNCATE для очистки таблицы
    op.execute('TRUNCATE TABLE categories RESTART IDENTITY CASCADE')

def downgrade() -> None:
    # В этом случае, если вы хотите откатить миграцию, это может быть пустым,
    # так как мы просто очищаем таблицу и нет данных для восстановления.
    pass