"""phase8_analytics_and_question_mgmt

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-08 16:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add question tags/starter_code and test_case category for Phase 8."""
    op.add_column('questions', sa.Column('tags', sa.String(length=255), nullable=True))
    op.add_column('questions', sa.Column('starter_code', sa.Text(), nullable=True))
    op.add_column('test_cases', sa.Column('category', sa.String(length=50), nullable=False, server_default='FUNCTIONAL'))
    op.create_index(op.f('ix_test_cases_category'), 'test_cases', ['category'], unique=False)

    # Set existing sample test cases (is_hidden = False) category to 'SAMPLE'
    op.execute("UPDATE test_cases SET category = 'SAMPLE' WHERE is_hidden = false")


def downgrade() -> None:
    """Downgrade schema to remove Phase 8 question/test_case extensions."""
    op.drop_index(op.f('ix_test_cases_category'), table_name='test_cases')
    op.drop_column('test_cases', 'category')
    op.drop_column('questions', 'starter_code')
    op.drop_column('questions', 'tags')
