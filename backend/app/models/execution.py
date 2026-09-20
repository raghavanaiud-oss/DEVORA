import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ExecutionStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class ExecutionJob(Base):
    __tablename__ = "execution_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey("workspace_files.id", ondelete="SET NULL"), nullable=True)
    language = Column(String(50), nullable=False)
    entrypoint = Column(String(500), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.QUEUED, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="execution_jobs")
    user = relationship("User", back_populates="execution_jobs")
    result = relationship("ExecutionResult", back_populates="job", uselist=False, cascade="all, delete-orphan")


class ExecutionResult(Base):
    __tablename__ = "execution_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("execution_jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    stdout = Column(Text, default="", nullable=False)
    stderr = Column(Text, default="", nullable=False)
    exit_code = Column(Integer, nullable=True)
    duration_ms = Column(Float, default=0.0, nullable=False)
    memory_kb = Column(Integer, default=0, nullable=False)
    cpu_time_ms = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    job = relationship("ExecutionJob", back_populates="result")
