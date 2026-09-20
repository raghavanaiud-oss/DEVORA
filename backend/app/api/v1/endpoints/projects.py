import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_active_user, get_db
from backend.app.models.user import User
from backend.app.schemas.project import (
    AddMemberRequest,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)
from backend.app.services.project_service import ProjectService

router = APIRouter()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new collaborative project workspace",
)
async def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project_service = ProjectService(db)
    return await project_service.create_project(current_user.id, project_in)


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List all projects accessible to the current user",
)
async def list_user_projects(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    project_service = ProjectService(db)
    return await project_service.list_user_projects(current_user.id)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details and membership role",
)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project_service = ProjectService(db)
    return await project_service.get_project(project_id, current_user.id)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project metadata",
)
async def update_project(
    project_id: uuid.UUID,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project_service = ProjectService(db)
    return await project_service.update_project(project_id, current_user.id, project_update)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project (Owner only)",
)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    project_service = ProjectService(db)
    await project_service.delete_project(project_id, current_user.id)


@router.get(
    "/{project_id}/members",
    response_model=List[ProjectMemberResponse],
    summary="List all project members and roles",
)
async def list_project_members(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectMemberResponse]:
    project_service = ProjectService(db)
    return await project_service.list_members(project_id, current_user.id)


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an existing user as a project member",
)
async def add_project_member(
    project_id: uuid.UUID,
    req: AddMemberRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectMemberResponse:
    project_service = ProjectService(db)
    return await project_service.invite_member(project_id, current_user.id, req)
