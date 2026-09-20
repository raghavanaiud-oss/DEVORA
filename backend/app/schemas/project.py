import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.models.project import ProjectRole, ProjectVisibility
from backend.app.schemas.user import UserResponse


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    visibility: ProjectVisibility = ProjectVisibility.PRIVATE


class ProjectCreate(ProjectBase):
    slug: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    visibility: Optional[ProjectVisibility] = None


class ProjectMemberResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    role: ProjectRole
    joined_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class ProjectResponse(ProjectBase):
    id: uuid.UUID
    slug: str
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    members_count: Optional[int] = 0
    current_user_role: Optional[ProjectRole] = None

    class Config:
        from_attributes = True


class AddMemberRequest(BaseModel):
    email: str
    role: ProjectRole = ProjectRole.DEVELOPER


class UpdateMemberRoleRequest(BaseModel):
    role: ProjectRole
