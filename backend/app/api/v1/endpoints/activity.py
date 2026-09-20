import uuid
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_active_user, get_db, require_project_permission
from backend.app.models.user import User
from backend.app.schemas.activity import ActivityResponse, AnalyticsResponse, NotificationResponse
from backend.app.security.rbac import Permission
from backend.app.services.activity_service import ActivityService

router = APIRouter()


@router.get(
    "/notifications",
    response_model=List[NotificationResponse],
    summary="List notifications for the current authenticated user",
)
async def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[NotificationResponse]:
    activity_service = ActivityService(db)
    return await activity_service.list_user_notifications(current_user.id, limit=limit)


@router.put(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    activity_service = ActivityService(db)
    return await activity_service.mark_notification_read(notification_id, current_user.id)


@router.get(
    "/{project_id}/activity",
    response_model=List[ActivityResponse],
    summary="Get chronological activity events for a project",
    dependencies=[Depends(require_project_permission(Permission.PROJECT_READ))],
)
async def list_project_activity(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[ActivityResponse]:
    activity_service = ActivityService(db)
    return await activity_service.list_project_activity(project_id, limit=limit)


@router.get(
    "/{project_id}/analytics",
    response_model=AnalyticsResponse,
    summary="Get project analytics and metrics",
    dependencies=[Depends(require_project_permission(Permission.PROJECT_READ))],
)
async def get_project_analytics(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    activity_service = ActivityService(db)
    return await activity_service.get_project_analytics(project_id)
