import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class RelationshipType(str, enum.Enum):
    IMPORTS = "IMPORTS"
    TESTS = "TESTS"
    DEPENDS_ON = "DEPENDS_ON"
    MODIFIED_BY = "MODIFIED_BY"
    REFERENCED_IN = "REFERENCED_IN"


class ProjectRelationship(Base):
    __tablename__ = "project_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # FILE, TEST, USER
    source_id = Column(String(255), nullable=False, index=True)  # e.g., file path or user id
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(255), nullable=False, index=True)
    relation_type = Column(Enum(RelationshipType), nullable=False, index=True)
    relationship_metadata = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    project = relationship("Project", back_populates="relationships")

    __table_args__ = (
        Index("idx_relationship_source_target", "project_id", "source_id", "target_id"),
    )
