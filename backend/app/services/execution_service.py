from datetime import datetime, timezone
import uuid
from typing import Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.execution.runner import execution_manager
from backend.app.execution.runtimes import detect_runtime
from backend.app.models.activity import ActivityEvent, ActivityType
from backend.app.models.execution import ExecutionJob, ExecutionResult, ExecutionStatus
from backend.app.repositories.activity_repo import ActivityRepository
from backend.app.repositories.execution_repo import ExecutionRepository
from backend.app.repositories.file_repo import FileRepository
from backend.app.schemas.execution import ExecutionJobCreate, ExecutionJobResponse


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.execution_repo = ExecutionRepository(db)
        self.file_repo = FileRepository(db)
        self.activity_repo = ActivityRepository(db)

    async def execute_job(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        job_in: ExecutionJobCreate,
    ) -> ExecutionJobResponse:
        # Load all workspace files for this project to create the execution directory structure
        files = await self.file_repo.list_by_project(project_id)
        file_map: Dict[str, str] = {
            f.path: f.content for f in files if not f.is_directory and f.content is not None
        }

        # Resolve entrypoint and language
        entrypoint = job_in.entrypoint
        if not entrypoint.startswith("/"):
            entrypoint = "/" + entrypoint

        # Verify entrypoint file exists in workspace
        target_file = await self.file_repo.get_by_path(project_id, entrypoint)
        file_id = target_file.id if target_file else None

        runtime = detect_runtime(entrypoint, job_in.language)
        language = runtime.language

        # Create execution job
        job = ExecutionJob(
            project_id=project_id,
            user_id=user_id,
            file_id=file_id,
            language=language,
            entrypoint=entrypoint,
            status=ExecutionStatus.RUNNING,
            started_at=utc_now(),
        )
        job = await self.execution_repo.create_job(job)

        await self.activity_repo.create_event(
            ActivityEvent(
                project_id=project_id,
                user_id=user_id,
                event_type=ActivityType.EXECUTION_STARTED,
                description=f"Started execution of {entrypoint} ({language})",
                event_metadata={"job_id": str(job.id), "entrypoint": entrypoint, "language": language},
            )
        )

        # Run code via execution manager sandbox
        result_data = await execution_manager.run_code(
            files=file_map,
            entrypoint=entrypoint,
            language=language,
            stdin=job_in.stdin,
            env_vars=job_in.env_vars,
        )

        job.status = result_data.status
        job.completed_at = utc_now()
        await self.db.flush()

        # Record execution result
        exec_result = ExecutionResult(
            job_id=job.id,
            stdout=result_data.stdout,
            stderr=result_data.stderr,
            exit_code=result_data.exit_code,
            duration_ms=result_data.duration_ms,
            memory_kb=result_data.memory_kb,
            cpu_time_ms=result_data.cpu_time_ms,
        )
        await self.execution_repo.create_result(exec_result)

        await self.activity_repo.create_event(
            ActivityEvent(
                project_id=project_id,
                user_id=user_id,
                event_type=ActivityType.EXECUTION_COMPLETED,
                description=f"Execution of {entrypoint} finished with status {result_data.status.value}",
                event_metadata={
                    "job_id": str(job.id),
                    "status": result_data.status.value,
                    "exit_code": result_data.exit_code,
                    "duration_ms": result_data.duration_ms,
                },
            )
        )

        full_job = await self.execution_repo.get_job(job.id)
        return ExecutionJobResponse.model_validate(full_job)

    async def get_job(self, project_id: uuid.UUID, job_id: uuid.UUID) -> ExecutionJobResponse:
        job = await self.execution_repo.get_job(job_id)
        if not job or job.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "JOB_NOT_FOUND", "message": "Execution job not found."}},
            )
        return ExecutionJobResponse.model_validate(job)

    async def list_jobs(self, project_id: uuid.UUID, limit: int = 50) -> List[ExecutionJobResponse]:
        jobs = await self.execution_repo.list_by_project(project_id, limit=limit)
        return [ExecutionJobResponse.model_validate(j) for j in jobs]
