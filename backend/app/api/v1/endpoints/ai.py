import uuid
from typing import Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_active_user, get_db, require_project_permission
from backend.app.models.user import User
from backend.app.schemas.ai import (
    AIReviewItemResponse,
    AIReviewResponse,
    AskProjectRequest,
    AskProjectResponse,
    CodeExplainRequest,
    CodeReviewCreate,
    ReviewItemActionRequest,
    TestGenRequest,
    TestGenResponse,
)
from backend.app.security.rbac import Permission
from backend.app.services.ai_service import AIService

router = APIRouter()


@router.post(
    "/{project_id}/ai/explain",
    response_model=Dict[str, str],
    summary="Generate architecture and logic explanation for a code snippet",
    dependencies=[Depends(require_project_permission(Permission.AI_REQUEST))],
)
async def explain_code(
    project_id: uuid.UUID,
    req: CodeExplainRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    ai_service = AIService(db)
    explanation = await ai_service.explain_code(project_id, current_user.id, req)
    return {"explanation": explanation}


@router.post(
    "/{project_id}/ai/review",
    response_model=AIReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger an automated AI Code Review with inline issues and suggested fixes",
    dependencies=[Depends(require_project_permission(Permission.AI_REQUEST))],
)
async def create_code_review(
    project_id: uuid.UUID,
    req: CodeReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AIReviewResponse:
    ai_service = AIService(db)
    return await ai_service.create_review(project_id, current_user.id, req)


@router.get(
    "/{project_id}/ai/reviews",
    response_model=List[AIReviewResponse],
    summary="List all code reviews for a project",
    dependencies=[Depends(require_project_permission(Permission.AI_REQUEST))],
)
async def list_code_reviews(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[AIReviewResponse]:
    ai_service = AIService(db)
    return await ai_service.list_reviews(project_id)


@router.get(
    "/{project_id}/ai/reviews/{review_id}",
    response_model=AIReviewResponse,
    summary="Get details and items for an AI review",
    dependencies=[Depends(require_project_permission(Permission.AI_REQUEST))],
)
async def get_code_review(
    project_id: uuid.UUID,
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AIReviewResponse:
    ai_service = AIService(db)
    return await ai_service.get_review(project_id, review_id)


@router.post(
    "/{project_id}/ai/reviews/{review_id}/items/{item_id}/action",
    response_model=AIReviewItemResponse,
    summary="Accept, reject, or dismiss a suggested code review fix",
    dependencies=[Depends(require_project_permission(Permission.AI_REVIEW_MANAGE))],
)
async def take_review_item_action(
    project_id: uuid.UUID,
    review_id: uuid.UUID,
    item_id: uuid.UUID,
    req: ReviewItemActionRequest,
    db: AsyncSession = Depends(get_db),
) -> AIReviewItemResponse:
    ai_service = AIService(db)
    return await ai_service.take_review_item_action(project_id, review_id, item_id, req)


@router.post(
    "/{project_id}/ai/tests",
    response_model=TestGenResponse,
    summary="Synthesize unit tests with boundary and error case coverage",
    dependencies=[Depends(require_project_permission(Permission.AI_REQUEST))],
)
async def generate_tests(
    project_id: uuid.UUID,
    req: TestGenRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TestGenResponse:
    ai_service = AIService(db)
    return await ai_service.generate_tests(project_id, current_user.id, req)


@router.post(
    "/{project_id}/ai/ask",
    response_model=AskProjectResponse,
    summary="Ask CodeOrbit RAG query across project documents",
    dependencies=[Depends(require_project_permission(Permission.AI_REQUEST))],
)
async def ask_project(
    project_id: uuid.UUID,
    req: AskProjectRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AskProjectResponse:
    ai_service = AIService(db)
    return await ai_service.ask_project(project_id, current_user.id, req)
