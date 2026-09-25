# KẾ HOẠCH TRIỂN KHAI DAY 8 — RAG PIPELINE

## Nhóm 3 thành viên: Phúc (nhóm trưởng) · Sang · Phát

> **Đề tài:** Chatbot RAG tra cứu **Bộ luật Lao động & Luật Bảo hiểm xã hội Việt Nam**  
> **Nguồn ưu tiên:** Thư Viện Pháp Luật (TVPL). Chỉ dùng nguồn khác khi TVPL không truy cập/crawl được hoặc cần bản PDF/văn bản gốc để đối chiếu.  
> **Nguyên tắc phân công:** Sang sở hữu các module kỹ thuật lõi và khó nhất; Phúc điều phối, tích hợp, UI và kiểm soát chất lượng; Phát sở hữu data ingestion, chuẩn hóa và lexical retrieval.  
> **Nguyên tắc Git:** Không làm song song trên cùng file nếu chưa thống nhất. Mỗi checkpoint có thứ tự merge/commit rõ ràng. Không commit `.env`, API key, `chroma_db/`, cache hoặc file tạm.

---

# 1. Hiểu đúng bài toán và đầu ra bắt buộc

Repo yêu cầu xây một chatbot RAG end-to-end trên bộ dữ liệu nhóm tự thu thập. Pipeline bắt buộc phải đi qua:

```text
Nguồn dữ liệu
    ↓
Landing data (legal + articles)
    ↓
Chuẩn hóa Markdown
    ↓
Chunking
    ↓
Embedding + ChromaDB
    ↓
Dense retrieval ─────┐
                     ├─→ RRF → Hybrid retrieval
BM25 retrieval ──────┘
                     ↓
Dense confidence check
     ├─ đủ tốt → dùng Hybrid
     └─ thấp → PageIndex fallback
                     ↓
Context formatting / reorder
                     ↓
LLM generation
                     ↓
Answer + citations + sources
                     ↓
Streamlit UI
                     ↓
Golden dataset + 4 metrics + A/B evaluation
```

## Deliverables bắt buộc

1. Repository chạy được từ máy sạch.
2. Tối thiểu **3 legal documents**.
3. Tối thiểu **5 bài viết/page** crawl từ web.
4. Dữ liệu được chuẩn hóa sang Markdown.
5. Chunking + embedding + ChromaDB.
6. Dense semantic search.
7. BM25 lexical search.
8. RRF fusion, chỉ fuse **một lần**.
9. Fallback dựa trên **dense cosine score gốc**, tuyệt đối không dùng RRF score để quyết định fallback.
10. PageIndex trả `retrieval_method="pageindex"`.
11. Generation có citation và safe refusal khi evidence không đủ.
12. Streamlit UI hiển thị answer + source + retrieval method + score.
13. Golden dataset tối thiểu 15 câu hỏi.
14. 4 metrics: faithfulness, answer relevance, context recall, context precision.
15. A/B: dense-only vs hybrid + RRF, giữ các biến còn lại giống nhau.
16. `reports/RESULT.md` hoàn chỉnh, không còn TODO.
17. Báo cáo cá nhân cho từng thành viên.
18. `pytest tests/test_contracts.py -q`, `pytest tests/test_acceptance.py -q`, `pytest -q` phải được chạy trước khi nộp.

---

# 2. Corpus được chốt cho đề tài

## 2.1. Legal documents — tối thiểu 3, nhóm dùng 4 để an toàn

| ID | Tài liệu | Vai trò trong corpus | Nguồn ưu tiên |
|---|---|---|---|
| LEGAL-01 | **Bộ luật Lao động 2019 — 45/2019/QH14** | Nguồn chính về hợp đồng lao động, thử việc, tiền lương, giờ làm, nghỉ phép, chấm dứt HĐLĐ | TVPL |
| LEGAL-02 | **Luật Bảo hiểm xã hội 2024 — 41/2024/QH15** | Nguồn chính về BHXH bắt buộc/tự nguyện, ốm đau, thai sản, hưu trí, tử tuất, đóng BHXH | TVPL |
| LEGAL-03 | **Nghị định 145/2020/NĐ-CP** | Hướng dẫn Bộ luật Lao động về điều kiện lao động và quan hệ lao động | TVPL |
| LEGAL-04 | **Nghị định 158/2025/NĐ-CP** | Hướng dẫn Luật BHXH 2024 về BHXH bắt buộc | TVPL; nếu trang TVPL khó crawl thì lấy văn bản gốc từ Cổng Chính phủ |

### URL đã xác minh

- Bộ luật Lao động 2019: `https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx`
- Luật BHXH 2024: `https://thuvienphapluat.vn/van-ban/Bao-hiem/Luat-Bao-hiem-xa-hoi-2024-557190.aspx`
- Nghị định 145/2020/NĐ-CP: `https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-145-2020-ND-CP-huong-dan-Bo-luat-Lao-dong-ve-dieu-kien-lao-dong-quan-he-lao-dong-459400.aspx`

> **Quy tắc:** Nếu TVPL cho phép lấy `Văn bản gốc/PDF`, ưu tiên lưu PDF/DOCX vào `data/landing/legal/`. Nếu chức năng tải bị giới hạn đăng nhập nhưng HTML toàn văn đọc được, có thể crawl HTML rồi lưu thành Markdown/HTML có metadata. Nếu bị WAF/chặn crawler, **không bypass WAF**; chuyển sang `vanban.chinhphu.vn` hoặc nguồn cơ quan nhà nước.

