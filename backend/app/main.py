from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    adaptive,
    analytics,
    assessments,
    auth,
    health,
    internal_judge0,
    proctoring,
    questions,
    student_assessments,
)
from app.core.config import settings
from app.core.database import dispose_database_engine
from app.core.redis import close_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis_client()
    await dispose_database_engine()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API foundation for the Vedantu Online Coding Assessment Platform.",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include modular API routers
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(questions.router, prefix=settings.API_V1_STR)
app.include_router(assessments.router, prefix=settings.API_V1_STR)
app.include_router(student_assessments.router, prefix=settings.API_V1_STR)
app.include_router(adaptive.router, prefix=settings.API_V1_STR)
app.include_router(proctoring.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)

# Register internal developer execution route (Development Only)
if settings.ENVIRONMENT == "development" and settings.ENABLE_DEV_JUDGE0_ROUTES:
    app.include_router(internal_judge0.router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health",
    }
