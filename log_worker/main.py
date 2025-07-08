import os
import json
import uuid
import time
import logging
import asyncio
from typing import Any, Dict, List

import httpx
import redis.asyncio as redis
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity


# ───────────────────── Configuration ─────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
QUEUE_NAME = os.getenv("QUEUE_NAME", "log_queue")
MODEL_URL = os.getenv("MODEL_URL", "http://retrieval:8004")
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "worker_log.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("worker")


# ───────────────────── Helper Functions ─────────────────────
async def get_embeddings(texts: List[str]) -> List[np.ndarray]:
    """
    Send texts to the embedding model and receive vector representations.
    """
    payload = {"texts": texts}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{MODEL_URL}/encode", json=payload)
        response.raise_for_status()
        embeddings = response.json()["embeddings"]
        return [np.array(vec, dtype=np.float32) for vec in embeddings]


def pairwise_cos(matrix: np.ndarray) -> np.ndarray:
    """
    Compute pairwise cosine similarities (upper triangle, excluding diagonal).
    """
    sims = cosine_similarity(matrix, matrix)
    return sims[np.triu_indices_from(sims, k=1)]


async def compute_metrics(
    question: str,
    chunks: List[str],
    answer: str,
    tau: float = 0.7,
) -> Dict[str, float]:
    """
    Compute quality metrics between question, context and answer.
    """
    t0 = time.time()
    texts = [question, answer] + chunks
    embs = await get_embeddings(texts)

    q_emb, a_emb, c_embs = embs[0], embs[1], embs[2:]

    if not c_embs:
        return {
            "answer_relevancy": float(cosine_similarity([q_emb], [a_emb])[0][0]),
            "context_relevancy_avg": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "faithfulness_approx": 0.0,
            "context_density": 0.0,
            "max_context_overlap": 0.0,
            "context_redundancy": 0.0,
            "metrics_total_time_ms": (time.time() - t0) * 1000,
        }

    sim_q_a = cosine_similarity([q_emb], [a_emb])[0][0]
    sim_q_c = cosine_similarity([q_emb], c_embs)[0]
    sim_a_c = cosine_similarity([a_emb], c_embs)[0]

    return {
        "answer_relevancy": float(sim_q_a),
        "context_relevancy_avg": float(sim_q_c.mean()),
        "context_precision": float((sim_q_c > tau).sum() / len(c_embs)),
        "context_recall": float((sim_a_c > tau).sum() / len(c_embs)),
        "faithfulness_approx": float((sim_a_c > tau).sum() / len(c_embs)),
        "context_density": float(sim_a_c.mean()),
        "max_context_overlap": float(sim_q_c.max()),
        "context_redundancy": float(pairwise_cos(np.vstack(c_embs)).mean()) if len(c_embs) > 1 else 0.0,
        "metrics_total_time_ms": (time.time() - t0) * 1000,
    }


def save_unique_log(log: Dict[str, Any], crushed: bool = False) -> None:
    """
    Save log to a uniquely named JSON file in LOG_DIR.
    """
    timestamp_ms = int(time.time() * 1000)
    unique_id = uuid.uuid4().hex
    filename = f"log_{timestamp_ms}_{unique_id}.json"
    if crushed:
        filename = filename.replace("log", "log_crushed", 1)

    filepath = LOG_DIR / filename

    try:
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"[Worker] Failed to write log {filename}: {e}")


# ───────────────────── Core Logic ─────────────────────
async def process_log(rds: redis.Redis) -> None:
    """
    Main Redis queue processing loop.
    """
    while True:
        log: Dict[str, Any] = {}
        raw = None

        try:
            _, raw = await rds.blpop(QUEUE_NAME)
            log = json.loads(raw)

            question = ""
            chunks: List[str] = []
            answer = ""

            for block in log.get("texts", []):
                if "question" in block:
                    question = block["question"]["text"]
                elif "context" in block:
                    chunks = [item["text"] for item in block["context"].get("items", []) if "text" in item]
                elif "answer" in block:
                    answer = block["answer"]["text"]

            if not all([question, chunks, answer]):
                logger.warning("[Worker] Skipped: incomplete data")
                continue

            try:
                log["metrics"] = await compute_metrics(question, chunks, answer)
            except Exception as metric_error:
                logger.warning(f"[Worker] Metric computation failed: {metric_error}")

            save_unique_log(log)

            logger.info(
                f"[Worker] Processed log — "
                f"{log.get('stats', [{}])[0].get('request_time', 'N/A')}"
            )

        except Exception as exc:
            logger.exception(f"[Worker] Processing error: {exc}")
            try:
                if log:
                    save_unique_log(log, crushed=True)
                elif raw:
                    save_unique_log({"raw": raw.decode("utf-8", errors="replace")}, crushed=True)
                else:
                    logger.warning("[Worker] Unable to save failed log: no data")
            except Exception as write_error:
                logger.warning(f"[Worker] Failed to write broken log: {write_error}")

            await asyncio.sleep(1)


async def main() -> None:
    logger.info("[Worker] Starting log_worker...")
    redis_client = await redis.from_url(REDIS_URL)
    await process_log(redis_client)


if __name__ == "__main__":
    asyncio.run(main())
