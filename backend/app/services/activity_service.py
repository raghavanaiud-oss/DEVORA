import uuid
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.activity_repo import ActivityRepository
from backend.app.schemas.activity import ActivityResponse, AnalyticsResponse, NotificationResponse


class ActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_repo = ActivityRepository(db)

    async def list_project_activity(
        self, project_id: uuid.UUID, limit: int = 50
    ) -> List[ActivityResponse]:
        events = await self.activity_repo.list_project_activity(project_id, limit=limit)
        return [ActivityResponse.model_validate(e) for e in events]

    async def list_user_notifications(
        self, user_id: uuid.UUID, limit: int = 50
    ) -> List[NotificationResponse]:
        notifications = await self.activity_repo.list_user_notifications(user_id, limit=limit)
        return [NotificationResponse.model_validate(n) for n in notifications]

    async def mark_notification_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> NotificationResponse:
        notification = await self.activity_repo.mark_notification_read(notification_id, user_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "NOTIFICATION_NOT_FOUND", "message": "Notification not found."}},
            )
        return NotificationResponse.model_validate(notification)

    async def get_project_analytics(self, project_id: uuid.UUID) -> AnalyticsResponse:
        analytics = await self.activity_repo.get_project_analytics(project_id)
        return AnalyticsResponse.model_validate(analytics)
