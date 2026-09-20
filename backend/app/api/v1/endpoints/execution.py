import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_active_user, get_db, require_project_permission
from backend.app.execution.runtimes import SUPPORTED_RUNTIMES
from backend.app.models.user import User
from backend.app.schemas.execution import (
    ExecutionJobCreate,
    ExecutionJobResponse,
)
from backend.app.security.rbac import Permission
from backend.app.services.execution_service import ExecutionService

router = APIRouter()


@router.get(
    "/runtimes",
    response_model=Dict[str, Any],
    summary="List supported code execution language runtimes",
)
async def list_supported_runtimes() -> Dict[str, Any]:
    return {
        key: {
            "name": cfg.name,
            "extension": cfg.extension,
            "default_entrypoint": cfg.default_entrypoint,
        }
        for key, cfg in SUPPORTED_RUNTIMES.items()
    }


@router.post(
    "/{project_id}/execute",
    response_model=ExecutionJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch a code execution job in the sandbox",
    dependencies=[Depends(require_project_permission(Permission.CODE_EXECUTE))],
)
async def execute_code(
    project_id: uuid.UUID,
    job_in: ExecutionJobCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ExecutionJobResponse:
    execution_service = ExecutionService(db)
    return await execution_service.execute_job(project_id, current_user.id, job_in)


@router.get(
    "/{project_id}/executions",
    response_model=List[ExecutionJobResponse],
    summary="List execution history for a project",
    dependencies=[Depends(require_project_permission(Permission.PROJECT_READ))],
)
async def list_executions(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[ExecutionJobResponse]:
    execution_service = ExecutionService(db)
    return await execution_service.list_jobs(project_id, limit=limit)


@router.get(
    "/{project_id}/executions/{job_id}",
    response_model=ExecutionJobResponse,
    summary="Get execution job status and stdout/stderr output",
    dependencies=[Depends(require_project_permission(Permission.PROJECT_READ))],
)
async def get_execution(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ExecutionJobResponse:
    execution_service = ExecutionService(db)
    return await execution_service.get_job(project_id, job_id)
