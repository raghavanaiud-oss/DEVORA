# DEVORA - Real-Time Collaborative Development Platform

DEVORA (CodeOrbit Engine) is an AI-first, real-time collaborative software development platform backend built with FastAPI, SQLAlchemy, Redis Pub/Sub, and Yjs CRDT protocol.

---

## Key Features

- **Multi-Tenant Project Workspaces**: Role-based access control (Owner, Admin, Developer, Viewer) with granular permissions.
- **Hierarchical Workspace File System**: Fast tree building, content hashing (SHA-256), automatic language detection, and file version history.
- **Sandboxed Code Execution Engine**: Multi-language execution (Python, Node.js, TypeScript, Go, Rust, C++) with CPU/memory limits, stdout/stderr streaming, and execution history.
- **Real-Time Collaboration**: Dual-mode WebSocket at `/ws/projects/{project_id}` supporting binary Yjs CRDT delta synchronization and live developer presence (cursor positions, file selections, active editor tabs).
- **AI-Powered Code Intelligence**:
  - **Explain Code**: Architectural and logic breakdown of code snippets.
  - **Automated Code Review**: Multi-category scanning (Security, Bugs, Performance, Maintainability) with actionable patches.
  - **Automated Test Generation**: Generates comprehensive unit tests with mocks and boundary tests.
  - **Ask CodeOrbit (RAG)**: Project-scoped semantic search using pgvector embeddings.
- **Activity & Notifications**: Real-time event auditing, developer activity streams, and in-app notifications.

---

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **ORM & Database**: SQLAlchemy 2.0 (AsyncIO), PostgreSQL + pgvector / SQLite fallback
- **Real-Time & Caching**: Redis Pub/Sub, WebSockets, Yjs CRDT protocol
- **Execution Sandboxing**: Process / Docker execution adapters
- **Authentication**: JWT access & refresh tokens, Passlib bcrypt
- **Testing**: Pytest, Pytest-AsyncIO, HTTPX

---

## Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── ai/               # AI engine, providers, RAG, reviews, test gen
│   │   ├── api/              # FastAPI routers, dependencies (deps.py), v1 endpoints
│   │   │   └── v1/endpoints/ # auth, projects, files, execution, ai, activity, invitations
│   │   ├── core/             # config, database, redis, security
│   │   ├── execution/        # sandbox runners, adapters (docker, process), runtimes
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── repositories/     # Data access layer
│   │   ├── schemas/          # Pydantic v2 validation schemas
│   │   ├── security/         # RBAC matrix, rate limiters
│   │   ├── services/         # Business logic layer
│   │   ├── websocket/        # Connection manager, presence, Yjs protocol
│   │   └── main.py           # FastAPI entrypoint, CORS, lifespan
│   ├── tests/                # Pytest automated test suite
│   └── requirements.txt      # Python dependencies
├── .gitignore
└── README.md
```

---

## Getting Started

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the project root:
```env
PROJECT_NAME=DEVORA
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=your-secure-secret-key-here
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/devora
REDIS_URL=redis://localhost:6379/0
```

### 3. Run the Development Server
```bash
uvicorn backend.app.main:app --reload --port 8000
```

- **Interactive API Documentation (Swagger)**: `http://localhost:8000/api/v1/docs`
- **ReDoc Documentation**: `http://localhost:8000/api/v1/redoc`
- **Health Check**: `http://localhost:8000/health`
- **WebSocket Endpoint**: `ws://localhost:8000/ws/projects/{project_id}`

---

## Running Tests

```bash
pytest backend/tests -v
```
