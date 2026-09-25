# Chatbot Tra Cứu Bộ Luật Lao Động & Luật Bảo Hiểm Xã Hội Việt Nam (RAG Pipeline)

> **Dự án Day 8 — Xây dựng và đánh giá hệ thống RAG Pipeline hoàn chỉnh (End-to-End)**  
> **Nhóm thực hiện:** Nhóm 3 thành viên — Phúc (Nhóm trưởng) · Sang · Phát  
> **Repository:** `NguyenDinhLamPhuc/K4-L3B-RAG-Pipeline-3Ironman`

---

## 1. Giới thiệu bài toán (Problem Statement)

Hệ thống văn bản quy phạm pháp luật tại Việt Nam, đặc biệt là **Bộ luật Lao động 2019** và **Luật Bảo hiểm xã hội 2024** (có hiệu lực từ 01/07/2025), có khối lượng thông tin lớn, tính liên kết điều khoản phức tạp và thường xuyên được hướng dẫn bởi các Nghị định chuyên ngành. Người lao động và doanh nghiệp thường gặp khó khăn khi tra cứu các chế độ thử việc, tiền lương làm thêm giờ, hợp đồng lao động, ốm đau, thai sản, trợ cấp hưu trí.

Dự án này xây dựng một **Trợ lý RAG thông minh** có khả năng:
- Truy xuất kết hợp đa phương thức (**Hybrid Retrieval**: Dense Semantic Search + Lexical BM25).
- Tự động dung hợp thứ hạng bằng thuật toán **Reciprocal Rank Fusion (RRF)**.
- Kiểm tra ngưỡng tự tin cosine để kích hoạt cơ chế **Vectorless Fallback (PageIndex)** hoặc **Safe Refusal** khi câu hỏi ngoài phạm vi.
- Sinh câu trả lời có kèm căn cứ trích dẫn chính xác (**Citations**) theo từng điều luật cụ thể.

---

## 2. Kiến trúc hệ thống (Architecture)

```text
               [Người dùng nhập câu hỏi]
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
   [Dense Search]                   [Lexical BM25]
 (ChromaDB + Cosine)             (RobustBM25Okapi Lucene)
         │                                 │
         └────────────────┬────────────────┘
                          ▼
            [Reciprocal Rank Fusion (RRF)]
                          │
                [Kiểm tra Dense Score]
                 /                  \
   (Score >= 0.35)                  (Score < 0.35)
         │                                 │
         ▼                                 ▼
 [Top-k Hybrid Chunks]            [PageIndex Fallback]
         │                                 │
         └────────────────┬────────────────┘
                          ▼
             [Lost-in-the-middle Reorder]
                          │
                          ▼
             [LLM Generation (Gemini)]
                          │
                          ▼
         [Answer + Citations + Sources Check]
                          │
                          ▼
               [Giao diện Streamlit UI]
```

---

## 3. Ngữ liệu dữ liệu (Corpus & Data Provenance)

Hệ thống thu thập và chuẩn hóa dữ liệu từ nguồn chính thống (**Thư Viện Pháp Luật** và **Cổng Thông tin điện tử Chính phủ**):

### 3.1. Văn bản pháp luật (4 văn bản — `data/standardized/legal/`)
1. **Bộ luật Lao động 2019** (Số hiệu: `45/2019/QH14` - Nguồn: Cổng TTĐT Chính phủ / TVPL).
2. **Luật Bảo hiểm xã hội 2024** (Số hiệu: `41/2024/QH15` - Có hiệu lực thi hành từ 01/07/2025).
3. **Nghị định 145/2020/NĐ-CP** (Quy định chi tiết điều kiện lao động và quan hệ lao động).
4. **Nghị định 158/2025/NĐ-CP** (Quy định chi tiết một số điều của Luật BHXH về BHXH bắt buộc).

### 3.2. Bài viết phân tích & hướng dẫn (5 bài viết — `data/standardized/news/`)
1. *14 nội dung trọng tâm của Luật Bảo hiểm xã hội 2024 và thời điểm có hiệu lực*.
2. *Hướng dẫn chi tiết chính sách Bảo hiểm xã hội tự nguyện theo quy định mới*.
3. *Quyền và trách nhiệm của người lao động khi tham gia giải quyết các chế độ BHXH*.
4. *Nội dung của hợp đồng lao động và hợp đồng làm việc theo Bộ luật Lao động 2019*.
5. *Cách tính tiền lương làm thêm giờ của người lao động vào ban đêm, ngày lễ, ngày nghỉ tuần*.

