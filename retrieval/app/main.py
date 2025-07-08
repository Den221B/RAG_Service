from fastapi import FastAPI
from logger import setup_logger
from api import router
import logging
from config import settings

setup_logger()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.service_name,
    version="1.0.0",
    description="Embedding and chunk retrieval service.",
)

app.include_router(router)


@app.on_event("startup")
async def startup():
    logger.info(f"🚀 {settings.service_name} is starting ...")
    from model_wrapper import get_backend
    _ = get_backend()
    logger.info(f"{settings.service_name} is ready.")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info(f"🛑 {settings.service_name} has been stopped.")
