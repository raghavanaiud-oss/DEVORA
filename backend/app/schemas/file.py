from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FileCreate(BaseModel):
    path: str = Field(..., description="Absolute path in workspace, e.g. /src/main.py")
    is_directory: bool = False
    content: Optional[str] = ""
    language: Optional[str] = None


class FileUpdate(BaseModel):
    content: str
    change_summary: Optional[str] = None


class FileRename(BaseModel):
    new_name: str = Field(..., min_length=1)


class FileMove(BaseModel):
    new_path: str = Field(..., min_length=1)


class FileVersionResponse(BaseModel):
    id: uuid.UUID
    file_id: uuid.UUID
    version_number: int
    content: Optional[str] = None
    content_hash: str
    change_summary: Optional[str] = None
    created_at: datetime
    created_by_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class FileResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    path: str
    name: str
    is_directory: bool
    content: Optional[str] = None
    size_bytes: int
    language: str
    content_hash: Optional[str] = None
    parent_path: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileTreeItem(BaseModel):
    id: uuid.UUID
    path: str
    name: str
    is_directory: bool
    language: str
    size_bytes: int
    children: List[FileTreeItem] = []

    class Config:
        from_attributes = True


FileTreeItem.model_rebuild()
