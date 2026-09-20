import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr
from backend.app.models.invitation import InvitationStatus
from backend.app.models.project import ProjectRole


class InvitationCreate(BaseModel):
    email: EmailStr
    role: ProjectRole = ProjectRole.DEVELOPER


class InvitationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    email: str
    inviter_id: uuid.UUID
    role: ProjectRole
    token: str
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True
