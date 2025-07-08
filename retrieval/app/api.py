import logging
from fastapi import APIRouter, Depends, HTTPException

from schemas import (
    RerankRequest,
    RerankResponse,
    EncodeRequest,
    EncodeResponse,
)
from model_wrapper import get_backend, EmbeddingBackend
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/healthz")
def health_check(backend: EmbeddingBackend = Depends(get_backend)) -> dict:
    """
    Health check endpoint to verify model, device, and FAISS index status.
    """
    return {
        "status": "ok",
        "device": backend.device,
        "model": settings.model_name,
        "vectors": backend.faiss_index.ntotal,
    }


@router.post("/get_chunks", response_model=RerankResponse)
async def get_chunks(
    request: RerankRequest,
    backend: EmbeddingBackend = Depends(get_backend),
) -> RerankResponse:
    """
    Returns top-k relevant document chunks with optional reranking.
    """
    try:
        chunks, scores, faiss_time, rerank_time = backend.get_top_chunks(
            question=request.question,
            k=request.k,
            top_n=request.top_n,
            use_reranker=request.use_reranker,
        )
        return RerankResponse(
            chunks=chunks,
            scores=scores,
            faiss_time=faiss_time,
            rerank_time=rerank_time,
        )
    except Exception as e:
        logger.exception("[API] Failed to retrieve chunks: %s", e)
        raise HTTPException(status_code=500, detail="Internal error in get_chunks")


@router.post("/encode", response_model=EncodeResponse)
async def encode(
    request: EncodeRequest,
    backend: EmbeddingBackend = Depends(get_backend),
) -> EncodeResponse:
    """
    Encodes input texts into dense vector embeddings.
    """
    if not request.texts:
        raise HTTPException(status_code=400, detail="Text list must not be empty.")

    try:
        embeddings = backend.encode(request.texts).tolist()
        return EncodeResponse(embeddings=embeddings)
    except Exception as e:
        logger.exception("[API] Failed to encode texts: %s", e)
        raise HTTPException(status_code=500, detail="Internal error in encode")
