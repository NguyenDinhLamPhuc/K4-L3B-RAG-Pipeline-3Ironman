"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import os
from pathlib import Path
from typing import Any
import yaml
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .contracts import validate_document

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

_EMBEDDING_MODEL_INSTANCE: Any = None


def _get_embedding_model():
    """Tải và lưu trữ singleton instance của embedding model."""
    global _EMBEDDING_MODEL_INSTANCE
    if _EMBEDDING_MODEL_INSTANCE is None:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL)
        _EMBEDDING_MODEL_INSTANCE = SentenceTransformer(model_name)
    return _EMBEDDING_MODEL_INSTANCE


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Tạo vector embeddings cho danh sách văn bản theo provider trong .env."""
    if not texts:
        return []

    provider = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").lower()

    if provider == "sentence_transformers":
        model = _get_embedding_model()
        embeddings = model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        response = client.embeddings.create(input=texts, model=model_name)
        return [item.embedding for item in response.data]

    if provider == "gemini":
        from google import genai

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
        embeddings: list[list[float]] = []
        for text in texts:
            result = client.models.embed_content(
                model=model_name,
                contents=text,
            )
            embeddings.append(result.embedding.values)
        return embeddings

    # Fallback mặc định về sentence_transformers
    model = _get_embedding_model()
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _parse_frontmatter_and_content(raw_text: str) -> tuple[dict, str]:
    """Tách YAML frontmatter và nội dung Markdown chính."""
    metadata = {}
    content = raw_text
    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            raw_fm = parts[1].strip()
            content = parts[2].strip()
            try:
                parsed = yaml.safe_load(raw_fm)
                if isinstance(parsed, dict):
                    metadata = parsed
            except Exception:
                pass
    return metadata, content


def load_documents() -> list[dict]:
    """Đọc Markdown trong data/standardized/ và trả về danh sách Document."""
    if not STANDARDIZED_DIR.exists():
        return []

    documents: list[dict] = []
    # Tìm kiếm toàn bộ các file .md trong thư mục standardized
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        if path.name.startswith(".") or not path.is_file():
            continue

        raw_text = path.read_text(encoding="utf-8").strip()
        if not raw_text:
            continue

        fm_meta, main_content = _parse_frontmatter_and_content(raw_text)
        content_to_use = main_content if main_content.strip() else raw_text

        # Xác định doc_type
        doc_type = fm_meta.get("doc_type")
        if not doc_type:
            doc_type = "legal" if "legal" in path.parts else "news"

        # Xác định metadata theo hợp đồng
        source = str(fm_meta.get("source") or path.name).strip()
        title = str(fm_meta.get("title") or path.stem.replace("_", " ")).strip()
        url = fm_meta.get("url")
        if url is not None and not str(url).strip():
            url = None

        doc_meta = {
            "source": source,
            "title": title,
            "doc_type": doc_type,
            "url": url,
        }

        # Lưu giữ các trường ngữ cảnh bổ sung nếu có trong frontmatter
        for extra_key in (
            "law_number",
            "effective_date",
            "issued_date",
            "domain",
            "historical",
            "source_priority",
        ):
            if extra_key in fm_meta:
                doc_meta[extra_key] = fm_meta[extra_key]

        doc_id = path.relative_to(STANDARDIZED_DIR).as_posix()
        document = {
            "id": doc_id,
            "content": content_to_use,
            "metadata": doc_meta,
        }
        validate_document(document, require_chunk=False)
        documents.append(document)

    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index tuân thủ contract."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n#### ", "\n### ", "\n## ", "\n# ", "\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict] = []
    for document in documents:
        raw_chunks = splitter.split_text(document["content"])
        chunk_idx = 0
        for text in raw_chunks:
            cleaned_text = text.strip()
            if not cleaned_text:
                continue

            chunk_meta = dict(document["metadata"])
            chunk_meta["chunk_index"] = chunk_idx

            chunk = {
                "id": f"{document['id']}::chunk-{chunk_idx}",
                "content": cleaned_text,
                "metadata": chunk_meta,
            }
            validate_document(chunk, require_chunk=True)
            chunks.append(chunk)
            chunk_idx += 1

    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    if not chunks:
        return []

    texts = [chunk["content"] for chunk in chunks]
    vectors = embed_texts(texts)
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB một cách idempotent và batch-safe."""
    if not chunks:
        return

    collection = get_collection()

    ids: list[str] = []
    documents: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict] = []

    for chunk in chunks:
        ids.append(chunk["id"])
        documents.append(chunk["content"])
        embeddings.append(chunk["embedding"])

        # Chroma chỉ hỗ trợ kiểu dữ liệu cơ bản (str, int, float, bool)
        clean_meta = {}
        for key, value in chunk["metadata"].items():
            if value is None:
                clean_meta[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                clean_meta[key] = value
            else:
                clean_meta[key] = str(value)
        metadatas.append(clean_meta)

    # Upsert theo từng batch 100 phần tử để tránh tràn bộ đệm
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        end = i + batch_size
        collection.upsert(
            ids=ids[i:end],
            documents=documents[i:end],
            embeddings=embeddings[i:end],
            metadatas=metadatas[i:end],
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    print("Loading documents from standardized data...")
    documents = load_documents()
    print(f"Loaded {len(documents)} documents.")

    print(f"Chunking documents (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    chunks = chunk_documents(documents)
    print(f"Created {len(chunks)} chunks.")

    print("Embedding chunks...")
    embedded_chunks = embed_chunks(chunks)
    print("Upserting into Chroma vectorstore...")
    index_to_vectorstore(embedded_chunks)
    print(f"Successfully indexed {len(embedded_chunks)} chunks into ChromaDB.")


if __name__ == "__main__":
    run_pipeline()
