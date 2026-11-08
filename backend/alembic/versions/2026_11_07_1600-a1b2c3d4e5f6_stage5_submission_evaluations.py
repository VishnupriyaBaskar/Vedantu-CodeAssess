"""stage5_submission_evaluations

Revision ID: a1b2c3d4e5f6
Revises: 9e7e46f4e4b1
Create Date: 2026-11-07 16:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9e7e46f4e4b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add submission_evaluations table for Stage 5."""
    op.create_table(
        'submission_evaluations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('submission_id', sa.UUID(), nullable=False),
        sa.Column('static_analysis', sa.JSON(), nullable=True),
        sa.Column('ai_feedback', sa.JSON(), nullable=True),
        sa.Column('ai_provider', sa.String(length=50), nullable=False),
        sa.Column('ai_status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('submission_id', name='uq_submission_evaluations_submission_id')
    )
    op.create_index(op.f('ix_submission_evaluations_ai_status'), 'submission_evaluations', ['ai_status'], unique=False)
    op.create_index(op.f('ix_submission_evaluations_created_at'), 'submission_evaluations', ['created_at'], unique=False)
    op.create_index(op.f('ix_submission_evaluations_submission_id'), 'submission_evaluations', ['submission_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema to remove submission_evaluations table."""
    op.drop_index(op.f('ix_submission_evaluations_submission_id'), table_name='submission_evaluations')
    op.drop_index(op.f('ix_submission_evaluations_created_at'), table_name='submission_evaluations')
    op.drop_index(op.f('ix_submission_evaluations_ai_status'), table_name='submission_evaluations')
    op.drop_table('submission_evaluations')
