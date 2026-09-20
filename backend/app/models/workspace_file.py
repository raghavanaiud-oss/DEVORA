import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class WorkspaceFile(Base):
    __tablename__ = "workspace_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(1000), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    is_directory = Column(Boolean, default=False, nullable=False)
    content = Column(Text, default="", nullable=False)
    size_bytes = Column(Integer, default=0, nullable=False)
    language = Column(String(50), default="plaintext", nullable=False)
    content_hash = Column(String(64), nullable=True)
    parent_path = Column(String(1000), default="/", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="files")
    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan", order_by="desc(FileVersion.version_number)")
    documents = relationship("ProjectDocument", back_populates="file", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "path", name="uq_project_file_path"),
        Index("idx_project_parent_path", "project_id", "parent_path"),
    )


class FileVersion(Base):
    __tablename__ = "file_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey("workspace_files.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_summary = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    file = relationship("WorkspaceFile", back_populates="versions")
    created_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("file_id", "version_number", name="uq_file_version"),
    )
