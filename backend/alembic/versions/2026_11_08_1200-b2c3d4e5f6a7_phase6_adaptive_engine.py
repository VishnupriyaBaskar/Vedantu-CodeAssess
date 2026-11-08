"""phase6_adaptive_engine

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-08 12:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add student_topic_mastery and topic_mastery_history tables for Phase 6."""
    # 1. Create student_topic_mastery
    op.create_table(
        'student_topic_mastery',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('mastery_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('mastery_level', sa.String(length=50), nullable=False, server_default='BEGINNER'),
        sa.Column('confidence_level', sa.String(length=50), nullable=False, server_default='LOW'),
        sa.Column('questions_attempted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('questions_solved', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_submissions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_submissions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('best_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('recommended_difficulty', sa.String(length=50), nullable=False, server_default='EASY'),
        sa.Column('trend', sa.String(length=50), nullable=False, server_default='STABLE'),
        sa.Column('last_calculated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'topic', name='uq_student_topic_mastery_user_topic')
    )
    op.create_index(op.f('ix_student_topic_mastery_user_id'), 'student_topic_mastery', ['user_id'], unique=False)
    op.create_index(op.f('ix_student_topic_mastery_topic'), 'student_topic_mastery', ['topic'], unique=False)
    op.create_index(op.f('ix_student_topic_mastery_mastery_level'), 'student_topic_mastery', ['mastery_level'], unique=False)
    op.create_index(op.f('ix_student_topic_mastery_last_calculated_at'), 'student_topic_mastery', ['last_calculated_at'], unique=False)

    # 2. Create topic_mastery_history
    op.create_table(
        'topic_mastery_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('mastery_score', sa.Float(), nullable=False),
        sa.Column('mastery_level', sa.String(length=50), nullable=False),
        sa.Column('trigger_event', sa.String(length=50), nullable=False, server_default='RECALCULATION'),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_topic_mastery_history_user_id'), 'topic_mastery_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_topic_mastery_history_topic'), 'topic_mastery_history', ['topic'], unique=False)
    op.create_index(op.f('ix_topic_mastery_history_recorded_at'), 'topic_mastery_history', ['recorded_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema to remove student_topic_mastery and topic_mastery_history tables."""
    op.drop_index(op.f('ix_topic_mastery_history_recorded_at'), table_name='topic_mastery_history')
    op.drop_index(op.f('ix_topic_mastery_history_topic'), table_name='topic_mastery_history')
    op.drop_index(op.f('ix_topic_mastery_history_user_id'), table_name='topic_mastery_history')
    op.drop_table('topic_mastery_history')

    op.drop_index(op.f('ix_student_topic_mastery_last_calculated_at'), table_name='student_topic_mastery')
    op.drop_index(op.f('ix_student_topic_mastery_mastery_level'), table_name='student_topic_mastery')
    op.drop_index(op.f('ix_student_topic_mastery_topic'), table_name='student_topic_mastery')
    op.drop_index(op.f('ix_student_topic_mastery_user_id'), table_name='student_topic_mastery')
    op.drop_table('student_topic_mastery')
