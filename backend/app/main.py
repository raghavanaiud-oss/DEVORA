from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.websocket.router import router as websocket_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("codeorbit")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: attempt to initialize database schema
    logger.info("Starting up CodeOrbit backend engine...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema verified and tables initialized.")
    except Exception as exc:
        logger.warning("Database initialization deferred (database might not be running locally): %s", exc)

    yield

    # Shutdown: dispose of database engine pools
    logger.info("Shutting down CodeOrbit backend engine...")
    try:
        await engine.dispose()
    except Exception as exc:
        logger.warning("Error disposing database engine: %s", exc)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Real-Time Collaborative Software Development Platform API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        error_payload = detail
    else:
        error_payload = {
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(detail),
            }
        }
    return JSONResponse(status_code=exc.status_code, content=error_payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        field = " -> ".join([str(loc) for loc in err.get("loc", [])])
        errors.append({"field": field, "message": err.get("msg", "Validation error")})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The submitted payload failed validation constraints.",
                "details": errors,
            }
        },
    )


# Mount API routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(websocket_router)


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} Collaborative Development API",
        "docs_url": f"{settings.API_V1_STR}/docs",
        "version": "1.0.0",
    }
