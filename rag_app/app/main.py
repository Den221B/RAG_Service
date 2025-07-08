from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import router as api_router
from logger import setup_logger
from config import settings

import logging

setup_logger()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Agent",
    version="1.0.0",
    description="Answer generation microservice using retrieval + LLM",
)

app.include_router(api_router, prefix="/api")
app.mount("/files", StaticFiles(directory=settings.documents_dir), name="documents")

# Enable CORS (for development use only, restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to allowed domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Log service startup.
    """
    logger.info("🚀 RAG Agent started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Log service shutdown.
    """
    logger.info("🛑 RAG Agent stopped")
