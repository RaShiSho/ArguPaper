"""FastAPI application factory for the local web workbench."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from argupaper.web.routes import router


def create_app() -> FastAPI:
    """Create the ArguPaper local workbench API app."""

    app = FastAPI(
        title="ArguPaper Local Workbench API",
        version="0.1.0",
        description="Local HTTP API for the ArguPaper React workbench.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
