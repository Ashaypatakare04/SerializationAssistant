from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.db.session import init_db
from backend.app.workers.job_runner import job_runner

# Import routers
from backend.app.api.v1.projects import router as projects_router
from backend.app.api.v1.documents import router as documents_router
from backend.app.api.v1.references import router as references_router
from backend.app.api.v1.analysis import router as analysis_router
from backend.app.api.v1.style import router as style_router
from backend.app.api.v1.planning import router as planning_router
from backend.app.api.v1.storyboard import router as storyboard_router
from backend.app.api.v1.generation import router as generation_router
from backend.app.api.v1.approvals import router as approvals_router
from backend.app.api.v1.jobs import router as jobs_router
from backend.app.api.v1.qa import router as qa_router
from backend.app.api.v1.export import router as export_router
from backend.app.api.v1.assets import router as assets_router
from backend.app.api.v1.capabilities import router as capabilities_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Initializing database tables and storage...")
    await init_db()
    logger.info("Recovering orphaned jobs from previous run...")
    await job_runner.recover_orphaned_jobs()
    logger.info("AI Novel-to-Webtoon Studio Backend Ready.")
    yield
    logger.info("Shutting down backend studio...")

app = FastAPI(
    title=settings.APP_NAME,
    description="Creator-controlled studio transforming novel manuscripts into vertical scrolling webtoons.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1 routers
v1_prefix = settings.API_V1_PREFIX
app.include_router(projects_router, prefix=v1_prefix)
app.include_router(documents_router, prefix=v1_prefix)
app.include_router(references_router, prefix=v1_prefix)
app.include_router(analysis_router, prefix=v1_prefix)
app.include_router(style_router, prefix=v1_prefix)
app.include_router(planning_router, prefix=v1_prefix)
app.include_router(storyboard_router, prefix=v1_prefix)
app.include_router(generation_router, prefix=v1_prefix)
app.include_router(approvals_router, prefix=v1_prefix)
app.include_router(jobs_router, prefix=v1_prefix)
app.include_router(qa_router, prefix=v1_prefix)
app.include_router(export_router, prefix=v1_prefix)
app.include_router(assets_router, prefix=v1_prefix)
app.include_router(capabilities_router, prefix=v1_prefix)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER,
        "image_provider": settings.IMAGE_PROVIDER
    }
