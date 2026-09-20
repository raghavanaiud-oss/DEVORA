import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.models.activity import ActivityEvent, ActivityType, Notification
from backend.app.models.ai import AIReview, AIReviewItem
from backend.app.models.execution import ExecutionJob, ExecutionResult, ExecutionStatus
from backend.app.models.workspace_file import FileVersion, WorkspaceFile


class ActivityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_event(self, event: ActivityEvent) -> ActivityEvent:
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def list_project_activity(self, project_id: uuid.UUID, limit: int = 50) -> List[ActivityEvent]:
        result = await self.db.execute(
            select(ActivityEvent)
            .options(selectinload(ActivityEvent.user))
            .where(ActivityEvent.project_id == project_id)
            .order_by(ActivityEvent.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def create_notification(self, notification: Notification) -> Notification:
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    async def list_user_notifications(self, user_id: uuid.UUID, limit: int = 50) -> List[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_notification_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Notification]:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        notification = result.scalars().first()
        if notification:
            notification.is_read = True
            await self.db.flush()
            await self.db.refresh(notification)
        return notification

    async def get_project_analytics(self, project_id: uuid.UUID) -> Dict[str, Any]:
        # Active developers
        dev_count_stmt = (
            select(func.count(distinct(ActivityEvent.user_id)))
            .where(ActivityEvent.project_id == project_id)
        )
        active_developers = (await self.db.execute(dev_count_stmt)).scalar() or 0

        # Files changed count
        files_count_stmt = (
            select(func.count(WorkspaceFile.id))
            .where(WorkspaceFile.project_id == project_id, WorkspaceFile.is_directory == False)
        )
        files_changed = (await self.db.execute(files_count_stmt)).scalar() or 0

        # Total events
        events_count_stmt = (
            select(func.count(ActivityEvent.id))
            .where(ActivityEvent.project_id == project_id)
        )
        total_events = (await self.db.execute(events_count_stmt)).scalar() or 0

        # Executions & success rate
        exec_count_stmt = (
            select(func.count(ExecutionJob.id))
            .where(ExecutionJob.project_id == project_id)
        )
        total_executions = (await self.db.execute(exec_count_stmt)).scalar() or 0

        success_exec_stmt = (
            select(func.count(ExecutionJob.id))
            .where(ExecutionJob.project_id == project_id, ExecutionJob.status == ExecutionStatus.SUCCESS)
        )
        success_executions = (await self.db.execute(success_exec_stmt)).scalar() or 0
        success_rate = (success_executions / total_executions * 100) if total_executions > 0 else 0.0

        # AI Reviews & issues
        reviews_stmt = select(func.count(AIReview.id)).where(AIReview.project_id == project_id)
        total_ai_reviews = (await self.db.execute(reviews_stmt)).scalar() or 0

        issues_stmt = (
            select(func.count(AIReviewItem.id))
            .join(AIReview, AIReviewItem.review_id == AIReview.id)
            .where(AIReview.project_id == project_id)
        )
        total_issues_detected = (await self.db.execute(issues_stmt)).scalar() or 0

        # Most modified files (by FileVersion count)
        most_modified_stmt = (
            select(WorkspaceFile.path, func.count(FileVersion.id).label("version_count"))
            .join(FileVersion, WorkspaceFile.id == FileVersion.file_id)
            .where(WorkspaceFile.project_id == project_id)
            .group_by(WorkspaceFile.path)
            .order_by(func.count(FileVersion.id).desc())
            .limit(5)
        )
        most_modified_rows = (await self.db.execute(most_modified_stmt)).all()
        most_modified_files = [{"path": row[0], "changes": row[1]} for row in most_modified_rows]

        # Languages distribution
        lang_stmt = (
            select(WorkspaceFile.language, func.count(WorkspaceFile.id))
            .where(WorkspaceFile.project_id == project_id, WorkspaceFile.is_directory == False)
            .group_by(WorkspaceFile.language)
        )
        lang_rows = (await self.db.execute(lang_stmt)).all()
        languages_distribution = {row[0]: row[1] for row in lang_rows}

        return {
            "active_developers": max(active_developers, 1),
            "files_changed": files_changed,
            "total_events": total_events,
            "total_executions": total_executions,
            "execution_success_rate": round(success_rate, 1),
            "total_ai_reviews": total_ai_reviews,
            "total_issues_detected": total_issues_detected,
            "most_modified_files": most_modified_files,
            "activity_timeline": [],
            "languages_distribution": languages_distribution,
        }
