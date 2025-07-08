import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from config import Settings, get_settings
from document_linker import inject_links_into_chunks
from schemas import GenerationResult
from llm_client import LLMClient, RetrieverClient

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGService:
    """High-level RAG agent (singleton via `get_rag_service`)."""

    _active_requests: int = 0
    _lock = asyncio.Lock()

    @classmethod
    async def _inc(cls) -> None:
        async with cls._lock:
            cls._active_requests += 1

    @classmethod
    async def _dec(cls) -> None:
        async with cls._lock:
            cls._active_requests = max(0, cls._active_requests - 1)

    @classmethod
    def active_requests(cls) -> int:
        """Current number of concurrent requests."""
        return cls._active_requests

    def __init__(self, st: Settings):
        self._settings = st
        self._retriever = RetrieverClient(st)
        self._llm = LLMClient(st)
        self._logger = logging.getLogger(self.__class__.__name__)

    @asynccontextmanager
    async def _req_scope(self):
        await self._inc()
        try:
            yield
        finally:
            await self._dec()

    async def generate(self, question: str) -> GenerationResult:
        """Generates a full answer (non-streaming)."""
        async with self._req_scope():
            chunks, faiss_t, rerank_t, scores = await self._gather_context(question)

            payload = self._build_payload(question, chunks, stream=False)
            t0 = time.perf_counter()
            response_json, error = await self._llm.chat(payload)
            model_time = time.perf_counter() - t0

            if error or response_json is None:
                answer = f"LLM error: {error}"
                finish_reason = "error"
                usage: Dict[str, Any] = {}
                timings: Dict[str, Any] = {}
            else:
                answer = response_json["choices"][0]["message"]["content"]
                finish_reason = response_json["choices"][0].get("finish_reason", "stop")
                usage = response_json.get("usage", {})
                timings = response_json.get("timings", {})

            self._logger.info("✅ Answer generated in %.2f sec", model_time)

            return GenerationResult(
                question=question,
                answer=answer,
                context=chunks,
                scores=scores,
                faiss_time=faiss_t,
                rerank_time=rerank_t,
                chunk_gen_time=faiss_t + rerank_t,
                model_time=model_time,
                timings=timings,
                usage=usage,
                finish_reason=finish_reason,
            )

    async def stream(self, question: str) -> AsyncGenerator[str, None]:
        """Line-by-line generation (SSE / chunked)."""
        async with self._req_scope():
            chunks, faiss_t, rerank_t, scores = await self._gather_context(question)
            payload = self._build_payload(question, chunks, stream=True)

            t_start = time.perf_counter()
            first_chunk = False
            ttfb: float = 0.0

            buf = ""
            usage: Dict[str, Any] = {}
            timings: Dict[str, Any] = {}
            finish_reason: Optional[str] = None

            async for line in self._llm.stream_chat(payload):
                if line == "[DONE]":
                    break
                try:
                    jd = json.loads(line)
                except json.JSONDecodeError:
                    self._logger.warning("[STREAM] Non‑JSON response: %.200s", line)
                    continue

                delta = jd["choices"][0].get("delta", {})
                content = delta.get("content")
                if content:
                    if not first_chunk:
                        ttfb = time.perf_counter() - t_start
                        timings["ttfb"] = ttfb
                        first_chunk = True
                        self._logger.info("⏱️ TTFB: %.2f sec", ttfb)
                    buf += content
                    yield content

                finish_reason = jd["choices"][0].get("finish_reason", finish_reason)
                usage.update(jd.get("usage", {}))
                timings.update(jd.get("timings", {}))

            model_time = time.perf_counter() - t_start

            yield json.dumps(
                GenerationResult(
                    question=question,
                    answer=buf,
                    context=chunks,
                    scores=scores,
                    faiss_time=faiss_t,
                    rerank_time=rerank_t,
                    chunk_gen_time=faiss_t + rerank_t,
                    model_time=model_time,
                    timings=timings,
                    usage=usage,
                    finish_reason=finish_reason or "stop",
                ).dict()
            )

    async def aclose(self) -> None:
        await asyncio.gather(
            self._retriever.aclose(),
            self._llm.aclose(),
            return_exceptions=True,
        )

    async def _gather_context(
        self, question: str
    ) -> Tuple[List[str], float, float, List[Optional[float]]]:
        chunks_raw, faiss_t, rerank_t, scores = await self._retriever.get_chunks(
            question=question,
            k=self._settings.default_k,
            top_n=self._settings.default_top_n,
            use_reranker=self._settings.use_reranker,
        )
        if len(chunks_raw) >= 1:
            chunks = inject_links_into_chunks(chunks_raw)
        else:
            self._logger.warning("[RAG] No chunks retrieved — fallback message injected.")
            chunks = [
                "[System message] Retrieval service is unavailable. Please contact support.\n"
                "LLM MUST PASS THIS TO THE USER!",
            ]

        chunks = chunks[::-1]
        chunks.extend(self._silly_handler(question))

        return chunks, faiss_t, rerank_t, scores

    def _build_payload(
        self, question: str, context_chunks: List[str], *, stream: bool
    ) -> Dict[str, Any]:
        context_block = "\n".join(context_chunks)

        system_prompt = self._settings.system_prompt.strip()
        user_prompt = f"Context:\n{context_block}\n\nQuestion: {question}"

        return {
            "model": self._settings.model_name,
            "stream": stream,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self._settings.temperature,
            "n_predict": self._settings.max_generated_tokens,
            "stop": ["<|im_end|>"],
        }

    def _silly_handler(self, question: str) -> List[str]:
        question = question.lower()
        system_chunks = []

        for rule in self._settings.system_hints:
            if any(keyword in question for keyword in rule["keywords"]):
                system_chunks.append(rule["message"])

        return system_chunks


@lru_cache(maxsize=1)
def get_rag_service() -> "RAGService":
    """Returns singleton instance of RAGService."""
    return RAGService(settings)
