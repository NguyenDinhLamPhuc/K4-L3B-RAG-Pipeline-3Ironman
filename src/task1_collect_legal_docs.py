"""Task 1 - download the legal source documents used by the RAG corpus.

The document detail pages and attachments are hosted by the Vietnamese
Government Portal. Downloads are validated as real PDFs before they are
accepted into ``data/landing/legal``; an HTML error page can therefore never
silently become a ``.pdf`` corpus item.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

import requests


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "landing" / "legal"
TEXT_DATA_DIR = ROOT_DIR / "data" / "landing" / "legal_text"
MANIFEST_PATH = DATA_DIR / "manifest.json"
REQUEST_TIMEOUT: Final = (15, 120)
USER_AGENT: Final = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36 "
    "K4-Day08-RAG-Corpus/1.0"
)


LEGAL_SOURCES: Final = (
    {
        "id": "LEGAL-01",
        "filename": "bo_luat_lao_dong_2019_45_2019_QH14.pdf",
        "title": "Bộ luật Lao động 2019",
        "law_number": "45/2019/QH14",
        "issued_date": "2019-11-20",
        "effective_date": "2021-01-01",
        "domain": "labor",
        "source_priority": 1,
        "historical": False,
        "url": "https://vanban.chinhphu.vn/?docid=198540&pageid=27160",
        "download_url": (
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2019/12/45.signed.pdf"
        ),
        "text_source_url": (
            "https://apolatlegal.com/wp-content/uploads/2023/12/"
            "Luat-Lao-dong.-2019.pdf"
        ),
        "text_source_filename": "bo_luat_lao_dong_2019_45_2019_QH14_text.pdf",
    },
    {
        "id": "LEGAL-02",
        "filename": "luat_bhxh_2024_41_2024_QH15.pdf",
        "title": "Luật Bảo hiểm xã hội 2024",
        "law_number": "41/2024/QH15",
        "issued_date": "2024-06-29",
        "effective_date": "2025-07-01",
        "domain": "social_insurance",
        "source_priority": 1,
        "historical": False,
        "url": (
            "https://vanban.chinhphu.vn/"
            "?classid=1&docid=211199&orggroupid=1&pageid=27160"
        ),
        "download_url": (
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/41-2024-qh15.pdf"
        ),
    },
    {
        "id": "LEGAL-03",
        "filename": "nghi_dinh_145_2020_ND_CP.pdf",
        "title": (
            "Nghị định 145/2020/NĐ-CP hướng dẫn Bộ luật Lao động về "
            "điều kiện lao động và quan hệ lao động"
        ),
        "law_number": "145/2020/NĐ-CP",
        "issued_date": "2020-12-14",
        "effective_date": "2021-02-01",
        "domain": "labor",
        "source_priority": 1,
        "historical": False,
        "url": "https://vanban.chinhphu.vn/default.aspx?docid=201967&pageid=27160",
        "download_url": (
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2020/12/145.signed.pdf"
        ),
        "text_source_url": (
            "https://luatonline.vn/wp-content/uploads/2025/05/"
            "Nghi-dinh-145-2020-ND-CP-huong-dan-Bo-luat-Lao-dong-ve-"
            "dieu-kien-lao-dong-quan-he-lao-dong.doc"
        ),
        "text_source_filename": "nghi_dinh_145_2020_ND_CP_text.doc",
    },
    {
        "id": "LEGAL-04",
        "filename": "nghi_dinh_158_2025_ND_CP.pdf",
        "title": (
            "Nghị định 158/2025/NĐ-CP hướng dẫn Luật Bảo hiểm xã hội "
            "về bảo hiểm xã hội bắt buộc"
        ),
        "law_number": "158/2025/NĐ-CP",
        "issued_date": "2025-06-25",
        "effective_date": "2025-07-01",
        "domain": "social_insurance",
        "source_priority": 1,
        "historical": False,
        "url": (
            "https://vanban.chinhphu.vn/"
            "?classid=1&docid=214189&orggroupid=2&pageid=27160"
        ),
        "download_url": (
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2025/6/"
            "158-ndcp.signed.pdf"
        ),
        "text_source_url": (
            "https://xaydungchinhsach.chinhphu.vn/"
            "toan-van-nghi-dinh-158-2025-nd-cp-quy-dinh-ve-bao-hiem-"
            "xa-hoi-bat-buoc-119250629171336803.htm"
        ),
        "text_source_filename": "nghi_dinh_158_2025_ND_CP_text.html",
    },
)


def setup_directory() -> None:
    """Create the directory that stores original legal documents."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def _is_valid_pdf(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size <= 1024:
        return False
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download_pdf(session: requests.Session, source: dict) -> Path:
    destination = DATA_DIR / source["filename"]
    if _is_valid_pdf(destination):
        print(f"Valid existing PDF: {destination}")
        return destination

    temporary = destination.with_suffix(".pdf.tmp")
    try:
        with session.get(
            source["download_url"], timeout=REQUEST_TIMEOUT, stream=True
        ) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            with temporary.open("wb") as handle:
                for block in response.iter_content(chunk_size=1024 * 1024):
                    if block:
                        handle.write(block)

        if not _is_valid_pdf(temporary):
            raise ValueError(
                f"Downloaded file is not a valid PDF "
                f"(content-type={content_type!r}): {source['download_url']}"
            )
        temporary.replace(destination)
        print(f"Saved: {destination}")
        return destination
    finally:
        if temporary.exists():
            temporary.unlink()


