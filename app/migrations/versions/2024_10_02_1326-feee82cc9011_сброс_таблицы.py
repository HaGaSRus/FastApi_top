"""сброс таблицы

Revision ID: feee82cc9011
Revises: aec9079cf6c4
Create Date: 2024-10-02 13:26:19.949313

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "feee82cc9011"
down_revision = "aec9079cf6c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('TRUNCATE TABLE sub_questions RESTART IDENTITY CASCADE')
    op.execute('TRUNCATE TABLE questions RESTART IDENTITY CASCADE')
    op.execute('TRUNCATE TABLE categories RESTART IDENTITY CASCADE')


def downgrade() -> None:
    pass
