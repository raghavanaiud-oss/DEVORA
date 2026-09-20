import uuid
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.api.deps import get_current_active_user, get_current_user, get_db
from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.models.project import Project, ProjectMember, ProjectRole, ProjectVisibility
from backend.app.models.user import User


@pytest.fixture
def mock_user() -> User:
    user_id = uuid.uuid4()
    return User(
        id=user_id,
        email="developer@codeorbit.io",
        username="devmaster",
        hashed_password="hashed_test_password",
        full_name="Lead Developer",
        is_active=True,
        is_superuser=False,
    )


@pytest.fixture
def mock_project(mock_user: User) -> Project:
    proj_id = uuid.uuid4()
    project = Project(
        id=proj_id,
        name="Orbit Engine",
        slug="orbit-engine",
        description="High-performance collaborative runtime engine",
        owner_id=mock_user.id,
        visibility=ProjectVisibility.PRIVATE,
    )
    member = ProjectMember(
        project_id=proj_id,
        user_id=mock_user.id,
        role=ProjectRole.OWNER,
    )
    project.members = [member]
    return project


@pytest_asyncio.fixture
async def async_client(mock_user: User) -> AsyncGenerator[AsyncClient, None]:
    # Dependency overrides for testing without live DB / external services
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
