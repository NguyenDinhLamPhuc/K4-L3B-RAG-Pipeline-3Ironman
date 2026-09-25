"""Task 3 - standardise landing legal/news data as Markdown."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown
from pdfminer.high_level import extract_text


ROOT_DIR = Path(__file__).resolve().parent.parent
LANDING_DIR = ROOT_DIR / "data" / "landing"
OUTPUT_DIR = ROOT_DIR / "data" / "standardized"
LEGAL_MANIFEST = LANDING_DIR / "legal" / "manifest.json"
STANDARDIZED_MANIFEST = OUTPUT_DIR / "manifest.json"
SUPPORTED_LEGAL_SUFFIXES: Final = {".pdf", ".doc", ".docx"}
MIN_UNIQUE_ARTICLES: Final = {
    "45/2019/QH14": 200,
    "41/2024/QH15": 130,
    "145/2020/NĐ-CP": 100,
    "158/2025/NĐ-CP": 20,
}


def _yaml_string(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _frontmatter(metadata: dict) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, int):
            rendered = str(value)
        elif value is None:
            rendered = "null"
        else:
            rendered = _yaml_string(value)
        lines.append(f"{key}: {rendered}")
    lines.extend(["---", ""])
    return "\n".join(lines)


def _normalise_legal_text(text: str, title: str) -> str:
    text = (
        text.replace("\x0c", "\n")
        .replace("\u2028", "\n")
        .replace("\xa0", " ")
        .replace("\u200b", "")
    )
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if re.match(r"^(?:\d+\s+)?CÔNG BÁO/Số", line, flags=re.IGNORECASE):
            continue
        if re.match(r"^PAGE\s+\d+", line, flags=re.IGNORECASE):
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if re.fullmatch(r"Chương\s+[IVXLCDM]+", line, flags=re.IGNORECASE):
            line = f"## {line}"
        elif re.fullmatch(r"Mục\s+\d+", line, flags=re.IGNORECASE):
            line = f"### {line}"
        elif re.match(r"^Điều\s+\d+[a-zA-Z]?\s*[.:-]", line, flags=re.IGNORECASE):
            line = f"#### {line}"
        lines.append(line)

    body = "\n".join(lines).strip()
    body = re.sub(r"\n{3,}", "\n\n", body)
    if len(body) < 200:
        raise ValueError(f"Extracted legal text is unexpectedly short: {len(body)} characters")
    return f"# {title}\n\n{body}\n"


def _load_legal_metadata() -> dict[str, dict]:
    if not LEGAL_MANIFEST.is_file():
        raise FileNotFoundError(
            f"Missing legal provenance manifest: {LEGAL_MANIFEST}. Run Task 1 first."
        )
    manifest = json.loads(LEGAL_MANIFEST.read_text(encoding="utf-8"))
    documents = manifest.get("documents", [])
    return {item["filename"]: item for item in documents}


def _extract_html_article(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    candidate = soup.select_one("[itemprop='articleBody'], .detail-content, article, main")
    if candidate is None:
        raise ValueError(f"Could not locate the legal text in {path}")
    for element in candidate.select(
        "script, style, nav, header, footer, form, iframe, noscript, aside, svg, "
        "figure, .VCSortableInPreviewMode.type-6, "
        ".VCSortableInPreviewMode.type-6_preview"
    ):
        element.decompose()
    return to_markdown(str(candidate), heading_style="ATX", bullets="-")


def _extract_legacy_doc(path: Path) -> str:
    textutil = shutil.which("textutil")
    if textutil:
        result = subprocess.run(
            [textutil, "-convert", "txt", "-stdout", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout
    antiword = shutil.which("antiword")
    if antiword:
        result = subprocess.run(
            [antiword, str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout
    raise RuntimeError(
        f"Cannot extract legacy Word file {path}; install textutil (macOS) "
        "or antiword, or reuse the committed standardized Markdown"
    )


def _extract_file_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text(str(path))
    if suffix == ".doc":
        return _extract_legacy_doc(path)
    if suffix in {".html", ".htm"}:
        return _extract_html_article(path)
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        from markitdown import MarkItDown

        return MarkItDown().convert(str(path)).text_content or ""
    raise ValueError(f"Unsupported text extraction source: {path}")


def _extract_legal_text(path: Path, source: dict) -> tuple[str, dict]:
    text = _extract_file_text(path)
    extraction = {
        "filename": path.name,
        "url": source["download_url"],
        "kind": "original_pdf",
    }
    if len(text.strip()) < 200:
        support = source.get("text_source")
        if not support:
            raise ValueError(
                f"Original is scanned and no supporting text source is recorded: {path}"
            )
        support_path = LANDING_DIR / "legal_text" / support["filename"]
        if not support_path.is_file():
            raise FileNotFoundError(f"Missing supporting text source: {support_path}")
        text = _extract_file_text(support_path)
        extraction = {
            "filename": support["filename"],
            "url": support["url"],
            "kind": support["purpose"],
        }

    article_numbers = {
        int(number)
        for number in re.findall(
            r"(?im)^\s*#{0,6}\s*(?:\*{1,2})?\s*Điều\s+(\d+)\s*[.:-]", text
        )
    }
    minimum = MIN_UNIQUE_ARTICLES[source["law_number"]]
    if len(article_numbers) < minimum:
        raise ValueError(
            f"Incomplete legal text for {source['law_number']}: found "
            f"{len(article_numbers)} unique article numbers, expected at least {minimum}"
        )
    extraction["unique_article_numbers"] = len(article_numbers)
    return text, extraction


def convert_legal_docs() -> None:
    """Convert every manifest-backed legal PDF/DOCX and retain provenance."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata_by_filename = _load_legal_metadata()

    paths = sorted(
        path
        for path in legal_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_LEGAL_SUFFIXES
    )
    if len(paths) < 3:
        raise ValueError(f"Expected at least 3 legal documents, found {len(paths)}")

    for path in paths:
        if path.name not in metadata_by_filename:
            raise ValueError(f"No provenance metadata for legal document: {path.name}")
        source = metadata_by_filename[path.name]
        metadata = {
            "id": source["id"],
            "title": source["title"],
            "source": path.name,
            "url": source["url"],
            "download_url": source["download_url"],
            "doc_type": "legal",
            "law_number": source["law_number"],
            "issued_date": source["issued_date"],
            "effective_date": source["effective_date"],
            "domain": source["domain"],
            "source_priority": source["source_priority"],
            "historical": source["historical"],
        }
        extracted_text, extraction = _extract_legal_text(path, source)
        metadata.update(
            {
                "text_extraction_source": extraction["filename"],
                "text_extraction_url": extraction["url"],
                "original_pdf_sha256": source["sha256"],
            }
        )
        body = _normalise_legal_text(extracted_text, source["title"])
        output = output_dir / f"{path.stem}.md"
        output.write_text(_frontmatter(metadata) + body, encoding="utf-8")
        print(
            f"Standardized: {output} ({len(body):,} characters, "
            f"{extraction['unique_article_numbers']} article numbers, "
            f"text source: {extraction['filename']})"
        )