## 2.2. News / explanatory pages — tối thiểu 5

Mục đích của nhóm bài này là tạo câu hỏi thực tế, paraphrase và ngôn ngữ đời thường để hybrid retrieval có ý nghĩa hơn so với chỉ index văn bản luật.

| ID | Chủ đề bài viết cần crawl | Nguồn ưu tiên |
|---|---|---|
| NEWS-01 | Luật BHXH mới nhất / thời điểm Luật BHXH 2024 có hiệu lực | TVPL |
| NEWS-02 | BHXH tự nguyện theo Luật BHXH 2024 / NĐ 159/2025 | TVPL |
| NEWS-03 | Quyền/trách nhiệm người lao động tham gia BHXH | TVPL |
| NEWS-04 | Hợp đồng lao động / thử việc theo Bộ luật Lao động 2019 | TVPL |
| NEWS-05 | Tiền lương làm thêm giờ / giới hạn làm thêm giờ | TVPL |
| NEWS-06 (dự phòng) | Nghỉ việc riêng / nghỉ không hưởng lương | TVPL |
| NEWS-07 (dự phòng) | Chậm đóng, trốn đóng BHXH bắt buộc | TVPL |

### URL TVPL đã tìm được để đưa vào `ARTICLE_URLS`

1. `https://thuvienphapluat.vn/hoi-dap-phap-luat/839F306-hd-luat-bao-hiem-xa-hoi-moi-nhat-2024-va-cac-van-ban-huong-dan-hien-nay.html`
2. `https://thuvienphapluat.vn/hoi-dap-phap-luat/83A8D92-hd-toan-van-nghi-dinh-159-2025-nd-cp-huong-dan-thi-hanh-luat-bao-hiem-xa-hoi-ve-bao-hiem-xa-hoi-tu-ngu.html`
3. `https://thuvienphapluat.vn/lao-dong-tien-luong/viec-giai-quyet-cac-che-do-bao-hiem-xa-hoi-duoc-xac-dinh-nhu-the-nao-48959.html`
4. `https://thuvienphapluat.vn/lao-dong-tien-luong/hop-dong-lao-dong-la-su-thoa-thuan-giua-doi-tuong-nao-623718-22482.html`
5. `https://thuvienphapluat.vn/lao-dong-tien-luong/tien-luong-lam-them-gio-cua-nguoi-lao-dong-duoc-tinh-the-nao-3024.html`
6. `https://thuvienphapluat.vn/hoi-dap-phap-luat/83AA102-hd-toan-van-du-thao-nghi-dinh-huong-dan-luat-bao-hiem-xa-hoi-ve-cham-dong-tron-dong-bao-hiem-xa-hoi-ba.html`

> **Lưu ý corpus theo thời điểm hiện tại:** Luật BHXH 2024 đã có hiệu lực từ 01/07/2025. Không dùng Luật BHXH 2014 làm nguồn pháp lý chính cho câu trả lời hiện hành; chỉ giữ nếu muốn làm câu hỏi lịch sử/so sánh và phải gắn metadata rõ `historical=true`.

---

# 3. Chuẩn metadata ngay từ đầu

Mỗi document/chunk phải giữ được nguồn xuyên suốt pipeline.

```python
{
    "id": str,
    "content": str,
    "metadata": {
        "source": str,
        "title": str,
        "doc_type": "legal" | "news",
        "url": str | None,
        "chunk_index": int
    }
}
```

Đề xuất bổ sung metadata nội bộ (không làm hỏng contract):

```python
{
    "law_number": "41/2024/QH15",
    "effective_date": "2025-07-01",
    "domain": "social_insurance",
    "article_number": "Điều 2",
    "chapter": "Chương I",
    "source_priority": 1,
    "historical": False
}
```

**Lý do:** Với dữ liệu luật, citation chỉ ghi tên file là chưa đủ tốt. Nếu chunk giữ được `Điều`, `Chương`, `số hiệu`, UI có thể hiển thị nguồn rất thuyết phục khi demo.

---

# 4. Phân role tổng thể

## Phúc — Nhóm trưởng / Integration Owner / UI & Delivery

Phúc chịu trách nhiệm **điều phối, bảo vệ main branch, tích hợp end-to-end, UI, acceptance, README và nộp bài**. Phúc không được tự ý sửa module Sang/Phát đang sở hữu nếu chưa báo để tránh conflict.

Ownership chính:

- Setup repo/team workflow.
- `.env.example`, hướng dẫn chạy.
- Kiểm tra contract giữa module.
- Task 8 PageIndex/fallback provider wrapper (phần provider integration).
- `app.py` Streamlit.
- Acceptance testing.
- README cuối.
- Điều phối evaluation, tổng hợp `RESULT.md`.
- Review PR của Sang và Phát.
- Tag/release bản nộp.

## Sang — Core RAG Engineer / phần việc quan trọng nhất

Sang sở hữu **xương sống kỹ thuật của RAG** và các module có ảnh hưởng trực tiếp đến điểm retrieval/generation:

