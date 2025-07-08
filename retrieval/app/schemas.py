from typing import List, Optional
from pydantic import BaseModel, Field


class RerankRequest(BaseModel):
    question: str = Field(..., description="User question")
    k: int = Field(..., description="Number of nearest neighbors to retrieve from FAISS")
    top_n: int = Field(..., description="Number of chunks to return after reranking")
    use_reranker: bool = Field(..., description="Whether to apply the reranker")


class RerankResponse(BaseModel):
    chunks: List[str] = Field(..., description="Final context chunks after reranking")
    scores: List[Optional[float]] = Field(..., description="Score for each chunk or None")
    faiss_time: float = Field(..., description="FAISS search time in seconds")
    rerank_time: float = Field(..., description="Reranking time in seconds")


class EncodeRequest(BaseModel):
    texts: List[str] = Field(..., description="List of input texts to embed")


class EncodeResponse(BaseModel):
    embeddings: List[List[float]] = Field(..., description="List of dense embeddings (one per input text)")
