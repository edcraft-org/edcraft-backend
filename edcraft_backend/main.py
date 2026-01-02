from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from edcraft_backend.config import settings
from edcraft_backend.database import close_db
from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.routers import (
    assessment_templates,
    assessments,
    folders,
    question_generation,
    question_templates,
    questions,
    users,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    yield
    await close_db()


app = FastAPI(
    title=settings.app_name,
    description="API for EdCraft Backend",
    version=settings.app_version,
    lifespan=lifespan,
)


@app.exception_handler(EdCraftBaseException)
async def edcraft_exception_handler(
    request: Request, exc: EdCraftBaseException
) -> JSONResponse:
    """Handle custom EdCraft exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_type": exc.__class__.__name__},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (prefix and tags are defined in each router file)
app.include_router(question_generation.router)
app.include_router(users.router)
app.include_router(folders.router)
app.include_router(questions.router)
app.include_router(assessments.router)
app.include_router(question_templates.router)
app.include_router(assessment_templates.router)


@app.get("/")
async def index() -> dict[str, str]:
    return {"message": "Edcraft API"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.app_env.value,
        "version": settings.app_version,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level,
    )