- Task 4: chunking + embedding + ChromaDB indexing.
- Task 5: semantic search.
- Task 7: RRF.
- Task 9: retrieval orchestration + threshold/fallback decision.
- Task 10: context reorder + format + generation + citation + safe refusal.
- Threshold calibration.
- A/B experiment logic.
- Debug các contract test kỹ thuật lõi.
- Bonus nếu còn thời gian: reranker hoặc query expansion/HyDE.

**Sang là người làm phần quan trọng nhất**, vì Task 4/5/7/9/10 quyết định phần lớn pipeline và trực tiếp bao phủ chunk/index, dense retrieval, fusion, fallback, generation/citation.

## Phát — Data Engineer / Lexical Retrieval / Evaluation Data

Phát sở hữu:

- Task 1: thu thập legal documents.
- Task 2: crawl ≥5 article.
- Task 3: chuẩn hóa Markdown + metadata.
- Task 6: BM25 lexical search.
- Data quality audit.
- Golden dataset ≥15 câu.
- Chạy evaluation theo harness do Sang/Phúc tích hợp.
- Failure table ban đầu cho `RESULT.md`.

---

# 5. THỨ TỰ THỰC HIỆN BẮT BUỘC — KHÔNG ĐƯỢC ĐẢO

## Phase A — Bootstrap

### A1 — Phúc làm trước

1. Fork/clone repo nhóm.
2. Tạo branch protection convention.
3. Tạo branches:

```bash
main
feat/phat-data-ingestion
feat/sang-core-rag
feat/phuc-integration-ui
feat/evaluation
```

4. Cài môi trường bằng `uv`:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
uv run playwright install chromium
cp .env.example .env
```

5. Chạy baseline:

```bash
uv run pytest tests/test_contracts.py -q
uv run pytest tests/test_acceptance.py -q
```

6. Ghi lại lỗi baseline do TODO — không cố sửa hết.
7. Chốt naming convention và thông báo cả nhóm.

### Commit A1 — Phúc

```text
chore: bootstrap team workflow and local environment
```

**Sau commit này Phát mới bắt đầu Task 1–3. Sang có thể đọc code nhưng chưa merge code core vào main cho đến khi schema data của Phát được chốt.**

---

# 6. PHÁT — HƯỚNG DẪN CỰC CHI TIẾT

## B1 — Task 1: Legal data collection

File sở hữu: `src/task1_collect_legal_docs.py`

### Việc phải làm

1. Tạo `data/landing/legal/`.
2. Lấy ít nhất 3 tài liệu pháp lý; mục tiêu nhóm là 4.
3. Ưu tiên TVPL.
4. Với mỗi tài liệu:
   - xác minh tiêu đề;
   - số hiệu;
   - ngày ban hành;
   - hiệu lực;
   - URL nguồn;
   - tên file không dấu.
5. Nếu tải được PDF/DOCX: lưu file gốc.
6. Nếu TVPL không cho tải nhưng trang toàn văn crawl được: lưu HTML/Markdown có metadata hoặc dùng nguồn chính phủ cho bản gốc.
7. Không bypass login/WAF.

### Tên file đề xuất

```text
data/landing/legal/
├── bo_luat_lao_dong_2019_45_2019_QH14.pdf
├── luat_bhxh_2024_41_2024_QH15.pdf
├── nghi_dinh_145_2020_ND_CP.pdf
└── nghi_dinh_158_2025_ND_CP.pdf
```

### Acceptance B1

```bash
find data/landing/legal -type f
```

Phải có ≥3 file hợp lệ, không phải HTML lỗi/login page giả PDF.

### Commit B1 — Phát

```text
data: collect labor and social insurance legal documents
```

---

## B2 — Task 2: Crawl ≥5 article

File sở hữu: `src/task2_crawl_news.py`

### Điền `ARTICLE_URLS`

Dùng 5 URL TVPL đã chốt ở mục 2.2; giữ URL thứ 6 làm dự phòng.

### `crawl_article()` bắt buộc trả

```python
{
    "url": url,
    "title": title,
    "date_crawled": datetime.now().isoformat(),
    "content_markdown": markdown
}
```

### Quy tắc crawl

- Mỗi URL → một JSON.
- Không lưu page chỉ có menu/login/banner mà thiếu nội dung chính.
- `content_markdown` không rỗng.
- Nên loại menu/header/footer nếu Crawl4AI hỗ trợ extraction.
- Nếu 1 URL TVPL fail: thử browser rendering của Crawl4AI.
- Nếu vẫn fail: thay bằng một page TVPL khác cùng chủ đề.
- Chỉ khi TVPL không có/không thể crawl mới dùng Cổng Chính phủ/BHXH Việt Nam.

### Output

```text
data/landing/news/
├── article_01.json
├── article_02.json
├── article_03.json
├── article_04.json
└── article_05.json
```

### Kiểm tra nhanh

```bash
python - <<'PY'
import json
from pathlib import Path
for p in Path('data/landing/news').glob('*.json'):
    d=json.loads(p.read_text(encoding='utf-8'))
    print(p.name, d['title'], len(d['content_markdown']))
