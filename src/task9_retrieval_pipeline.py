"""Task 9 — Hybrid retrieval with fallback based on raw dense cosine scores."""

import logging
import math
import os

from .contracts import validate_search_results
from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search


# Provisional default: calibrate against in-domain and out-of-domain queries.
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD") or "0.3")
DEFAULT_TOP_K = 5
logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Fuse once, then try PageIndex only when dense confidence is insufficient.

    Disabling reranking returns the dense baseline, preserving the starter's
    comparison mode. Failed, empty or invalid fallback results retain baseline
    results; no evidence yields an empty list for generation's safe refusal.
    """
    if top_k <= 0 or not query.strip():
        return []
    if not math.isfinite(score_threshold) or not -1 <= score_threshold <= 1:
        raise ValueError("score_threshold must be a finite cosine score between -1 and 1")

    dense = semantic_search(query, top_k=top_k * 2)
    sparse = lexical_search(query, top_k=top_k * 2)
    best_dense_score = max((item["score"] for item in dense), default=float("-inf"))
    hybrid = (
        rerank_rrf([dense, sparse], top_k=top_k)
        if use_reranking else dense[:top_k]
    )

    if best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            validate_search_results(fallback, top_k=top_k, expected_method="pageindex")
            if fallback:
                return fallback
        except Exception as exc:
            logger.warning("PageIndex fallback failed (%s); keeping retrieval results", type(exc).__name__)
    return hybrid[:top_k]


if __name__ == "__main__":
    for result in retrieve("test query", top_k=3):
        print(result)
