"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .contracts import validate_search_results
from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if not query.strip() or top_k <= 0:
        return []

    # Dùng chung hàm embed_texts của Task 4
    query_vector = embed_texts([query])[0]
    collection = get_collection()

    response = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    results: list[dict] = []
    if response and response.get("ids") and response["ids"][0]:
        ids = response["ids"][0]
        documents = response["documents"][0]
        metadatas = response["metadatas"][0]
        distances = response["distances"][0]

        seen_ids: set[str] = set()
        for item_id, content, metadata, distance in zip(
            ids, documents, metadatas, distances
        ):
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            # Chuẩn hóa metadata tuân thủ Document/Chunk contract
            clean_metadata = dict(metadata) if metadata else {}
            if clean_metadata.get("url") == "":
                clean_metadata["url"] = None
            if "chunk_index" in clean_metadata:
                clean_metadata["chunk_index"] = int(clean_metadata["chunk_index"])

            # Cosine similarity từ cosine distance: 1.0 - distance
            score = float(1.0 - distance)

            results.append({
                "id": str(item_id),
                "content": str(content),
                "score": score,
                "metadata": clean_metadata,
                "retrieval_method": "dense",
            })

    # Sắp xếp giảm dần theo score và giới hạn top_k
    results.sort(key=lambda item: item["score"], reverse=True)
    results = results[:top_k]

    validate_search_results(results, top_k=top_k, expected_method="dense")
    return results


if __name__ == "__main__":
    for res in semantic_search("thời gian thử việc", top_k=3):
        print(res)
