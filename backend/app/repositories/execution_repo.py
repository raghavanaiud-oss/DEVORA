import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.execution import ExecutionJob, ExecutionResult, ExecutionStatus


class ExecutionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(self, job: ExecutionJob) -> ExecutionJob:
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: uuid.UUID) -> Optional[ExecutionJob]:
        result = await self.db.execute(
            select(ExecutionJob)
            .options(selectinload(ExecutionJob.result))
            .where(ExecutionJob.id == job_id)
        )
        return result.scalars().first()

    async def update_job_status(self, job: ExecutionJob, status: ExecutionStatus) -> ExecutionJob:
        job.status = status
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def create_result(self, result: ExecutionResult) -> ExecutionResult:
        self.db.add(result)
        await self.db.flush()
        await self.db.refresh(result)
        return result

    async def list_by_project(self, project_id: uuid.UUID, limit: int = 50) -> List[ExecutionJob]:
        result = await self.db.execute(
            select(ExecutionJob)
            .options(selectinload(ExecutionJob.result))
            .where(ExecutionJob.project_id == project_id)
            .order_by(ExecutionJob.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
