"""phase7_advanced_proctoring

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-08 14:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add proctoring tables and assessment proctoring_config for Phase 7."""
    # 1. Add proctoring_config to assessments table
    op.add_column('assessments', sa.Column('proctoring_config', sa.JSON(), nullable=True))

    # 2. Create proctoring_sessions table
    op.create_table(
        'proctoring_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('assessment_attempt_id', sa.UUID(), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='INITIALIZED'),
        sa.Column('consent_given', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('consent_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('monitoring_config', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['assessment_attempt_id'], ['assessment_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_attempt_id', name='uq_proctoring_sessions_attempt')
    )
    op.create_index(op.f('ix_proctoring_sessions_assessment_attempt_id'), 'proctoring_sessions', ['assessment_attempt_id'], unique=False)
    op.create_index(op.f('ix_proctoring_sessions_assessment_id'), 'proctoring_sessions', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_proctoring_sessions_user_id'), 'proctoring_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_proctoring_sessions_status'), 'proctoring_sessions', ['status'], unique=False)

    # 3. Create proctoring_events table
    op.create_table(
        'proctoring_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('proctoring_session_id', sa.UUID(), nullable=False),
        sa.Column('assessment_attempt_id', sa.UUID(), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='LOW'),
        sa.Column('event_metadata', sa.JSON(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['assessment_attempt_id'], ['assessment_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['proctoring_session_id'], ['proctoring_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_proctoring_events_proctoring_session_id'), 'proctoring_events', ['proctoring_session_id'], unique=False)
    op.create_index(op.f('ix_proctoring_events_assessment_attempt_id'), 'proctoring_events', ['assessment_attempt_id'], unique=False)
    op.create_index(op.f('ix_proctoring_events_assessment_id'), 'proctoring_events', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_proctoring_events_user_id'), 'proctoring_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_proctoring_events_event_type'), 'proctoring_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_proctoring_events_severity'), 'proctoring_events', ['severity'], unique=False)
    op.create_index(op.f('ix_proctoring_events_recorded_at'), 'proctoring_events', ['recorded_at'], unique=False)

    # 4. Create proctoring_alerts table
    op.create_table(
        'proctoring_alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('proctoring_session_id', sa.UUID(), nullable=False),
        sa.Column('assessment_attempt_id', sa.UUID(), nullable=False),
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('alert_category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('related_event_ids', sa.JSON(), nullable=True),
        sa.Column('review_status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assessment_attempt_id'], ['assessment_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['proctoring_session_id'], ['proctoring_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_proctoring_alerts_proctoring_session_id'), 'proctoring_alerts', ['proctoring_session_id'], unique=False)
    op.create_index(op.f('ix_proctoring_alerts_assessment_attempt_id'), 'proctoring_alerts', ['assessment_attempt_id'], unique=False)
    op.create_index(op.f('ix_proctoring_alerts_assessment_id'), 'proctoring_alerts', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_proctoring_alerts_user_id'), 'proctoring_alerts', ['user_id'], unique=False)
    op.create_index(op.f('ix_proctoring_alerts_alert_category'), 'proctoring_alerts', ['alert_category'], unique=False)
    op.create_index(op.f('ix_proctoring_alerts_severity'), 'proctoring_alerts', ['severity'], unique=False)
    op.create_index(op.f('ix_proctoring_alerts_review_status'), 'proctoring_alerts', ['review_status'], unique=False)
    op.create_index(op.f('ix_proctoring_alerts_created_at'), 'proctoring_alerts', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema to drop proctoring tables and assessment proctoring_config."""
    op.drop_table('proctoring_alerts')
    op.drop_table('proctoring_events')
    op.drop_table('proctoring_sessions')
    op.drop_column('assessments', 'proctoring_config')
