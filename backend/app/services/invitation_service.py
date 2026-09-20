from datetime import datetime, timedelta, timezone
import secrets
import uuid
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.activity import ActivityEvent, ActivityType, Notification, NotificationType
from backend.app.models.invitation import Invitation, InvitationStatus
from backend.app.models.project import ProjectRole
from backend.app.repositories.activity_repo import ActivityRepository
from backend.app.repositories.project_repo import ProjectRepository
from backend.app.repositories.user_repo import UserRepository
from backend.app.schemas.invitation import InvitationCreate, InvitationResponse
from backend.app.security.rbac import Permission, enforce_permission


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InvitationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.user_repo = UserRepository(db)
        self.activity_repo = ActivityRepository(db)

    async def create_invitation(
        self, project_id: uuid.UUID, inviter_id: uuid.UUID, req: InvitationCreate
    ) -> InvitationResponse:
        member = await self.project_repo.get_member(project_id, inviter_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        enforce_permission(member.role, Permission.MEMBER_INVITE)

        # Check if user with email exists and is already member
        target_user = await self.user_repo.get_by_email(req.email)
        if target_user:
            existing_member = await self.project_repo.get_member(project_id, target_user.id)
            if existing_member:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": {"code": "ALREADY_MEMBER", "message": "User is already a project member."}},
                )

        token = secrets.token_urlsafe(32)
        invitation = Invitation(
            project_id=project_id,
            inviter_id=inviter_id,
            email=req.email,
            role=req.role,
            token=token,
            status=InvitationStatus.PENDING,
            expires_at=utc_now() + timedelta(days=7),
        )
        invitation = await self.project_repo.create_invitation(invitation)

        # If user exists, create an in-app notification
        if target_user:
            project = await self.project_repo.get_by_id(project_id)
            project_name = project.name if project else "a project"
            await self.activity_repo.create_notification(
                Notification(
                    user_id=target_user.id,
                    project_id=project_id,
                    notification_type=NotificationType.INVITATION,
                    title="Project Invitation",
                    message=f"You have been invited to join {project_name} as {req.role.value}.",
                    notification_metadata={"invitation_token": token, "project_id": str(project_id)},
                )
            )

        return InvitationResponse.model_validate(invitation)

    async def list_project_invitations(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[InvitationResponse]:
        member = await self.project_repo.get_member(project_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        stmt = (
            select(Invitation)
            .where(Invitation.project_id == project_id)
            .order_by(Invitation.created_at.desc())
        )
        result = await self.db.execute(stmt)
        invitations = result.scalars().all()
        return [InvitationResponse.model_validate(inv) for inv in invitations]

    async def accept_invitation(self, token: str, user_id: uuid.UUID) -> InvitationResponse:
        invitation = await self.project_repo.get_invitation_by_token(token)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "INVALID_INVITATION", "message": "Invitation not found or already used."}},
            )

        if invitation.expires_at < utc_now():
            invitation.status = InvitationStatus.EXPIRED
            await self.db.flush()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "INVITATION_EXPIRED", "message": "This invitation has expired."}},
            )

        # Add user as member
        existing_member = await self.project_repo.get_member(invitation.project_id, user_id)
        if not existing_member:
            await self.project_repo.add_member(invitation.project_id, user_id, invitation.role)

        invitation.status = InvitationStatus.ACCEPTED
        await self.db.flush()

        user = await self.user_repo.get_by_id(user_id)
        username = user.username if user else "A user"
        await self.activity_repo.create_event(
            ActivityEvent(
                project_id=invitation.project_id,
                user_id=user_id,
                event_type=ActivityType.MEMBER_ADDED,
                description=f"{username} accepted invitation as {invitation.role.value}",
            )
        )

        return InvitationResponse.model_validate(invitation)

    async def decline_invitation(self, token: str) -> InvitationResponse:
        invitation = await self.project_repo.get_invitation_by_token(token)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "INVALID_INVITATION", "message": "Invitation not found or expired."}},
            )

        invitation.status = InvitationStatus.REJECTED
        await self.db.flush()
        return InvitationResponse.model_validate(invitation)
