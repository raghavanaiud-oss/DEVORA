import uuid
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field
from app.models.execution import ExecutionStatus


class ExecutionJobCreate(BaseModel):
    entrypoint: str = Field(..., description="File path to execute, e.g. /main.py")
    language: Optional[str] = Field(None, description="python, node, etc. Auto-detected if omitted.")
    stdin: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None


class ExecutionResultResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    stdout: str
    stderr: str
    exit_code: Optional[int]
    duration_ms: float
    memory_kb: int
    cpu_time_ms: float
    created_at: datetime

    class Config:
        from_attributes = True


class ExecutionJobResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    file_id: Optional[uuid.UUID]
    language: str
    entrypoint: str
    status: ExecutionStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[ExecutionResultResponse] = None

    class Config:
        from_attributes = True
