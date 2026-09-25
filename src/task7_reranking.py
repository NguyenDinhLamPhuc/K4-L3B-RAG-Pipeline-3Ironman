"""Task 7 — Reciprocal Rank Fusion; scores are ranks, not confidence."""

from copy import deepcopy


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse unique-ID ranked lists without mutating their items.

    Repeated IDs across lists contribute once per list. Repeated IDs within
    one list are an upstream contract error and must be fixed by its producer.
    The first occurrence supplies content and metadata; ties retain input order.
    """
    if k < 0:
        raise ValueError("RRF k must be non-negative")
    if top_k <= 0:
        return []
    scores = {}
    items = {}
    for ranked_list in ranked_lists:
        seen = set()
        for rank, item in enumerate(ranked_list, start=1):
            item_id = item["id"]
            if item_id in seen:
                raise ValueError(
                    f"Duplicate ID {item_id!r} within a ranked list; fix the upstream retriever"
                )
            seen.add(item_id)
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            items.setdefault(item_id, item)

    results = []
    for item_id in sorted(scores, key=scores.get, reverse=True)[:top_k]:
        result = deepcopy(items[item_id])
        result["score"] = scores[item_id]
        result["retrieval_method"] = "hybrid"
        results.append(result)
    return results
