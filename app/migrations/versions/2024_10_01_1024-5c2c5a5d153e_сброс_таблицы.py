"""сброс таблицы

Revision ID: 5c2c5a5d153e
Revises: caf8273f771d
Create Date: 2024-10-01 10:24:45.591697

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5c2c5a5d153e"
down_revision = "caf8273f771d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Используем команду TRUNCATE для очистки таблицы
    op.execute('TRUNCATE TABLE sub_questions RESTART IDENTITY CASCADE')


def downgrade() -> None:
    pass
