import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.models.ai import (
    AIRequestType,
    AIReviewCategory,
    AIReviewSeverity,
    AIReviewStatus,
)


class CodeExplainRequest(BaseModel):
    file_path: str
    code_snippet: Optional[str] = None
    question: Optional[str] = None


class CodeReviewCreate(BaseModel):
    file_path: Optional[str] = None


class AIReviewItemResponse(BaseModel):
    id: uuid.UUID
    review_id: uuid.UUID
    file_path: str
    line_number: Optional[int] = None
    severity: AIReviewSeverity
    category: AIReviewCategory
    issue: str
    why_it_matters: Optional[str] = None
    suggested_code: Optional[str] = None
    status: AIReviewStatus
    created_at: datetime

    class Config:
        from_attributes = True


class AIReviewResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    status: AIReviewStatus
    summary: Optional[str] = None
    created_at: datetime
    items: List[AIReviewItemResponse] = []

    class Config:
        from_attributes = True


class ReviewItemActionRequest(BaseModel):
    action: str = Field(..., pattern="^(ACCEPT|REJECT|DISMISS)$")


class TestGenRequest(BaseModel):
    file_path: str
    function_name: Optional[str] = None
    code_snippet: Optional[str] = None


class TestGenResponse(BaseModel):
    test_file_path: str
    generated_code: str
    diff: str
    dependencies: List[str] = []
    explanation: str


class SourceFileReference(BaseModel):
    path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    snippet: Optional[str] = None
    relevance_score: float = 0.0


class AskProjectRequest(BaseModel):
    query: str = Field(..., min_length=2)
    active_file: Optional[str] = None


class AskProjectResponse(BaseModel):
    answer: str
    source_files: List[SourceFileReference] = []
    suggested_actions: List[str] = []
