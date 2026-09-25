"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import math
import re
from typing import Any
import numpy as np
from rank_bm25 import BM25Okapi

from .contracts import validate_search_results

CORPUS: list[dict] = []
_INDEX_CACHE: dict[str, Any] = {"corpus_id": None, "corpus_len": 0, "index": None}


class RobustBM25Okapi(BM25Okapi):
    """
    Biến thể BM25Okapi dùng công thức chuẩn Lucene IDF:
    IDF = ln(1 + (N - n + 0.5) / (n + 0.5))
    giúp tránh giá trị IDF = 0 khi n = N/2 hoặc với tập ngữ liệu nhỏ.
    """

    def _calc_idf(self, nd):
        for word, freq in nd.items():
            self.idf[word] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))


def tokenize(text: str) -> list[str]:
    """Tokenize tiếng Việt đơn giản: chuẩn hóa chữ thường, tách từ theo ký tự phân cách."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower(), flags=re.UNICODE)
    return cleaned.split()


def build_bm25_index(corpus: list[dict]) -> BM25Okapi:
    """Tạo BM25 index từ danh sách corpus chunks."""
    tokenized = [tokenize(item["content"]) for item in corpus]
    return RobustBM25Okapi(tokenized)


def _get_bm25_index(corpus: list[dict]) -> BM25Okapi:
    """Lấy hoặc tạo mới BM25 index có cache theo corpus hiện tại."""
    global _INDEX_CACHE
    current_id = id(corpus)
    current_len = len(corpus)
    if (
        _INDEX_CACHE["corpus_id"] != current_id
        or _INDEX_CACHE["corpus_len"] != current_len
        or _INDEX_CACHE["index"] is None
    ):
        _INDEX_CACHE = {
            "corpus_id": current_id,
            "corpus_len": current_len,
            "index": build_bm25_index(corpus),
        }
    return _INDEX_CACHE["index"]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    global CORPUS
    if not CORPUS:
        try:
            from .task4_chunking_indexing import chunk_documents, load_documents

            documents = load_documents()
            CORPUS = chunk_documents(documents)
        except Exception:
            pass

    if not CORPUS or not query.strip() or top_k <= 0:
        return []

    tokens = tokenize(query)
    if not tokens:
        return []

    bm25 = _get_bm25_index(CORPUS)
    scores = bm25.get_scores(tokens)

    # Sắp xếp index theo điểm số giảm dần
    indices = np.argsort(scores)[::-1]

    results: list[dict] = []
    seen_ids: set[str] = set()

    for idx in indices:
        item = CORPUS[idx]
        item_id = str(item["id"])
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)

        clean_metadata = dict(item.get("metadata", {}))
        if clean_metadata.get("url") == "":
            clean_metadata["url"] = None
        if "chunk_index" in clean_metadata:
            clean_metadata["chunk_index"] = int(clean_metadata["chunk_index"])

        results.append({
            "id": item_id,
            "content": str(item["content"]),
            "score": float(scores[idx]),
            "metadata": clean_metadata,
            "retrieval_method": "bm25",
        })

        if len(results) >= top_k:
            break

    validate_search_results(results, top_k=top_k, expected_method="bm25")
    return results


if __name__ == "__main__":
    for res in lexical_search("bảo hiểm xã hội bắt buộc", top_k=3):
        print(res)
