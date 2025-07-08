import json
import logging
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from rag_service import RAGService, get_rag_service
from schemas import QueryRequest
from log_stats import (
    extract_timings_and_stats,
    format_log_payload,
    send_log_to_collector,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _real_ip(request: Request) -> str:
    """
    Extract real IP address from proxy headers or client host.
    """
    return (
        request.headers.get("x-forwarded-for")
        or request.headers.get("x-real-ip")
        or request.client.host
    )


@router.get("/metrics")
async def metrics(service: RAGService = Depends(get_rag_service)) -> dict:
    """
    Return the current number of active requests in the RAG service.
    """
    return {"active_requests": service.active_requests()}


@router.post("/query")
async def query(
    req: QueryRequest,
    request: Request,
    service: RAGService = Depends(get_rag_service),
):
    """
    Handle a full query-response request with logging.
    """
    res = await service.generate(req.message)

    timings, stats = extract_timings_and_stats(res.dict(), ip=_real_ip(request))

    await send_log_to_collector(
        format_log_payload(
            question=res.question,
            context=res.context,
            answer=res.answer,
            stats=stats,
            timings=timings,
            scores=res.scores,
        )
    )

    return JSONResponse(
        {
            "received_data": {"message": res.answer},
            "server_info": {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        },
        status_code=status.HTTP_200_OK,
    )


@router.post("/stream")
async def stream_answer(
    req: QueryRequest,
    request: Request,
    service: RAGService = Depends(get_rag_service),
):
    """
    Handle streamed generation response with logging.
    """
    real_ip = _real_ip(request)

    async def _generator() -> AsyncGenerator[str, None]:
        async for chunk in service.stream(req.message):
            try:
                parsed = json.loads(chunk)
                if "answer" in parsed:
                    timings, stats = extract_timings_and_stats(parsed, ip=real_ip)
                    await send_log_to_collector(
                        format_log_payload(
                            question=parsed["question"],
                            context=parsed["context"],
                            answer=parsed["answer"],
                            stats=stats,
                            timings=timings,
                            scores=parsed.get("scores"),
                        )
                    )
                    yield ""
                else:
                    yield json.dumps(parsed, ensure_ascii=False)
            except Exception:
                yield chunk

    return StreamingResponse(_generator(), media_type="text/plain; charset=utf-8")
