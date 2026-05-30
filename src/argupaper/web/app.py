"""FastAPI application factory for the local web workbench."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from argupaper.config import load_config
from argupaper.web.logging import configure_web_logging
from argupaper.web.routes import router

logger = logging.getLogger("argupaper.web")


def create_app() -> FastAPI:
    """Create the ArguPaper local workbench API app."""

    config = load_config(require_pdf_api_key=False)
    log_file = configure_web_logging(config.log.web_path)
    logger.info("Local workbench API logging to %s", log_file)

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
    app.state.web_log_path = config.log.web_path
    return app


app = create_app()
