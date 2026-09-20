import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, require_project_permission
from app.models.user import User
from app.schemas.file import (
    FileCreate,
    FileMove,
    FileRename,
    FileResponse,
    FileTreeItem,
    FileUpdate,
    FileVersionResponse,
)
from app.security.rbac import Permission
from app.services.file_service import FileService

router = APIRouter()


@router.get(
    "/{project_id}/files/tree",
    response_model=List[FileTreeItem],
    summary="Get hierarchical workspace file tree",
    dependencies=[Depends(require_project_permission(Permission.FILE_READ))],
)
async def get_file_tree(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[FileTreeItem]:
    file_service = FileService(db)
    return await file_service.get_file_tree(project_id)


@router.get(
    "/{project_id}/files/by-path",
    response_model=FileResponse,
    summary="Get workspace file by its path",
    dependencies=[Depends(require_project_permission(Permission.FILE_READ))],
)
async def get_file_by_path(
    project_id: uuid.UUID,
    path: str = Query(..., description="File path, e.g. /main.py"),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    file_service = FileService(db)
    return await file_service.get_file_by_path(project_id, path)


@router.get(
    "/{project_id}/files/{file_id}",
    response_model=FileResponse,
    summary="Get file details and content by ID",
    dependencies=[Depends(require_project_permission(Permission.FILE_READ))],
)
async def get_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    file_service = FileService(db)
    return await file_service.get_file(project_id, file_id)


@router.post(
    "/{project_id}/files",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace file or directory",
    dependencies=[Depends(require_project_permission(Permission.FILE_WRITE))],
)
async def create_file(
    project_id: uuid.UUID,
    file_in: FileCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    file_service = FileService(db)
    return await file_service.create_file(project_id, current_user.id, file_in)


@router.put(
    "/{project_id}/files/{file_id}",
    response_model=FileResponse,
    summary="Update file content (creates version snapshot)",
    dependencies=[Depends(require_project_permission(Permission.FILE_WRITE))],
)
async def update_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    file_update: FileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    file_service = FileService(db)
    return await file_service.update_file(project_id, file_id, current_user.id, file_update)


@router.post(
    "/{project_id}/files/{file_id}/rename",
    response_model=FileResponse,
    summary="Rename a workspace file or directory",
    dependencies=[Depends(require_project_permission(Permission.FILE_WRITE))],
)
async def rename_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    req: FileRename,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    file_service = FileService(db)
    return await file_service.rename_file(project_id, file_id, current_user.id, req)


@router.post(
    "/{project_id}/files/{file_id}/move",
    response_model=FileResponse,
    summary="Move a workspace file or directory to a new path",
    dependencies=[Depends(require_project_permission(Permission.FILE_WRITE))],
)
async def move_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    req: FileMove,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    file_service = FileService(db)
    return await file_service.move_file(project_id, file_id, current_user.id, req)


@router.delete(
    "/{project_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace file or directory",
    dependencies=[Depends(require_project_permission(Permission.FILE_DELETE))],
)
async def delete_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    file_service = FileService(db)
    await file_service.delete_file(project_id, file_id, current_user.id)


@router.get(
    "/{project_id}/files/{file_id}/versions",
    response_model=List[FileVersionResponse],
    summary="Get version history for a file",
    dependencies=[Depends(require_project_permission(Permission.FILE_READ))],
)
async def list_file_versions(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[FileVersionResponse]:
    file_service = FileService(db)
    return await file_service.list_versions(project_id, file_id)
