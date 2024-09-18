"""truncate category table

Revision ID: 2622b4bfda7d
Revises: 31061b0362ad
Create Date: 2024-09-18 13:44:33.473483

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2622b4bfda7d"
down_revision = "31061b0362ad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Используем команду TRUNCATE для очистки таблицы
    op.execute('TRUNCATE TABLE categories RESTART IDENTITY CASCADE')

def downgrade() -> None:
    # В этом случае, если вы хотите откатить миграцию, это может быть пустым,
    # так как мы просто очищаем таблицу и нет данных для восстановления.
    pass