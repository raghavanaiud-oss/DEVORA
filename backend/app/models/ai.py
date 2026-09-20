import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

try:
    from pgvector.sqlalchemy import Vector
    EMBEDDING_TYPE = Vector(384)
except ImportError:
    from sqlalchemy import JSON
    EMBEDDING_TYPE = JSON


def utc_now():
    return datetime.now(timezone.utc)


class AIRequestType(str, enum.Enum):
    EXPLAIN = "EXPLAIN"
    REVIEW = "REVIEW"
    FIND_BUGS = "FIND_BUGS"
    GENERATE_TESTS = "GENERATE_TESTS"
    IMPROVE = "IMPROVE"
    GENERATE_DOCS = "GENERATE_DOCS"
    ASK_PROJECT = "ASK_PROJECT"


class AIReviewSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AIReviewCategory(str, enum.Enum):
    BUG = "BUG"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    MAINTAINABILITY = "MAINTAINABILITY"
    STYLE = "STYLE"
    TESTING = "TESTING"


class AIReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DISMISSED = "DISMISSED"


class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey("workspace_files.id", ondelete="CASCADE"), nullable=True, index=True)
    path = Column(String(1000), nullable=False)
    language = Column(String(50), default="plaintext", nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    doc_type = Column(String(50), default="CODE", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    project = relationship("Project", back_populates="documents")
    file = relationship("WorkspaceFile", back_populates="documents")
    embeddings = relationship("Embedding", back_populates="document", cascade="all, delete-orphan")


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("project_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_content = Column(Text, nullable=False)
    embedding = Column(EMBEDDING_TYPE, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    document = relationship("ProjectDocument", back_populates="embeddings")

    __table_args__ = (
        Index("idx_embedding_project_doc", "project_id", "document_id"),
    )


class AIRequest(Base):
    __tablename__ = "ai_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    request_type = Column(Enum(AIRequestType), nullable=False)
    prompt = Column(Text, nullable=False)
    context_files = Column(JSONB, default=list, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)
    response_text = Column(Text, nullable=True)
    response_metadata = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="ai_requests")
    user = relationship("User")


class AIReview(Base):
    __tablename__ = "ai_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    status = Column(Enum(AIReviewStatus), default=AIReviewStatus.PENDING, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    project = relationship("Project", back_populates="ai_reviews")
    user = relationship("User")
    items = relationship("AIReviewItem", back_populates="review", cascade="all, delete-orphan")


class AIReviewItem(Base):
    __tablename__ = "ai_review_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    review_id = Column(UUID(as_uuid=True), ForeignKey("ai_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(1000), nullable=False)
    line_number = Column(Integer, nullable=True)
    severity = Column(Enum(AIReviewSeverity), default=AIReviewSeverity.MEDIUM, nullable=False)
    category = Column(Enum(AIReviewCategory), default=AIReviewCategory.BUG, nullable=False)
    issue = Column(Text, nullable=False)
    why_it_matters = Column(Text, nullable=True)
    suggested_code = Column(Text, nullable=True)
    status = Column(Enum(AIReviewStatus), default=AIReviewStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    review = relationship("AIReview", back_populates="items")
