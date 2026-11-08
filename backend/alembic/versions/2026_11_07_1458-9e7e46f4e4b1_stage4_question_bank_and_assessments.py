"""stage4_question_bank_and_assessments

Revision ID: 9e7e46f4e4b1
Revises: 3faee3e02f86
Create Date: 2026-11-07 14:58:00.573199+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e7e46f4e4b1'
down_revision: Union[str, Sequence[str], None] = '3faee3e02f86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('assessment_attempts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.Column('percentage', sa.Float(), nullable=False),
        sa.Column('is_passed', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'user_id', name='uq_assessment_attempts_user')
    )
    op.create_index(op.f('ix_assessment_attempts_assessment_id'), 'assessment_attempts', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_assessment_attempts_status'), 'assessment_attempts', ['status'], unique=False)
    op.create_index(op.f('ix_assessment_attempts_user_id'), 'assessment_attempts', ['user_id'], unique=False)

    op.create_table('assessment_candidates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id', 'user_id', name='uq_assessment_candidates')
    )
    op.create_index(op.f('ix_assessment_candidates_assessment_id'), 'assessment_candidates', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_assessment_candidates_user_id'), 'assessment_candidates', ['user_id'], unique=False)

    op.create_table('code_drafts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('question_id', sa.UUID(), nullable=False),
        sa.Column('programming_language_id', sa.UUID(), nullable=False),
        sa.Column('source_code', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['programming_language_id'], ['programming_languages.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'assessment_id', 'question_id', name='uq_code_drafts_user_assessment_question')
    )
    op.create_index(op.f('ix_code_drafts_assessment_id'), 'code_drafts', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_code_drafts_programming_language_id'), 'code_drafts', ['programming_language_id'], unique=False)
    op.create_index(op.f('ix_code_drafts_question_id'), 'code_drafts', ['question_id'], unique=False)
    op.create_index(op.f('ix_code_drafts_user_id'), 'code_drafts', ['user_id'], unique=False)

    op.create_table('submission_test_case_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('submission_id', sa.UUID(), nullable=False),
        sa.Column('test_case_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('execution_time', sa.Float(), nullable=True),
        sa.Column('memory_usage', sa.Integer(), nullable=True),
        sa.Column('marks_awarded', sa.Float(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('is_sample', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_submission_test_case_results_submission_id'), 'submission_test_case_results', ['submission_id'], unique=False)
    op.create_index(op.f('ix_submission_test_case_results_test_case_id'), 'submission_test_case_results', ['test_case_id'], unique=False)

    op.add_column('assessments', sa.Column('instructions', sa.Text(), nullable=True))
    op.add_column('assessments', sa.Column('passing_marks', sa.Integer(), nullable=False, server_default='40'))
    op.add_column('assessments', sa.Column('allowed_languages', sa.String(length=255), nullable=False, server_default='ALL_ACTIVE'))

    op.add_column('questions', sa.Column('topic', sa.String(length=100), nullable=False, server_default='General'))
    op.add_column('questions', sa.Column('time_limit_seconds', sa.Float(), nullable=False, server_default='2.0'))
    op.add_column('questions', sa.Column('memory_limit_mb', sa.Integer(), nullable=False, server_default='256'))
    op.add_column('questions', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('questions', sa.Column('created_by', sa.UUID(), nullable=True))
    op.alter_column('questions', 'assessment_id', existing_type=sa.UUID(), nullable=True)
    op.create_index(op.f('ix_questions_created_by'), 'questions', ['created_by'], unique=False)
    op.create_index(op.f('ix_questions_difficulty'), 'questions', ['difficulty'], unique=False)
    op.create_index(op.f('ix_questions_is_archived'), 'questions', ['is_archived'], unique=False)
    op.create_index(op.f('ix_questions_topic'), 'questions', ['topic'], unique=False)
    op.create_foreign_key('fk_questions_created_by_users', 'questions', 'users', ['created_by'], ['id'], ondelete='SET NULL')

    op.add_column('submissions', sa.Column('assessment_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_submissions_assessment_id'), 'submissions', ['assessment_id'], unique=False)
    op.create_foreign_key('fk_submissions_assessment_id_assessments', 'submissions', 'assessments', ['assessment_id'], ['id'], ondelete='RESTRICT')

    op.add_column('test_cases', sa.Column('explanation', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('test_cases', 'explanation')

    op.drop_constraint('fk_submissions_assessment_id_assessments', 'submissions', type_='foreignkey')
    op.drop_index(op.f('ix_submissions_assessment_id'), table_name='submissions')
    op.drop_column('submissions', 'assessment_id')

    op.drop_constraint('fk_questions_created_by_users', 'questions', type_='foreignkey')
    op.drop_index(op.f('ix_questions_topic'), table_name='questions')
    op.drop_index(op.f('ix_questions_is_archived'), table_name='questions')
    op.drop_index(op.f('ix_questions_difficulty'), table_name='questions')
    op.drop_index(op.f('ix_questions_created_by'), table_name='questions')
    op.alter_column('questions', 'assessment_id', existing_type=sa.UUID(), nullable=False)
    op.drop_column('questions', 'created_by')
    op.drop_column('questions', 'is_archived')
    op.drop_column('questions', 'memory_limit_mb')
    op.drop_column('questions', 'time_limit_seconds')
    op.drop_column('questions', 'topic')

    op.drop_column('assessments', 'allowed_languages')
    op.drop_column('assessments', 'passing_marks')
    op.drop_column('assessments', 'instructions')

    op.drop_index(op.f('ix_submission_test_case_results_test_case_id'), table_name='submission_test_case_results')
    op.drop_index(op.f('ix_submission_test_case_results_submission_id'), table_name='submission_test_case_results')
    op.drop_table('submission_test_case_results')

    op.drop_index(op.f('ix_code_drafts_user_id'), table_name='code_drafts')
    op.drop_index(op.f('ix_code_drafts_question_id'), table_name='code_drafts')
    op.drop_index(op.f('ix_code_drafts_programming_language_id'), table_name='code_drafts')
    op.drop_index(op.f('ix_code_drafts_assessment_id'), table_name='code_drafts')
    op.drop_table('code_drafts')

    op.drop_index(op.f('ix_assessment_candidates_user_id'), table_name='assessment_candidates')
    op.drop_index(op.f('ix_assessment_candidates_assessment_id'), table_name='assessment_candidates')
    op.drop_table('assessment_candidates')

    op.drop_index(op.f('ix_assessment_attempts_user_id'), table_name='assessment_attempts')
    op.drop_index(op.f('ix_assessment_attempts_status'), table_name='assessment_attempts')
    op.drop_index(op.f('ix_assessment_attempts_assessment_id'), table_name='assessment_attempts')
    op.drop_table('assessment_attempts')
