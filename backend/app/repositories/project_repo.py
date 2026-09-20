import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.models.invitation import Invitation, InvitationStatus
from backend.app.models.project import Project, ProjectMember, ProjectRole


class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
            .where(Project.id == project_id)
        )
        return result.scalars().first()

    async def get_by_slug(self, slug: str) -> Optional[Project]:
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
            .where(Project.slug == slug)
        )
        return result.scalars().first()

    async def list_for_user(self, user_id: uuid.UUID) -> List[Tuple[Project, ProjectRole]]:
        """Return all projects owned by or shared with the user, along with their role."""
        stmt = (
            select(Project, ProjectMember.role)
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.updated_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.all()

    async def create(self, project: Project, owner_role: ProjectRole = ProjectRole.OWNER) -> Project:
        self.db.add(project)
        await self.db.flush()
        
        # Add owner as member with OWNER role
        member = ProjectMember(
            project_id=project.id,
            user_id=project.owner_id,
            role=owner_role,
        )
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def update(self, project: Project) -> Project:
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def delete(self, project: Project) -> None:
        await self.db.delete(project)
        await self.db.flush()

    async def get_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ProjectMember]:
        result = await self.db.execute(
            select(ProjectMember)
            .options(selectinload(ProjectMember.user))
            .where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        )
        return result.scalars().first()

    async def list_members(self, project_id: uuid.UUID) -> List[ProjectMember]:
        result = await self.db.execute(
            select(ProjectMember)
            .options(selectinload(ProjectMember.user))
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.joined_at.asc())
        )
        return result.scalars().all()

    async def add_member(self, project_id: uuid.UUID, user_id: uuid.UUID, role: ProjectRole) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member

    async def remove_member(self, member: ProjectMember) -> None:
        await self.db.delete(member)
        await self.db.flush()

    async def create_invitation(self, invitation: Invitation) -> Invitation:
        self.db.add(invitation)
        await self.db.flush()
        await self.db.refresh(invitation)
        return invitation

    async def get_invitation_by_token(self, token: str) -> Optional[Invitation]:
        result = await self.db.execute(
            select(Invitation).where(Invitation.token == token, Invitation.status == InvitationStatus.PENDING)
        )
        return result.scalars().first()
