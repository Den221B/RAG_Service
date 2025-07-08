import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import httpx

from config import Settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for sending requests to the LLM inference server."""

    def __init__(self, settings: Settings):
        self._url: str = settings.llm_url
        self._timeout: int = settings.timeout_clients
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers={"Authorization": f"Bearer {settings.api_key}"},
        )

    async def chat(self, payload: Dict[str, Any]) -> Tuple[Optional[dict], Optional[str]]:
        """Send a standard chat completion request."""
        try:
            resp = await self._client.post(self._url, json=payload)
            resp.raise_for_status()
            return resp.json(), None
        except httpx.TimeoutException:
            logger.error("[LLM] Request timeout.")
            return None, "timeout"
        except httpx.RequestError as exc:
            logger.error("[LLM] Network error: %s", exc)
            return None, "request_error"
        except httpx.HTTPStatusError as exc:
            logger.error("[LLM] HTTP error: %s", exc.response.status_code)
            return None, f"http_{exc.response.status_code}"
        except Exception as exc:
            logger.exception("[LLM] Unexpected error: %s", exc)
            return None, str(exc)

    async def stream_chat(self, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Send a streaming chat request (SSE / chunked)."""
        try:
            async with self._client.stream("POST", self._url, json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    yield json.dumps({
                        "error": f"http_{resp.status_code}",
                        "details": body.decode(errors="replace"),
                    })
                    return
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield line.removeprefix("data: ").strip()
        except httpx.TimeoutException:
            yield json.dumps({"error": "timeout"})
        except Exception as exc:
            yield json.dumps({"error": str(exc)})

    async def aclose(self) -> None:
        """Close the HTTP client session."""
        await self._client.aclose()


class RetrieverClient:
    """Client for sending semantic search queries to the retrieval service."""

    def __init__(self, settings: Settings):
        self._url: str = settings.retriever_url
        self._timeout: int = settings.timeout_clients
        self._client = httpx.AsyncClient(timeout=self._timeout)

    async def get_chunks(
        self,
        *,
        question: str,
        k: int,
        top_n: int,
        use_reranker: bool,
    ) -> Tuple[List[str], float, float, List[Optional[float]]]:
        """
        Sends a retrieval request and returns relevant context chunks,
        along with faiss and reranking times and scores.
        """
        payload = {
            "question": question,
            "k": k,
            "top_n": top_n,
            "use_reranker": use_reranker,
        }
        try:
            resp = await self._client.post(self._url, json=payload)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()
            return (
                data.get("chunks", []),
                float(data.get("faiss_time", 0.0)),
                float(data.get("rerank_time", 0.0)),
                data.get("scores", [None] * top_n),
            )
        except httpx.TimeoutException:
            logger.error("[Retriever] Request timeout.")
        except Exception as exc:
            logger.error("[Retriever] Connection error: %s", exc)
        return [], 0.0, 0.0, []

    async def aclose(self) -> None:
        """Close the HTTP client session."""
        await self._client.aclose()
