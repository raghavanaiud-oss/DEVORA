import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, require_project_permission
from app.models.user import User
from app.schemas.invitation import InvitationCreate, InvitationResponse
from app.security.rbac import Permission
from app.services.invitation_service import InvitationService

router = APIRouter()


@router.post(
    "/{project_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and send a project invitation",
    dependencies=[Depends(require_project_permission(Permission.MEMBER_INVITE))],
)
async def create_invitation(
    project_id: uuid.UUID,
    req: InvitationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationResponse:
    invitation_service = InvitationService(db)
    return await invitation_service.create_invitation(project_id, current_user.id, req)


@router.get(
    "/{project_id}/invitations",
    response_model=List[InvitationResponse],
    summary="List pending invitations for a project",
    dependencies=[Depends(require_project_permission(Permission.MEMBER_INVITE))],
)
async def list_project_invitations(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[InvitationResponse]:
    invitation_service = InvitationService(db)
    return await invitation_service.list_project_invitations(project_id, current_user.id)


@router.post(
    "/invitations/{token}/accept",
    response_model=InvitationResponse,
    summary="Accept a project invitation",
)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationResponse:
    invitation_service = InvitationService(db)
    return await invitation_service.accept_invitation(token, current_user.id)


@router.post(
    "/invitations/{token}/decline",
    response_model=InvitationResponse,
    summary="Decline a project invitation",
)
async def decline_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> InvitationResponse:
    invitation_service = InvitationService(db)
    return await invitation_service.decline_invitation(token)
