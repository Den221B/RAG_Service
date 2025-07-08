import os
import json
import asyncio
import logging
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pathlib import Path
import redis.asyncio as redis


# ───────────────────── Logging Configuration ─────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("log_collector")


# ───────────────────── App Settings ─────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")
QUEUE_NAME: str = "log_queue"
LOG_DIR: Path = Path("/app/logs")

app = FastAPI(title="Log Collector", description="Receives logs and queues them in Redis")

redis_conn: redis.Redis = None


# ───────────────────── Lifecycle ─────────────────────
@app.on_event("startup")
async def startup() -> None:
    """
    Initialize Redis connection and start periodic queue size logging.
    """
    global redis_conn
    redis_conn = redis.from_url(REDIS_URL)

    async def monitor_queue():
        while True:
            try:
                length = await redis_conn.llen(QUEUE_NAME)
                if length > 0:
                    logger.info(f"[LogCollector] {length} logs in queue")
                await asyncio.sleep(10)
            except Exception as e:
                logger.warning(f"[LogCollector] Queue monitor error: {e}")

    asyncio.create_task(monitor_queue())


# ───────────────────── Routes ─────────────────────
@app.get("/ping")
async def ping() -> Dict[str, Any]:
    """
    Health check endpoint to verify Redis availability.
    """
    try:
        pong = await redis_conn.ping()
        return {"status": "ok", "redis": pong}
    except Exception as e:
        logger.error(f"[Ping] Redis unavailable: {e}")
        return {"status": "error", "redis": False}


@app.post("/collect")
async def collect_logs(request: Request) -> Dict[str, str]:
    """
    Accepts a JSON log from request body and pushes it into Redis queue.
    """
    try:
        data = await request.json()
        await redis_conn.lpush(QUEUE_NAME, json.dumps(data, ensure_ascii=False))
        return {"status": "queued"}
    except Exception as e:
        logger.error(f"[Collect] Failed to process incoming log: {e}")
        return {"status": "error"}


@app.get("/logs")
async def get_aggregated_logs() -> JSONResponse:
    """
    Aggregates all log_*.json files in the logs folder and deletes them after reading.
    """
    logger.info("[LogCollector] Received aggregation request")
    logs = []

    try:
        for file in LOG_DIR.glob("log_*.json"):
            try:
                with file.open("r", encoding="utf-8") as f:
                    logs.append(json.load(f))
                file.unlink()
            except Exception as e:
                logger.warning(f"[LogCollector] Error reading {file.name}: {e}")

        logger.info(f"[LogCollector] Successfully aggregated and removed {len(logs)} log files")
        return JSONResponse(content=logs)

    except Exception as e:
        logger.error(f"[LogCollector] Aggregation failed: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
