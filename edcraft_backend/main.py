from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from edcraft_backend.exceptions import EdCraftBaseException
from edcraft_backend.routers import question_generation

app = FastAPI(
    title="EdCraft Backend API", description="API for EdCraft Backend", version="0.1.0"
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
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(question_generation.router)


@app.get("/")
async def index() -> dict[str, str]:
    return {"message": "Edcraft API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