---

## 4. Hướng dẫn cài đặt & Chạy từ máy sạch (Quickstart)

### 4.1. Cài đặt môi trường

```bash
# Tạo môi trường ảo
python -m venv .venv
source .venv/bin/activate       # Trên Windows: .venv\Scripts\activate

# Cài đặt dependencies
pip install -e ".[dev]"
```

### 4.2. Cấu hình file `.env`

Sao chép file `.env.example` thành `.env` và điền cấu hình:

```env
# LLM Provider: gemini | openai | anthropic
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_api_key_here

# Embedding: sentence_transformers | gemini | openai
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=keepitreal/vietnamese-sbert    # hoặc BAAI/bge-m3

# Ngưỡng cosine fallback
SCORE_THRESHOLD=0.35
```

### 4.3. Chạy Pipeline dữ liệu & Đánh chỉ mục

```bash
# 1. Thu thập dữ liệu
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news

# 2. Chuẩn hóa Markdown
python -m src.task3_convert_markdown

# 3. Phân đoạn và đánh chỉ mục ChromaDB
python -m src.task4_chunking_indexing
```

### 4.4. Khởi chạy Chatbot giao diện Streamlit

```bash
streamlit run app.py
```
Ứng dụng sẽ mở tại địa chỉ `http://localhost:8501`.

---

## 5. Kiểm thử hệ thống (Test Execution)

Dự án tuân thủ nghiêm ngặt chuẩn hợp đồng (**Contract-driven Development**):

```bash
# 1. Chạy kiểm tra Contracts
pytest tests/test_contracts.py -v

# 2. Chạy kiểm tra Acceptance
pytest tests/test_acceptance.py -v

# 3. Chạy toàn bộ 40 tests trong dự án
pytest -v
```
*(Kết quả hiện tại: **40/40 tests PASSED 100%**).*

---

## 6. Tóm tắt kết quả đánh giá (Evaluation Summary)

Thực nghiệm đánh giá theo khung chuẩn **Ragas** trên tập Golden Dataset 20 câu hỏi:

| Tiêu chuẩn đo lường (Metric) | Config A (Dense-only) | Config B (Hybrid + RRF) | Chênh lệch (Delta B−A) |
|---|:---:|:---:|:---:|
| **Faithfulness** (Tính trung thực) | 0.835 | **0.945** | **+0.110** |
| **Answer Relevance** (Độ liên quan câu trả lời) | 0.860 | **0.935** | **+0.075** |
| **Context Recall** (Độ bao phủ ngữ cảnh) | 0.790 | **0.915** | **+0.125** |
| **Context Precision** (Độ chuẩn xác ngữ cảnh) | 0.805 | **0.900** | **+0.095** |
| **Điểm trung bình (Average)** | **0.822** | **0.924** | **+0.102 (+10.2%)** |

> Chi tiết phân tích nguyên nhân lỗi (Worst performers) và khuyến nghị cải tiến được trình bày đầy đủ tại [group_project/evaluation/RESULT.md](group_project/evaluation/RESULT.md).

---

## 7. Phân công vai trò & Đóng góp thành viên (Team Contributions)

| Thành viên | Vai trò | Nhiệm vụ chính phụ trách | Báo cáo chi tiết |
|---|---|---|:---:|
| **Nguyễn Đình Lâm Phúc** | Nhóm trưởng / UI & Delivery | Điều phối workflow, PageIndex fallback provider (Task 8), Streamlit UI (`app.py`), tổng hợp đánh giá và test gate | [phuc_report.md](reports/phuc_report.md) |
| **Nguyễn Minh Sang** | Core RAG Engineer | Chunking & Chroma indexing (Task 4), Dense search (Task 5), RRF Fusion (Task 7), Retrieval pipeline (Task 9), Generation & Citations (Task 10) | [sang_report.md](reports/sang_report.md) |
| **Nguyễn Tấn Phát** | Data Engineer & Evaluation | Thu thập văn bản luật (Task 1), crawl bài viết (Task 2), chuẩn hóa Markdown (Task 3), BM25 Lexical (Task 6), Golden dataset 20 câu | [phat_report.md](reports/phat_report.md) |
