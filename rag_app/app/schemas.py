from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class QueryRequest(BaseModel):
    """
    User input query to the RAG agent.
    """

    message: str = Field(..., min_length=1, example="What are the occupational safety requirements?")

    @validator("message")
    def strip_and_validate(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("The query message must not be empty.")
        return v


class Chunk(BaseModel):
    """
    A single chunk of context retrieved by the retriever.
    """

    text: str
    score: Optional[float] = None


class GenerationResult(BaseModel):
    """
    Full generation result returned by the system,
    including question, answer, context, metadata and timing.
    """

    question: str
    answer: str
    context: List[str]
    scores: List[Optional[float]]

    faiss_time: float
    rerank_time: float
    chunk_gen_time: float
    model_time: float

    timings: Dict[str, Any] = Field(default_factory=dict)
    usage: Dict[str, Any] = Field(default_factory=dict)
    finish_reason: str
