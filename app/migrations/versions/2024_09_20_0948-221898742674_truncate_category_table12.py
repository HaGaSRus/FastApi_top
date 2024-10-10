"""truncate category table12

Revision ID: 221898742674
Revises: 311b834f479f
Create Date: 2024-09-20 09:48:13.678567

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "221898742674"
down_revision = "311b834f479f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Используем команду TRUNCATE для очистки таблицы
    op.execute('TRUNCATE TABLE categories RESTART IDENTITY CASCADE')

def downgrade() -> None:
    # В этом случае, если вы хотите откатить миграцию, это может быть пустым,
    # так как мы просто очищаем таблицу и нет данных для восстановления.
    pass
