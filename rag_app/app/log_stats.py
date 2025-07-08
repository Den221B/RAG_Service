import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def send_log_to_collector(data: dict) -> None:
    """
    Sends a log entry to the log_collector service via HTTP POST.
    """
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.post(settings.log_collector_url, json=data)
            response.raise_for_status()
            logger.info("[LogStats] Log sent successfully (%s)", response.status_code)
    except httpx.RequestError as exc:
        logger.warning("[LogStats] Network error: %s", exc)
    except httpx.HTTPStatusError as exc:
        logger.warning("[LogStats] HTTP error %s – %s", exc.response.status_code, exc.response.text)
    except Exception as exc:
        logger.exception("[LogStats] Unexpected error: %s", exc)


def format_log_payload(
    question: str,
    context: List[str],
    answer: str,
    stats: Dict[str, Any],
    timings: Dict[str, float],
    scores: Optional[List[Optional[float]]] = None
) -> Dict[str, Any]:
    """
    Formats a full log payload for storage or transmission.

    Args:
        question: User's input question.
        context: List of retrieved context chunks.
        answer: Model's final answer.
        stats: Stats such as IP, token counts, request time.
        timings: Time-based performance metrics.
        scores: Reranker scores for each context chunk (if available).

    Returns:
        A dict formatted for RAGAS-style logging.
    """
    logger.info("[RAG] Question: %s", question)
    logger.info("[RAG] Context:\n%s", json.dumps(context, indent=2, ensure_ascii=False))
    logger.info("[RAG] Answer: %s%s", answer[:1000], "..." if len(answer) > 1000 else "")

    ctx_items = [
        {
            "text": chunk,
            "score": scores[i] if scores and i < len(scores) else None,
        }
        for i, chunk in enumerate(context)
    ]

    return {
        "stats": [stats],
        "timings": timings,
        "texts": [
            {"question": {"text": question, "len_question": len(question)}},
            {
                "context": {
                    "items": ctx_items,
                    "len_context": len('\n'.join(context)),
                }
            },
            {"answer": {"text": answer, "len_answer": len(answer)}}
        ],
    }


def extract_timings_and_stats(
    data: dict,
    ip: str
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Extracts execution timing metrics and user statistics from a generation result.

    Args:
        data: The model's full response including timings, usage, etc.
        ip: Request origin IP address.

    Returns:
        Tuple of timing metrics and stats.
    """
    timings: Dict[str, float] = {
        "faiss_time": data.get("faiss_time", 0.0),
        "rerank_time": data.get("rerank_time", 0.0),
        "chunk_gen_time": data.get("chunk_gen_time", 0.0),
        "ttfb": data.get("timings", {}).get("ttfb", 0.0),
        "model_time": data.get("model_time", 0.0),
        "prompt_ms": data.get("timings", {}).get("prompt_ms", 0.0),
        "prompt_per_token_ms": data.get("timings", {}).get("prompt_per_token_ms", 0.0),
        "predicted_ms": data.get("timings", {}).get("predicted_ms", 0.0),
        "predicted_per_token_ms": data.get("timings", {}).get("predicted_per_token_ms", 0.0),
        "all_time": data.get("faiss_time", 0.0) + data.get("model_time", 0.0),
    }

    stats: Dict[str, Any] = {
        "ip": ip,
        "request_time": datetime.utcnow().isoformat(),
        "generated_tokens": data.get("usage", {}).get("completion_tokens"),
        "question_context_tokens": data.get("usage", {}).get("prompt_tokens"),
        "total_tokens": data.get("usage", {}).get("total_tokens"),
        "finish_reason": data.get("finish_reason", "unknown"),
    }

    return timings, stats
