import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from backend.app.models.activity import ActivityType, NotificationType
from backend.app.schemas.user import UserResponse


class ActivityResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    event_type: ActivityType
    description: str
    event_metadata: Dict[str, Any] = {}
    created_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool
    notification_metadata: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    active_developers: int
    files_changed: int
    total_events: int
    total_executions: int
    execution_success_rate: float
    total_ai_reviews: int
    total_issues_detected: int
    most_modified_files: List[Dict[str, Any]] = []
    activity_timeline: List[Dict[str, Any]] = []
    languages_distribution: Dict[str, int] = {}