PY
```

Mỗi bài nên có nội dung đáng kể; bài vài trăm ký tự thường là crawl lỗi.

### Commit B2 — Phát

```text
data: crawl labor and social insurance reference articles
```

---

## B3 — Task 3: Standardize Markdown

File sở hữu: `src/task3_convert_markdown.py`

### Legal

- Convert PDF/DOCX → `.md`.
- Không làm mất heading `Chương`, `Mục`, `Điều` nếu converter đọc được.
- Thêm YAML/frontmatter hoặc header metadata.

Ví dụ:

```markdown
---
title: "Luật Bảo hiểm xã hội 2024"
source: "luat_bhxh_2024_41_2024_QH15.pdf"
url: "https://..."
doc_type: "legal"
law_number: "41/2024/QH15"
effective_date: "2025-07-01"
---

# LUẬT BẢO HIỂM XÃ HỘI
...
```

### News

Header tối thiểu:

```markdown
# <title>

**Source:** <url>
**Crawled:** <iso datetime>

---

<content>
```

### Acceptance B3

```bash
find data/standardized -name '*.md' -type f
```

Phải có ≥8 Markdown (3 legal + 5 news; nếu dùng 4 legal thì ≥9).

Không file nào rỗng.

### Commit B3 — Phát

```text
feat: standardize legal corpus and articles to markdown
```

### HANDOFF 1

Sau B3, **Phát dừng sửa cấu trúc data** và báo Phúc + Sang. Phúc review metadata. Chỉ khi Phúc approve thì merge B1+B2+B3 vào main.

---

# 7. PHÚC — CHECKPOINT DATA GATE

## C1 — Review dữ liệu của Phát

Phúc kiểm:

- ≥3 legal.
- ≥5 news.
- Nguồn rõ ràng.
- URL có thật.
- Không trộn Luật BHXH 2014 như luật hiện hành.
- Markdown không rỗng.
- Không có API key.
- Không có nội dung crawl lỗi.

### Commit C1 — Phúc (nếu cần sửa docs/metadata nhỏ)

```text
docs: document corpus sources and data provenance
```

**Chỉ sau khi C1 xong, Sang bắt đầu commit Task 4 lên branch core.**

---

# 8. SANG — CORE RAG, PHẦN QUAN TRỌNG NHẤT

## D1 — Task 4: Load → Chunk → Embed → ChromaDB

File: `src/task4_chunking_indexing.py`

### `load_documents()`

- Đọc tất cả `.md` trong `data/standardized/`.
- ID ổn định bằng relative path.
- `doc_type` suy ra legal/news.
- Parse title/source/url từ frontmatter nếu có.
- Không dùng filename làm title nếu metadata có title tốt hơn.

### `chunk_documents()`

Baseline repo: `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`.

Với văn bản luật, Sang nên ưu tiên **structure-aware + recursive fallback**:

1. Split theo `Điều <số>.` nếu phát hiện legal doc.
2. Nếu một Điều quá dài → recursive splitter.
3. News → recursive splitter bình thường.
4. ID chunk ổn định:

```text
<document-id>::chunk-0000
```

5. `chunk_index` tăng từ 0.
6. Không chunk rỗng.
7. Giữ metadata nguồn.

### `embed_texts()`

Repo gợi ý `BAAI/bge-m3`, dimension 1024.

- Load model một lần, không load lại mỗi batch.
- Task 5 phải import chính hàm này.
- Batch embedding để tránh chậm.
- Nếu máy yếu, ghi rõ lựa chọn model khác trong report nhưng Task 4/5 phải đồng nhất.

### `get_collection()`

- Persistent Chroma.
- cosine space.
- collection `rag_documents`.

### `index_to_vectorstore()`

- `upsert`, không `add` để chạy lại không duplicate.
- ids/documents/embeddings/metadatas cùng length.

### Test bắt buộc

```bash
uv run pytest tests/test_contracts.py::test_chunk_documents_preserves_identity_and_metadata -q
```

### Commit D1 — Sang

```text
feat: implement structure-aware chunking embedding and chroma indexing
```

---

## D2 — Task 5: Dense semantic search

File: `src/task5_semantic_search.py`

Yêu cầu:

- Embed query bằng `task4.embed_texts()`.
- Query Chroma.
- Chroma cosine distance → similarity, ví dụ `1 - distance`.
- Trả đúng `SearchResult`.
- `retrieval_method="dense"`.
- unique ID.
- sort score giảm dần.
- không vượt `top_k`.

### Commit D2 — Sang

```text
feat: implement dense semantic retrieval with shared embeddings
```

---

# 9. PHÁT — Task 6 sau khi Task 4 schema đã ổn định

## E1 — BM25

File: `src/task6_lexical_search.py`

**Phát chỉ bắt đầu E1 sau khi Sang commit D1**, vì BM25 phải chạy trên cùng corpus chunk schema.

Yêu cầu:

- Corpus chính là chunks sau Task 4, không tự tạo schema khác.
- Tokenizer tiếng Việt tối thiểu normalize lowercase + whitespace/punctuation.
- Nếu không thêm tokenizer tiếng Việt chuyên biệt, ghi limitation trong report.
- `retrieval_method="bm25"`.
- score giảm dần.
- unique ID.

### Commit E1 — Phát

```text
feat: implement bm25 lexical retrieval on shared chunks
```

### HANDOFF 2

Phát gửi branch/commit cho Sang. Sang không copy code; merge/rebase rồi dùng output BM25 cho RRF.

---

# 10. SANG — RRF + RETRIEVAL ORCHESTRATION

## F1 — Task 7: RRF

File: `src/task7_reranking.py`

Công thức bắt buộc:

```text
RRF(d) = Σ 1 / (k + rank)
```

- rank bắt đầu từ 1.
- default `k=60`.
- deduplicate theo `id`.
- output `retrieval_method="hybrid"`.
- RRF chỉ fuse **một lần**.
- Không lấy dense score + BM25 score cộng trực tiếp vì scale khác nhau.

### Commit F1 — Sang

```text
feat: add reciprocal rank fusion for hybrid retrieval
```

---

## F2 — Task 9: Retrieval pipeline

File: `src/task9_retrieval_pipeline.py`

Logic chuẩn:

```python
dense = semantic_search(query, top_k=...)
bm25 = lexical_search(query, top_k=...)

