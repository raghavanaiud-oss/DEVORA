import enum
from typing import Dict, Set
from fastapi import HTTPException, status
from backend.app.models.project import ProjectRole


class Permission(str, enum.Enum):
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    MEMBER_INVITE = "member:invite"
    MEMBER_MANAGE = "member:manage"
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"
    CODE_EXECUTE = "code:execute"
    AI_REQUEST = "ai:request"
    AI_REVIEW_MANAGE = "ai:review_manage"


# Role-Based Permission Matrix
ROLE_PERMISSIONS: Dict[ProjectRole, Set[Permission]] = {
    ProjectRole.OWNER: {
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.MEMBER_INVITE,
        Permission.MEMBER_MANAGE,
        Permission.FILE_READ,
        Permission.FILE_WRITE,
        Permission.FILE_DELETE,
        Permission.CODE_EXECUTE,
        Permission.AI_REQUEST,
        Permission.AI_REVIEW_MANAGE,
    },
    ProjectRole.ADMIN: {
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.MEMBER_INVITE,
        Permission.MEMBER_MANAGE,
        Permission.FILE_READ,
        Permission.FILE_WRITE,
        Permission.FILE_DELETE,
        Permission.CODE_EXECUTE,
        Permission.AI_REQUEST,
        Permission.AI_REVIEW_MANAGE,
    },
    ProjectRole.DEVELOPER: {
        Permission.PROJECT_READ,
        Permission.FILE_READ,
        Permission.FILE_WRITE,
        Permission.FILE_DELETE,
        Permission.CODE_EXECUTE,
        Permission.AI_REQUEST,
        Permission.AI_REVIEW_MANAGE,
    },
    ProjectRole.VIEWER: {
        Permission.PROJECT_READ,
        Permission.FILE_READ,
        Permission.AI_REQUEST,
    },
}


def check_permission(user_role: ProjectRole, required_permission: Permission) -> bool:
    role_perms = ROLE_PERMISSIONS.get(user_role, set())
    return required_permission in role_perms


def enforce_permission(user_role: ProjectRole, required_permission: Permission) -> None:
    if not check_permission(user_role, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": f"Role '{user_role.value}' does not have permission '{required_permission.value}'."
                }
            }
        )