def _is_valid_text_source(path: Path, expected_suffix: str | None = None) -> bool:
    if not path.is_file() or path.stat().st_size <= 1024:
        return False
    header = path.read_bytes()[:16]
    suffix = (expected_suffix or path.suffix).lower()
    if suffix == ".pdf":
        return header.startswith(b"%PDF-")
    if suffix == ".doc":
        return header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if suffix in {".html", ".htm"}:
        sample = path.read_text(encoding="utf-8", errors="ignore")[:10_000].lower()
        return "<html" in sample and "access denied" not in sample
    return False


def _download_text_source(session: requests.Session, source: dict) -> dict | None:
    url = source.get("text_source_url")
    filename = source.get("text_source_filename")
    if not url or not filename:
        return None

    destination = TEXT_DATA_DIR / filename
    if not _is_valid_text_source(destination):
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        try:
            with session.get(url, timeout=REQUEST_TIMEOUT, stream=True) as response:
                response.raise_for_status()
                with temporary.open("wb") as handle:
                    for block in response.iter_content(chunk_size=1024 * 1024):
                        if block:
                            handle.write(block)
            if not _is_valid_text_source(temporary, destination.suffix):
                raise ValueError(f"Invalid supporting text source: {url}")
            temporary.replace(destination)
            print(f"Saved text source: {destination}")
        finally:
            if temporary.exists():
                temporary.unlink()
    else:
        print(f"Valid existing text source: {destination}")

    return {
        "url": url,
        "filename": filename,
        "bytes": destination.stat().st_size,
        "sha256": _sha256(destination),
        "purpose": "text extraction for a scanned original PDF",
    }


def download_documents() -> None:
    """Download and validate all four legal documents, then write provenance."""
    setup_directory()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"})

    downloaded_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    documents = []
    for source in LEGAL_SOURCES:
        path = _download_pdf(session, source)
        text_source = _download_text_source(session, source)
        documents.append(
            {
                **source,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "downloaded_at": downloaded_at,
                "text_source": text_source,
            }
        )

    manifest = {
        "schema_version": 1,
        "generated_at": downloaded_at,
        "source": "Cổng Thông tin điện tử Chính phủ",
        "document_count": len(documents),
        "documents": documents,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved provenance: {MANIFEST_PATH}")


if __name__ == "__main__":
    download_documents()