best_dense_score = dense[0]["score"] if dense else 0.0

if best_dense_score < score_threshold:
    try:
        pageindex = pageindex_search(query, top_k=top_k)
        if pageindex:
            return pageindex
    except Exception:
        pass

if use_reranking:
    return rerank_rrf([dense, bm25], top_k=top_k)

return dense[:top_k]
```

### Điểm cực quan trọng

- Threshold so với **dense cosine similarity gốc**.
- Không threshold trên RRF.
- PageIndex lỗi → không crash.
- Nếu fallback lỗi, vẫn có thể trả hybrid.
- Không gọi RRF hai lần.

### Threshold calibration

Sang tạo tối thiểu:

**In-domain:**
- "Thời gian thử việc tối đa là bao lâu?"
- "Người lao động làm thêm ngày lễ được trả lương thế nào?"
- "Ai thuộc đối tượng tham gia BHXH bắt buộc?"
- "Điều kiện hưởng lương hưu theo Luật BHXH 2024 là gì?"

**Out-of-domain:**
- "Cách nấu phở bò?"
- "iPhone mới nhất giá bao nhiêu?"
- "Ai vô địch World Cup 2022?"
- "Cách học React?"

Ghi best dense score vào bảng, chọn threshold tách hai nhóm hợp lý nhất. Không chọn threshold bằng cảm tính.

### Commit F2 — Sang

```text
feat: orchestrate hybrid retrieval and calibrated fallback
```

---

# 11. PHÚC — Task 8 PageIndex provider

## G1 — PageIndex

File: `src/task8_pageindex_vectorless.py`

Phúc làm song song sau khi corpus chuẩn hóa xong, nhưng merge trước F2 hoặc phối hợp với Sang.

Yêu cầu:

- `pageindex_search(query, top_k=5)`.
- output đúng `SearchResult`.
- `retrieval_method="pageindex"`.
- provider/API lỗi phải catch được ở Task 9.
- Không hard-code key.

### Commit G1 — Phúc

```text
feat: implement pageindex fallback provider
```

**Thứ tự merge bắt buộc trước F2 hoàn chỉnh:** E1 (BM25) → F1 (RRF) → G1 (PageIndex) → F2 (retrieval pipeline).

---

# 12. SANG — Task 10 Generation + Citation

## H1 — `reorder_for_llm()`

- Không mutate list đầu vào.
- Không làm mất ID.
- Có thể dùng long-context reorder đơn giản nhưng phải giữ source mapping.

## H2 — `format_context()`

Mỗi chunk phải có marker rõ:

```text
[SOURCE 1]
Title: Luật Bảo hiểm xã hội 2024
Source: luat_bhxh_2024_41_2024_QH15.md
URL: ...
Content: ...
```

## H3 — `generate_with_citation()`

- Gọi `retrieve()`.
- Nếu không có evidence → safe refusal.
- Prompt LLM: chỉ trả lời từ context, không tự bịa điều luật.
- Citation trong answer phải map về `sources`.
- Output:

```python
{
    "answer": str,
    "sources": list[SearchResult],
    "retrieval_source": "hybrid" | "pageindex" | "none"
}
```

### Prompt hệ thống đề xuất

```text
Bạn là trợ lý tra cứu pháp luật lao động và bảo hiểm xã hội Việt Nam.
Chỉ trả lời dựa trên CONTEXT được cung cấp.
Không suy đoán điều luật, mức tiền, tỷ lệ, thời hạn hoặc điều kiện nếu context không nêu rõ.
Khi nêu kết luận pháp lý, trích dẫn nguồn theo dạng [1], [2] tương ứng với SOURCE trong context.
Nếu evidence không đủ hoặc câu hỏi ngoài phạm vi corpus, nói rõ rằng dữ liệu hiện có không đủ để kết luận.
Không thay thế tư vấn pháp lý chuyên nghiệp cho tình huống tranh chấp cụ thể.
```

### Commit H1 — Sang

```text
feat: generate grounded answers with citations and safe refusal
```

---

# 13. PHÚC — Streamlit UI + Integration

## I1 — `app.py`

UI tối thiểu:

- Title: `Labor & Social Insurance RAG Assistant`.
- Chat input.
- Answer.
- Expandable sources.
- Mỗi source hiển thị:
  - title;
  - source/file;
  - URL nếu có;
  - retrieval method;
  - score;
  - chunk index;
  - snippet.
- Hiển thị `retrieval_source`.
- Catch exception để UI không crash.

### Demo UI nên có 3 preset

1. **In-domain exact:** "Thời gian thử việc tối đa đối với công việc cần trình độ cao đẳng trở lên là bao lâu?"
2. **Cross-document:** "Người lao động theo hợp đồng từ 1 tháng trở lên có thuộc diện BHXH bắt buộc không?"
3. **Out-of-domain:** "Cách nấu bún bò Huế?"

### Commit I1 — Phúc

```text
feat: build streamlit chat ui with source inspection
```

---

# 14. PHÁT — Golden Dataset

## J1 — Tạo ≥15 Q&A

Khuyến nghị 20 câu để an toàn:

- 5 câu Bộ luật Lao động.
- 5 câu Luật BHXH 2024.
- 3 câu Nghị định hướng dẫn.
- 3 câu paraphrase đời thường.
- 2 câu cross-document.
- 2 câu out-of-domain/safe refusal.

### Ví dụ câu hỏi

1. Thời gian thử việc tối đa với vị trí yêu cầu trình độ cao đẳng trở lên?
2. Lương thử việc tối thiểu bằng bao nhiêu phần trăm lương công việc?
3. Người lao động làm thêm ngày thường được trả tối thiểu bao nhiêu?
4. Giới hạn làm thêm trong tháng là bao nhiêu giờ?
5. Người lao động kết hôn được nghỉ bao nhiêu ngày hưởng nguyên lương?
6. Luật BHXH 2024 có hiệu lực từ ngày nào?
7. Hợp đồng lao động từ bao nhiêu tháng thuộc diện BHXH bắt buộc?
8. BHXH bắt buộc gồm những chế độ nào?
9. BHXH tự nguyện gồm những chế độ nào?
10. Người từ đủ bao nhiêu tuổi có thể thuộc diện trợ cấp hưu trí xã hội theo điều kiện luật định?
11. Chủ hộ kinh doanh có thuộc diện BHXH bắt buộc không?
12. Nguyên tắc tính mức hưởng BHXH dựa trên yếu tố nào?
13. Trốn đóng BHXH có thể bị xử lý thế nào?
14. Tôi ký hợp đồng 6 tháng thì có phải tham gia BHXH không?
15. Công ty bắt tôi làm thêm nhưng không hỏi ý kiến có đúng không?
16. Làm ngày lễ thì tiền lương làm thêm được tính thế nào?
17. Quy định về thời gian nghỉ giữa giờ nằm ở đâu?
18. Nếu dense retrieval không tự tin thì hệ thống dùng cơ chế gì?
19. Ai vô địch World Cup 2022? *(out-of-domain)*
20. Cách nấu phở? *(out-of-domain)*

### Commit J1 — Phát

```text
test: add golden qa dataset for labor and social insurance corpus
```

---

# 15. EVALUATION — làm theo đúng thứ tự

## K1 — Sang chuẩn bị runner/config A-B

Config A:

```text
dense-only
```

Config B:

```text
dense + BM25 + RRF
```

Giữ giống nhau:

- golden dataset;
- generator model;
- evaluator model;
- prompt;
- `top_k`;
- corpus version;
- embedding model.

Chỉ thay retrieval strategy.

### Commit K1 — Sang

```text
test: add dense versus hybrid evaluation harness
```

## K2 — Phát chạy evaluation và điền raw results

4 metrics:

- Faithfulness.
- Answer relevance.
- Context recall.
- Context precision.

Phát điền:

- overall score;
- delta B-A;
- 3 worst performers;
- failure stage;
- root cause.

### Commit K2 — Phát

```text
docs: record rag evaluation metrics and failure cases
```

## K3 — Phúc + Sang review interpretation

Phúc chịu trách nhiệm wording báo cáo; Sang xác nhận kết luận kỹ thuật có đúng với số liệu.

### Commit K3 — Phúc

```text
docs: finalize ab analysis and retrieval recommendations
```

---

# 16. TEST GATE — Phúc điều phối, cả nhóm phải có mặt

Chạy đúng thứ tự:

```bash
uv run pytest tests/test_contracts.py -q
uv run pytest tests/test_acceptance.py -q
uv run pytest -q
```

Sau đó:

```bash
uv run python -m src.task1_collect_legal_docs
uv run python -m src.task2_crawl_news
uv run python -m src.task3_convert_markdown
uv run python -m src.task4_chunking_indexing
uv run streamlit run app.py
```

### Test manual bắt buộc

| Test | Kỳ vọng |
|---|---|
| Query đúng Bộ luật Lao động | Answer đúng + citation |
| Query đúng BHXH | Answer đúng + citation |
| Query paraphrase | Hybrid tìm được evidence |
| Query có từ khóa chính xác | BM25 đóng góp chunk tốt |
| Query ngoài domain | PageIndex hoặc safe refusal, không bịa |
| PageIndex lỗi giả lập | UI không crash |
| Chạy index lần 2 | Không duplicate chunks |
| Citation | Map đúng source/chunk |

### Commit L1 — Phúc

```text
test: verify end to end rag acceptance flow
```

---

# 17. README + REPORT + NỘP BÀI

## Phúc

README phải có:

1. Problem statement.
2. Corpus/source list.
3. Architecture.
4. Setup bằng `uv`.
5. `.env` variables.
6. Cách chạy data pipeline.
7. Cách index.
8. Cách chạy Streamlit.
9. Cách chạy tests.
10. Evaluation summary.
11. Known limitations.
12. Team contribution table.

### Commit M1 — Phúc

```text
docs: finalize reproducible setup and team handoff
```

## Báo cáo cá nhân

### Phúc

Kê:
- integration;
- PageIndex;
- Streamlit;
- acceptance tests;
- README;
- review/evaluation synthesis.

Commit:

```text
docs: add phuc individual contribution report
```

### Sang

Kê:
- chunking/indexing;
- embedding;
- dense retrieval;
- RRF;
- retrieval pipeline;
- threshold calibration;
- generation/citation;
- A/B harness.

Commit:

```text
docs: add sang individual contribution report
```

### Phát

Kê:
- legal collection;
- crawling;
- Markdown standardization;
- BM25;
- golden dataset;
- evaluation run/failure analysis.

Commit:

```text
docs: add phat individual contribution report
```

---

# 18. TOÀN BỘ THỨ TỰ COMMIT — PHẢI TUÂN THỦ

> Hash thực tế sẽ khác; đây là **thứ tự logic bắt buộc**.

| # | Người | Commit message | Phụ thuộc |
|---:|---|---|---|
| 01 | Phúc | `chore: bootstrap team workflow and local environment` | Bắt đầu |
| 02 | Phát | `data: collect labor and social insurance legal documents` | #01 |
| 03 | Phát | `data: crawl labor and social insurance reference articles` | #02 |
| 04 | Phát | `feat: standardize legal corpus and articles to markdown` | #03 |
| 05 | Phúc | `docs: document corpus sources and data provenance` | #04 |
| 06 | Sang | `feat: implement structure-aware chunking embedding and chroma indexing` | #05 |
| 07 | Sang | `feat: implement dense semantic retrieval with shared embeddings` | #06 |
| 08 | Phát | `feat: implement bm25 lexical retrieval on shared chunks` | #06 |
| 09 | Sang | `feat: add reciprocal rank fusion for hybrid retrieval` | #07 + #08 |
| 10 | Phúc | `feat: implement pageindex fallback provider` | #05 |
| 11 | Sang | `feat: orchestrate hybrid retrieval and calibrated fallback` | #09 + #10 |
| 12 | Sang | `feat: generate grounded answers with citations and safe refusal` | #11 |
| 13 | Phúc | `feat: build streamlit chat ui with source inspection` | #12 |
| 14 | Phát | `test: add golden qa dataset for labor and social insurance corpus` | #04 |
| 15 | Sang | `test: add dense versus hybrid evaluation harness` | #12 + #14 |
| 16 | Phát | `docs: record rag evaluation metrics and failure cases` | #15 |
| 17 | Phúc | `docs: finalize ab analysis and retrieval recommendations` | #16 |
| 18 | Phúc | `test: verify end to end rag acceptance flow` | #13 + #17 |
| 19 | Phúc | `docs: finalize reproducible setup and team handoff` | #18 |
| 20 | Phát | `docs: add phat individual contribution report` | #19 |
| 21 | Sang | `docs: add sang individual contribution report` | #19 |
| 22 | Phúc | `docs: add phuc individual contribution report` | #19 |
| 23 | Phúc | `chore: prepare final submission release` | #20-22 |

---

# 19. Quy tắc Git để không phá repo nhóm

## Mỗi người trước khi làm

```bash
git checkout main
git pull origin main
git checkout <branch-cua-minh>
git rebase main
```

## Trước khi push

```bash
git status
git diff
uv run pytest -q
git add <dung-file-minh-lam>
git commit -m "<message-da-chot>"
git push origin <branch>
```

## Không được làm

```text
❌ git add . mà không kiểm tra
❌ commit .env
❌ commit API key
❌ force push main
❌ sửa cùng lúc cùng file với người khác
❌ merge branch đang fail test
❌ đổi public function signature trong MODULE_CONTRACTS
❌ sửa test để “né” lỗi implementation
```

---

# 20. Checkpoint theo timeline 3 giờ của bài

## Checkpoint 0 — phút 0–10: Setup

Owner: **Phúc**

Done khi:
- môi trường chạy;
- dependency cài;
- `.env` có local key nhưng không tracked;
- baseline tests đã chạy;
- branches tạo xong.

## Checkpoint 1 — phút 10–35: Data

Owner: **Phát**; review: **Phúc**

Done khi:
- ≥3 legal;
- ≥5 news;
- Markdown chuẩn;
- provenance rõ.

## Checkpoint 2 — phút 35–65: Index & Search

Owner chính: **Sang**; BM25: **Phát**

Done khi:
- chunk IDs ổn định;
- embeddings chạy;
- Chroma upsert;
- dense search chạy;
- BM25 chạy.

## Checkpoint 3 — phút 65–90: Fusion & Fallback

Owner chính: **Sang**; PageIndex: **Phúc**

Done khi:
- RRF đúng công thức;
- fuse một lần;
- threshold dùng dense score;
- PageIndex fail không crash.

## Checkpoint 4 — phút 90–120: Generation & UI

Generation: **Sang**; UI: **Phúc**

Done khi:
- answer grounded;
- citation map đúng;
- safe refusal;
- Streamlit hiển thị source/method/score.

## Checkpoint 5 — phút 120–150: Evaluation

Golden + run: **Phát**; harness: **Sang**; review: **Phúc**

Done khi:
- ≥15 Q&A;
- 4 metrics;
- dense vs hybrid A/B;
- worst performers;
- recommendations.

## Checkpoint 6 — phút 150–180: Demo & Handoff

Owner: **Phúc**, cả nhóm cùng verify.

Done khi:
- all tests pass;
- README hoàn chỉnh;
- reports đủ;
- demo 1 in-domain + 1 paraphrase + 1 out-of-domain;
- repo sạch;
- push/tag final.

---

# 21. Definition of Done theo từng người

## Phúc DONE khi

- main branch tích hợp sạch.
- PageIndex wrapper hoạt động hoặc fail gracefully.
- Streamlit không crash.
- source/method/score hiển thị.
- acceptance + full test được chạy.
- README và RESULT hoàn chỉnh.
- 3 individual reports tồn tại.
- final submission release tạo xong.

## Sang DONE khi

- Task 4/5/7/9/10 đúng contract.
- Chroma idempotent.
- Dense score hợp lý.
- RRF đúng rank.
- Fallback dùng dense score.
- Citation map đúng source.
- Safe refusal hoạt động.
- Threshold có calibration evidence.
- A/B harness tái chạy được.

## Phát DONE khi

- ≥3 legal, ≥5 articles.
- data source rõ ràng.
- Markdown sạch.
- BM25 đúng contract.
- golden ≥15 câu, khuyến nghị 20.
- evaluation raw results đầy đủ.
- failure cases có root cause.

---

# 22. Bonus — chỉ làm sau khi core đạt 90 điểm

Ưu tiên bonus theo thứ tự:

1. **Reranker** (Sang) — Jina/BGE reranker, chỉ giữ nếu A/B chứng minh cải thiện.
2. **HyDE/query expansion** (Sang) — phải đo delta metric.
3. **UI source highlighting** (Phúc) — highlight đoạn evidence.
4. **Conversation memory** (Phúc/Sang) — follow-up question.

Không làm bonus trước khi:

```text
[ ] all core tests pass
[ ] citation đúng
[ ] evaluation core xong
[ ] RESULT.md không TODO
[ ] README chạy lại được
```

---

# 23. Các lỗi dễ mất điểm nhất

1. Dùng Luật BHXH 2014 làm luật hiện hành trong corpus mà không đánh dấu historical.
2. Crawl được URL nhưng content thực tế chỉ là login/menu.
3. Chunk mất metadata nguồn.
4. Task 4 và Task 5 dùng hai embedding model khác nhau.
5. Chroma dùng `add` khiến chạy lại duplicate.
6. BM25 tự tạo IDs khác dense → RRF không fuse đúng document.
7. RRF cộng raw dense/BM25 score thay vì rank.
8. Threshold dùng RRF score.
9. PageIndex exception làm Streamlit crash.
10. Citation `[1]` nhưng `sources[0]` không phải evidence tương ứng.
11. LLM trả lời ngoài context.
12. A/B thay nhiều biến cùng lúc → kết quả không chứng minh hybrid tốt hơn.
13. Golden dataset quá dễ hoặc copy nguyên câu chữ trong luật.
14. `RESULT.md` còn TODO.
15. Commit một cục cuối cùng khiến individual contribution khó chứng minh.

---

# 24. Checklist trước khi Phúc bấm nộp

```text
DATA
[ ] >= 3 legal docs
[ ] >= 5 crawled pages
[ ] TVPL ưu tiên
[ ] URL/source metadata đầy đủ
[ ] Luật BHXH 2024 là nguồn hiện hành chính
[ ] Markdown không rỗng

