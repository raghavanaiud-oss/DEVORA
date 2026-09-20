import os
import posixpath
import uuid
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.activity import ActivityEvent, ActivityType
from backend.app.models.workspace_file import WorkspaceFile
from backend.app.repositories.activity_repo import ActivityRepository
from backend.app.repositories.file_repo import FileRepository
from backend.app.schemas.file import (
    FileCreate,
    FileMove,
    FileRename,
    FileResponse,
    FileTreeItem,
    FileUpdate,
    FileVersionResponse,
)

EXTENSION_LANGUAGE_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".java": "java",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".env": "plaintext",
    ".txt": "plaintext",
}


def detect_language(path: str) -> str:
    _, ext = posixpath.splitext(path.lower())
    return EXTENSION_LANGUAGE_MAP.get(ext, "plaintext")


def normalize_path(path: str) -> str:
    normalized = posixpath.normpath(path)
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized


class FileService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.file_repo = FileRepository(db)
        self.activity_repo = ActivityRepository(db)

    async def get_file_tree(self, project_id: uuid.UUID) -> List[FileTreeItem]:
        all_files = await self.file_repo.list_by_project(project_id)
        if not all_files:
            return []

        # Create mapping of path -> FileTreeItem
        items_by_path: Dict[str, FileTreeItem] = {}
        for f in all_files:
            items_by_path[f.path] = FileTreeItem(
                id=f.id,
                path=f.path,
                name=f.name,
                is_directory=f.is_directory,
                language=f.language,
                size_bytes=f.size_bytes,
                children=[],
            )

        root_items: List[FileTreeItem] = []

        # Build hierarchy
        for f in all_files:
            item = items_by_path[f.path]
            parent_path = f.parent_path
            if parent_path == "/" or parent_path not in items_by_path:
                root_items.append(item)
            else:
                items_by_path[parent_path].children.append(item)

        def sort_items(items: List[FileTreeItem]) -> None:
            # Directories first, then alphabetically by name
            items.sort(key=lambda x: (not x.is_directory, x.name.lower()))
            for child in items:
                if child.children:
                    sort_items(child.children)

        sort_items(root_items)
        return root_items

    async def get_file(self, project_id: uuid.UUID, file_id: uuid.UUID) -> FileResponse:
        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "FILE_NOT_FOUND", "message": "File not found in project."}},
            )
        return FileResponse.model_validate(file)

    async def get_file_by_path(self, project_id: uuid.UUID, path: str) -> FileResponse:
        norm_path = normalize_path(path)
        file = await self.file_repo.get_by_path(project_id, norm_path)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "FILE_NOT_FOUND", "message": f"File '{norm_path}' not found."}},
            )
        return FileResponse.model_validate(file)

    async def create_file(
        self, project_id: uuid.UUID, user_id: uuid.UUID, file_in: FileCreate
    ) -> FileResponse:
        norm_path = normalize_path(file_in.path)
        existing = await self.file_repo.get_by_path(project_id, norm_path)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "FILE_ALREADY_EXISTS", "message": f"File at '{norm_path}' already exists."}},
            )

        name = posixpath.basename(norm_path)
        parent_path = posixpath.dirname(norm_path)
        if not parent_path.startswith("/"):
            parent_path = "/" + parent_path

        language = file_in.language or detect_language(norm_path)
        content = file_in.content or ""

        file = WorkspaceFile(
            project_id=project_id,
            path=norm_path,
            name=name,
            is_directory=file_in.is_directory,
            content=content,
            language=language,
            parent_path=parent_path,
        )
        created_file = await self.file_repo.create(file)

        await self.activity_repo.create_event(
            ActivityEvent(
                project_id=project_id,
                user_id=user_id,
                event_type=ActivityType.FILE_CREATED,
                description=f"Created {'directory' if file_in.is_directory else 'file'} {norm_path}",
                event_metadata={"path": norm_path, "is_directory": file_in.is_directory},
            )
        )

        return FileResponse.model_validate(created_file)

    async def update_file(
        self, project_id: uuid.UUID, file_id: uuid.UUID, user_id: uuid.UUID, file_update: FileUpdate
    ) -> FileResponse:
        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "FILE_NOT_FOUND", "message": "File not found in project."}},
            )

        if file.is_directory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "CANNOT_UPDATE_DIRECTORY", "message": "Cannot update content of a directory."}},
            )

        updated_file = await self.file_repo.update(
            file=file,
            new_content=file_update.content,
            user_id=user_id,
            summary=file_update.change_summary,
        )

        await self.activity_repo.create_event(
            ActivityEvent(
                project_id=project_id,
                user_id=user_id,
                event_type=ActivityType.FILE_UPDATED,
                description=f"Updated file {file.path}",
                event_metadata={"path": file.path, "summary": file_update.change_summary},
            )
        )

        return FileResponse.model_validate(updated_file)

    async def rename_file(
        self, project_id: uuid.UUID, file_id: uuid.UUID, user_id: uuid.UUID, req: FileRename
    ) -> FileResponse:
        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "FILE_NOT_FOUND", "message": "File not found."}},
            )

        new_name = req.new_name.strip("/")
        parent = posixpath.dirname(file.path)
        new_path = posixpath.join(parent, new_name)
        if not new_path.startswith("/"):
            new_path = "/" + new_path

        existing = await self.file_repo.get_by_path(project_id, new_path)
        if existing and existing.id != file.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "PATH_COLLISION", "message": f"Path '{new_path}' already exists."}},
            )

        file.name = new_name
        file.path = new_path
        if not file.is_directory:
            file.language = detect_language(new_path)
        await self.db.flush()
        await self.db.refresh(file)

        return FileResponse.model_validate(file)

    async def move_file(
        self, project_id: uuid.UUID, file_id: uuid.UUID, user_id: uuid.UUID, req: FileMove
    ) -> FileResponse:
        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "FILE_NOT_FOUND", "message": "File not found."}},
            )

        new_path = normalize_path(req.new_path)
        existing = await self.file_repo.get_by_path(project_id, new_path)
        if existing and existing.id != file.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "PATH_COLLISION", "message": f"Path '{new_path}' already exists."}},
            )

        file.path = new_path
        file.name = posixpath.basename(new_path)
        file.parent_path = posixpath.dirname(new_path)
        if not file.parent_path.startswith("/"):
            file.parent_path = "/" + file.parent_path

        if not file.is_directory:
            file.language = detect_language(new_path)

        await self.db.flush()
        await self.db.refresh(file)

        return FileResponse.model_validate(file)

    async def delete_file(
        self, project_id: uuid.UUID, file_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "FILE_NOT_FOUND", "message": "File not found."}},
            )

        deleted_path = file.path
        await self.file_repo.delete(file)

        await self.activity_repo.create_event(
            ActivityEvent(
                project_id=project_id,
                user_id=user_id,
                event_type=ActivityType.FILE_DELETED,
                description=f"Deleted file {deleted_path}",
                event_metadata={"path": deleted_path},
            )
        )

    async def list_versions(
        self, project_id: uuid.UUID, file_id: uuid.UUID
    ) -> List[FileVersionResponse]:
        file = await self.file_repo.get_by_id(file_id)
        if not file or file.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "FILE_NOT_FOUND", "message": "File not found."}},
            )

        versions = await self.file_repo.list_versions(file_id)
        return [FileVersionResponse.model_validate(v) for v in versions]
