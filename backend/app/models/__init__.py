r"""
Database Models Package
Project: Vedantu Online Coding Assessment Platform (Stage 4)
Workspace: E:\VedantuCodingPlatform_New

Exposes declarative base and all domain entity models for Alembic metadata discovery and ORM operations.
"""

from app.models.base import Base, TimestampMixin, utc_now
from app.models.user import User
from app.models.role import Role, UserRole
from app.models.assessment import Assessment
from app.models.question import Question
from app.models.programming_language import ProgrammingLanguage
from app.models.test_case import TestCase
from app.models.submission import Submission
from app.models.assessment_candidate import AssessmentCandidate
from app.models.assessment_attempt import AssessmentAttempt
from app.models.code_draft import CodeDraft
from app.models.submission_test_case_result import SubmissionTestCaseResult
from app.models.submission_evaluation import SubmissionEvaluation
from app.models.student_topic_mastery import StudentTopicMastery
from app.models.topic_mastery_history import TopicMasteryHistory
from app.models.proctoring_session import ProctoringSession
from app.models.proctoring_event import ProctoringEvent
from app.models.proctoring_alert import ProctoringAlert

__all__ = [
    "Base",
    "TimestampMixin",
    "utc_now",
    "User",
    "Role",
    "UserRole",
    "Assessment",
    "Question",
    "ProgrammingLanguage",
    "TestCase",
    "Submission",
    "AssessmentCandidate",
    "AssessmentAttempt",
    "CodeDraft",
    "SubmissionTestCaseResult",
    "SubmissionEvaluation",
    "StudentTopicMastery",
    "TopicMasteryHistory",
    "ProctoringSession",
    "ProctoringEvent",
    "ProctoringAlert",
]
