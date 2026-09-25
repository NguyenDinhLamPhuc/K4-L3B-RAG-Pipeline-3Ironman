"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
DOCUMENT_IDS_PATH = STANDARDIZED_DIR.parent / "pageindex_doc_ids.json"
logger = logging.getLogger(__name__)


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        logger.warning("PAGEINDEX_API_KEY is not configured; skipping uploads")
        return

    import requests
    import yaml
    from fpdf import FPDF
    from pageindex import PageIndexClient

    try:
        document_ids = (
            json.loads(DOCUMENT_IDS_PATH.read_text(encoding="utf-8"))
            if DOCUMENT_IDS_PATH.exists() else {}
        )
        if not isinstance(document_ids, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) or not value.strip()
            for key, value in document_ids.items()
        ):
            raise ValueError("Invalid source-to-document-ID cache")
    except (OSError, ValueError) as exc:
        logger.warning("Cannot read PageIndex cache: %s", exc)
        return

    font_paths = [
        Path(os.getenv("PAGEINDEX_FONT_PATH", "")),
        Path(os.getenv("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    font_path = next((path for path in font_paths if path.is_file()), None)
    with requests.Session() as session, TemporaryDirectory(prefix="pageindex_") as temp_dir:
        session.headers.update({"api_key": PAGEINDEX_API_KEY})
        for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
            if not path.is_file() or path.name.startswith("."):
                continue
            try:
                content = path.read_text(encoding="utf-8").strip()
                metadata = {}
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) == 3:
                        metadata = yaml.safe_load(parts[1]) or {}
                        content = parts[2].strip()
                source = str(metadata.get("source") or path.name).strip()
                if source in document_ids or not content:
                    continue
                if font_path is None:
                    raise ValueError("Set PAGEINDEX_FONT_PATH to a Unicode TrueType font")
                pdf = FPDF()
                pdf.add_font("Document", fname=str(font_path))
                pdf.set_font("Document", size=11)
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.multi_cell(w=0, h=6, text=content)
                pdf_path = Path(temp_dir) / "document.pdf"
                pdf.output(str(pdf_path))
                with pdf_path.open("rb") as document:
                    response = session.post(
                        f"{PageIndexClient.BASE_URL}/doc/",
                        files={"file": (f"{path.stem}.pdf", document, "application/pdf")},
                        data={"if_retrieval": True},
                        timeout=(10, 120),
                    )
                response.raise_for_status()
                document_id = response.json().get("doc_id")
                if not isinstance(document_id, str) or not document_id.strip():
                    raise ValueError("PageIndex upload response has no valid doc_id")
            except Exception as exc:
                logger.warning("PageIndex upload failed for %s: %s", path, exc)
                continue

            document_ids[source] = document_id
            try:
                DOCUMENT_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
                temporary_cache = DOCUMENT_IDS_PATH.with_suffix(".json.tmp")
                temporary_cache.write_text(
                    json.dumps(document_ids, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                temporary_cache.replace(DOCUMENT_IDS_PATH)
            except OSError as exc:
                logger.warning("Cannot save PageIndex cache: %s", exc)
                return


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if not PAGEINDEX_API_KEY or not query.strip() or top_k <= 0:
        return []

    from concurrent.futures import ThreadPoolExecutor
    from math import isfinite
    from time import monotonic, sleep

    import requests
    from pageindex import PageIndexClient

    try:
        document_ids = json.loads(DOCUMENT_IDS_PATH.read_text(encoding="utf-8"))
        if not isinstance(document_ids, dict) or any(
            not isinstance(source, str) or not source.strip()
            or not isinstance(doc_id, str) or not doc_id.strip()
            for source, doc_id in document_ids.items()
        ):
            raise ValueError("Invalid source-to-document-ID cache")
    except (OSError, ValueError) as exc:
        logger.warning("Cannot read PageIndex cache: %s", exc)
        return []

    def retrieve(item: tuple[str, str]) -> list[dict]:
        source, doc_id = item
        results = []
        try:
            with requests.Session() as session:
                session.headers.update({"api_key": PAGEINDEX_API_KEY})
                deadline = monotonic() + 60
                response = session.post(
                    f"{PageIndexClient.BASE_URL}/retrieval/",
                    json={"doc_id": doc_id, "query": query, "thinking": False},
                    timeout=(5, 30),
                )
                response.raise_for_status()
                retrieval_id = response.json()["retrieval_id"]
                while True:
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        raise TimeoutError("PageIndex retrieval timed out")
                    response = session.get(
                        f"{PageIndexClient.BASE_URL}/retrieval/{retrieval_id}/",
                        timeout=(min(5, remaining), min(10, remaining)),
                    )
                    response.raise_for_status()
                    payload = response.json()
                    status = payload.get("status")
                    if status in {"failed", "error", "cancelled"}:
                        raise ValueError(f"PageIndex retrieval status: {status}")
                    if status == "completed" or "retrieved_nodes" in payload:
                        break
                    sleep(min(0.5, max(0, deadline - monotonic())))

            for rank, node in enumerate(payload.get("retrieved_nodes", [])):
                if not isinstance(node, dict):
                    continue
                content = node.get("content") or node.get("text")
                if isinstance(content, list):
                    content = "\n\n".join(
                        text for page in content if isinstance(page, dict)
                        for text in [page.get("text") or page.get("content")]
                        if isinstance(text, str) and text.strip()
                    )
                if not isinstance(content, str) or not content.strip():
                    continue
                score = node.get("score")
                if (not isinstance(score, (int, float)) or isinstance(score, bool)
                        or not isfinite(score)):
                    score = 1.0 / (rank + 1)
                results.append({
                    "id": f"{doc_id}:{node.get('node_id', rank)}",
                    "content": content.strip(),
                    "score": float(score),
                    "metadata": {
                        "source": source,
                        "title": str(node.get("title") or Path(source).stem or source),
                        "doc_type": "pdf",
                        "url": source if source.startswith(("http://", "https://")) else None,
                        "chunk_index": rank,
                    },
                    "retrieval_method": "pageindex",
                })
        except Exception as exc:
            logger.warning("PageIndex retrieval failed for %s: %s", source, exc)
        return results

    if not document_ids:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(document_ids))) as executor:
        results = [result for batch in executor.map(retrieve, document_ids.items())
                   for result in batch]
    results.sort(key=lambda result: result["score"], reverse=True)
    unique = {}
    for result in results:
        unique.setdefault(result["id"], result)
        if len(unique) == top_k:
            break
    return list(unique.values())


if __name__ == "__main__":
    upload_documents()
