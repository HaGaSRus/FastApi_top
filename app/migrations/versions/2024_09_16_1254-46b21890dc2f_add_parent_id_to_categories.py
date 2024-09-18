"""Add parent_id to categories

Revision ID: 46b21890dc2f
Revises: 20c3165e94d2
Create Date: 2024-09-16 12:54:38.319838

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "46b21890dc2f"
down_revision = "20c3165e94d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "categories", sa.Column("parent_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        None, "categories", "categories", ["parent_id"], ["id"]
    )
    op.add_column("questions", sa.Column("text", sa.String(), nullable=True))
    op.drop_index("ix_questions_name", table_name="questions")
    op.create_index(
        op.f("ix_questions_text"), "questions", ["text"], unique=False
    )
    op.drop_column("questions", "name")
    op.drop_column("questions", "sub_question")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "questions",
        sa.Column(
            "sub_question", sa.BOOLEAN(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "questions",
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.drop_index(op.f("ix_questions_text"), table_name="questions")
    op.create_index("ix_questions_name", "questions", ["name"], unique=False)
    op.drop_column("questions", "text")
    op.drop_constraint(None, "categories", type_="foreignkey")
    op.drop_column("categories", "parent_id")
    # ### end Alembic commands ###
