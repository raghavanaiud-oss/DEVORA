from fastapi import APIRouter

from backend.app.api.v1.endpoints import (
    activity,
    ai,
    auth,
    execution,
    files,
    invitations,
    projects,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(files.router, prefix="/projects", tags=["Workspace Files"])
api_router.include_router(execution.router, prefix="/projects", tags=["Code Execution"])
api_router.include_router(ai.router, prefix="/projects", tags=["AI Code Intelligence"])
api_router.include_router(activity.router, prefix="", tags=["Activity & Notifications"])
api_router.include_router(invitations.router, prefix="", tags=["Invitations"])