RETRIEVAL
[ ] stable chunk IDs
[ ] chunk_index đầy đủ
[ ] same embedding model Task 4/5
[ ] Chroma cosine
[ ] dense sorted descending
[ ] BM25 sorted descending
[ ] RRF rank starts at 1
[ ] RRF only once
[ ] fallback uses raw dense cosine similarity
[ ] PageIndex error safe

GENERATION
[ ] context has title/source
[ ] citation maps to sources
[ ] safe refusal works
[ ] no unsupported legal claims

UI
[ ] answer visible
[ ] sources visible
[ ] retrieval method visible
[ ] score visible
[ ] out-of-domain does not hallucinate

EVALUATION
[ ] >= 15 golden Q&A
[ ] faithfulness
[ ] answer relevance
[ ] context recall
[ ] context precision
[ ] dense-only baseline
[ ] hybrid + RRF comparison
[ ] 3 worst cases
[ ] root cause analysis
[ ] recommendations

SUBMISSION
[ ] contract tests pass
[ ] acceptance tests pass
[ ] full pytest pass
[ ] README complete
[ ] RESULT.md no TODO
[ ] Phúc report
[ ] Sang report
[ ] Phát report
[ ] .env ignored
[ ] no API keys
[ ] no cache/temporary secrets
[ ] final commit/tag pushed
```

---

# 25. Chốt ownership ngắn gọn

```text
PHÁT
Data → Crawl → Markdown → BM25 → Golden dataset → Evaluation raw results

                ↓ handoff

SANG
Chunk/Embed/Index → Dense → RRF → Retrieval/Fallback → Generation/Citation → A/B harness

                ↓ handoff

PHÚC
Review/Integrate → PageIndex provider → Streamlit → Acceptance → README/RESULT → Final submission
```

**Không đổi ownership giữa chừng trừ khi nhóm trưởng Phúc ghi rõ trong PR/issue. Sang giữ ownership các module core quan trọng nhất; Phúc giữ quyền merge và final acceptance; Phát giữ data provenance và evaluation dataset.**
