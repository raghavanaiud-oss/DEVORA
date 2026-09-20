import hashlib
import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.workspace_file import FileVersion, WorkspaceFile


class FileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, file_id: uuid.UUID) -> Optional[WorkspaceFile]:
        result = await self.db.execute(select(WorkspaceFile).where(WorkspaceFile.id == file_id))
        return result.scalars().first()

    async def get_by_path(self, project_id: uuid.UUID, path: str) -> Optional[WorkspaceFile]:
        result = await self.db.execute(
            select(WorkspaceFile).where(WorkspaceFile.project_id == project_id, WorkspaceFile.path == path)
        )
        return result.scalars().first()

    async def list_by_project(self, project_id: uuid.UUID) -> List[WorkspaceFile]:
        result = await self.db.execute(
            select(WorkspaceFile)
            .where(WorkspaceFile.project_id == project_id)
            .order_by(WorkspaceFile.is_directory.desc(), WorkspaceFile.path.asc())
        )
        return result.scalars().all()

    async def create(self, file: WorkspaceFile) -> WorkspaceFile:
        if file.content is not None and not file.content_hash:
            file.content_hash = hashlib.sha256(file.content.encode("utf-8")).hexdigest()
            file.size_bytes = len(file.content.encode("utf-8"))
        self.db.add(file)
        await self.db.flush()
        await self.db.refresh(file)
        return file

    async def update(self, file: WorkspaceFile, new_content: str, user_id: Optional[uuid.UUID] = None, summary: Optional[str] = None) -> WorkspaceFile:
        old_content = file.content
        file.content = new_content
        file.content_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
        file.size_bytes = len(new_content.encode("utf-8"))
        await self.db.flush()

        # Create FileVersion entry
        version_count_stmt = select(func.count(FileVersion.id)).where(FileVersion.file_id == file.id)
        version_count = (await self.db.execute(version_count_stmt)).scalar() or 0

        version = FileVersion(
            file_id=file.id,
            version_number=version_count + 1,
            content=new_content,
            content_hash=file.content_hash,
            created_by_id=user_id,
            change_summary=summary or f"Version {version_count + 1}"
        )
        self.db.add(version)
        await self.db.flush()
        await self.db.refresh(file)
        return file

    async def delete(self, file: WorkspaceFile) -> None:
        await self.db.delete(file)
        await self.db.flush()

    async def list_versions(self, file_id: uuid.UUID) -> List[FileVersion]:
        result = await self.db.execute(
            select(FileVersion).where(FileVersion.file_id == file_id).order_by(FileVersion.version_number.desc())
        )
        return result.scalars().all()
