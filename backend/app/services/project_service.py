import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.activity import ActivityEvent, ActivityType
from app.models.invitation import Invitation, InvitationStatus
from app.models.project import Project, ProjectMember, ProjectRole, ProjectVisibility
from app.models.workspace_file import WorkspaceFile
from app.repositories.activity_repo import ActivityRepository
from app.repositories.file_repo import FileRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.schemas.project import (
    AddMemberRequest,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.security.rbac import Permission, enforce_permission


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.user_repo = UserRepository(db)
        self.file_repo = FileRepository(db)
        self.activity_repo = ActivityRepository(db)

    async def create_project(self, user_id: uuid.UUID, project_in: ProjectCreate) -> ProjectResponse:
        slug = project_in.slug
        if not slug:
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", project_in.name.lower()).strip("-")
            # Ensure uniqueness
            existing = await self.project_repo.get_by_slug(slug)
            if existing:
                slug = f"{slug}-{secrets.token_hex(3)}"

        project = Project(
            name=project_in.name,
            slug=slug,
            description=project_in.description,
            owner_id=user_id,
            visibility=project_in.visibility,
        )
        created_project = await self.project_repo.create(project, owner_role=ProjectRole.OWNER)

        # Create starter files: README.md and main.py
        readme_file = WorkspaceFile(
            project_id=created_project.id,
            path="/README.md",
            name="README.md",
            is_directory=False,
            content=f"# {created_project.name}\n\n{created_project.description or 'A collaborative software development workspace.'}\n\n## Getting Started\nRun `main.py` or explore project intelligence via Ask CodeOrbit.",
            language="markdown",
            parent_path="/",
        )
        await self.file_repo.create(readme_file)

        main_file = WorkspaceFile(
            project_id=created_project.id,
            path="/main.py",
            name="main.py",
            is_directory=False,
            content="""# CodeOrbit - Real-Time Collaborative Workspace
import sys

def main():
    print(f"CodeOrbit execution runtime online: Python {sys.version.split()[0]}")
    print("Real-time CRDT synchronization active.")

if __name__ == "__main__":
    main()
""",
            language="python",
            parent_path="/",
        )
        await self.file_repo.create(main_file)

        # Log activity
        await self.activity_repo.create_event(
            ActivityEvent(
                project_id=created_project.id,
                user_id=user_id,
                event_type=ActivityType.PROJECT_CREATED,
                description=f"Created project {created_project.name}",
            )
        )

        resp = ProjectResponse.model_validate(created_project)
        resp.current_user_role = ProjectRole.OWNER
        resp.members_count = 1
        return resp

    async def get_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> ProjectResponse:
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found."}},
            )

        member = await self.project_repo.get_member(project_id, user_id)
        if not member and project.visibility != ProjectVisibility.PUBLIC:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "PROJECT_ACCESS_DENIED", "message": "You do not have access to this project."}},
            )

        resp = ProjectResponse.model_validate(project)
        resp.current_user_role = member.role if member else ProjectRole.VIEWER
        resp.members_count = len(project.members)
        return resp

    async def list_user_projects(self, user_id: uuid.UUID) -> List[ProjectResponse]:
        projects_with_roles = await self.project_repo.list_for_user(user_id)
        responses = []
        for project, role in projects_with_roles:
            resp = ProjectResponse.model_validate(project)
            resp.current_user_role = role
            resp.members_count = len(project.members) if project.members else 1
            responses.append(resp)
        return responses

    async def update_project(
        self, project_id: uuid.UUID, user_id: uuid.UUID, project_update: ProjectUpdate
    ) -> ProjectResponse:
        member = await self.project_repo.get_member(project_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        enforce_permission(member.role, Permission.PROJECT_UPDATE)

        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        if project_update.name is not None:
            project.name = project_update.name
        if project_update.description is not None:
            project.description = project_update.description
        if project_update.visibility is not None:
            project.visibility = project_update.visibility

        updated = await self.project_repo.update(project)
        resp = ProjectResponse.model_validate(updated)
        resp.current_user_role = member.role
        return resp

    async def delete_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        member = await self.project_repo.get_member(project_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        enforce_permission(member.role, Permission.PROJECT_DELETE)

        project = await self.project_repo.get_by_id(project_id)
        if project:
            await self.project_repo.delete(project)

    async def invite_member(
        self, project_id: uuid.UUID, user_id: uuid.UUID, req: AddMemberRequest
    ) -> ProjectMemberResponse:
        member = await self.project_repo.get_member(project_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        enforce_permission(member.role, Permission.MEMBER_INVITE)

        target_user = await self.user_repo.get_by_email(req.email)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "USER_NOT_FOUND", "message": f"No user registered with email {req.email}"}},
            )

        existing_membership = await self.project_repo.get_member(project_id, target_user.id)
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "ALREADY_MEMBER", "message": "User is already a member of this project."}},
            )

        new_member = await self.project_repo.add_member(project_id, target_user.id, req.role)

        await self.activity_repo.create_event(
            ActivityEvent(
                project_id=project_id,
                user_id=user_id,
                event_type=ActivityType.MEMBER_ADDED,
                description=f"Added {target_user.username} as {req.role.value}",
            )
        )

        return ProjectMemberResponse.model_validate(new_member)

    async def list_members(self, project_id: uuid.UUID, user_id: uuid.UUID) -> List[ProjectMemberResponse]:
        member = await self.project_repo.get_member(project_id, user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        members = await self.project_repo.list_members(project_id)
        return [ProjectMemberResponse.model_validate(m) for m in members]