def convert_news_articles() -> None:
    """Convert validated article JSON files and retain crawl metadata."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = sorted(news_dir.glob("article_*.json"))
    if len(paths) < 5:
        raise ValueError(f"Expected at least 5 news articles, found {len(paths)}")

    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        required = {"url", "title", "date_crawled", "content_markdown"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"{path.name} is missing fields: {sorted(missing)}")
        content = str(data["content_markdown"]).strip()
        if len(content) < 200:
            raise ValueError(f"{path.name} has insufficient article content")

        metadata = {
            "id": data.get(
                "id", f"NEWS-{int(path.stem.rsplit('_', 1)[-1]):02d}"
            ),
            "title": data["title"],
            "source": path.name,
            "url": data["url"],
            "final_url": data.get("final_url", data["url"]),
            "doc_type": "news",
            "date_crawled": data["date_crawled"],
            "domain": (
                "social_insurance"
                if "bảo hiểm xã hội" in f"{data['title']} {content[:500]}".lower()
                else "labor"
            ),
            "source_priority": 2,
            "historical": False,
        }
        for key in ("topic", "source_type", "preferred_url", "fallback_reason"):
            if data.get(key):
                metadata[key] = data[key]
        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n"
            "---\n\n"
        )
        output = output_dir / f"{path.stem}.md"
        output.write_text(
            _frontmatter(metadata) + header + content + "\n", encoding="utf-8"
        )
        print(f"Standardized: {output} ({len(content):,} content characters)")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_standardized_manifest() -> None:
    files = sorted(OUTPUT_DIR.glob("*/*.md"))
    legal_count = sum(path.parent.name == "legal" for path in files)
    news_count = sum(path.parent.name == "news" for path in files)
    if legal_count < 3 or news_count < 5:
        raise ValueError(
            f"Incomplete standardized corpus: {legal_count} legal, {news_count} news"
        )
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "document_count": len(files),
        "legal_count": legal_count,
        "news_count": news_count,
        "documents": [
            {
                "path": path.relative_to(ROOT_DIR).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in files
        ],
    }
    STANDARDIZED_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved corpus manifest: {STANDARDIZED_MANIFEST}")


def convert_all() -> None:
    """Convert all landing data and verify corpus coverage."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    _write_standardized_manifest()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
