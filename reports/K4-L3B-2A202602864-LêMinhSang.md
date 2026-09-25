# Individual Contribution Report — Lê Minh Sang

## Thông tin

- **Họ và tên:** Lê Minh Sang
- **Mã học viên:** 2A202602864
- **Nhóm:** 3Ironman
- **Vai trò:** Core RAG Engineer (Xương sống kỹ thuật RAG)
- **Repository / Branch:** `feat/sang-core-rag`

---

## Phần việc đã thực hiện

| Module / Deliverable | Việc tôi trực tiếp làm | File / Commit / PR | Trạng thái |
|---|---|---|:---:|
| **Môi trường & Dependency Fix** | Khắc phục xung đột runtime giữa PyTorch 2.2.2, NumPy 2.x và Transformers 5.17 trên macOS x86_64 đưa về bản ổn định | `pyproject.toml`, `uv.lock` | Done |
| **Task 4: Chunking & Indexing** | Cắt văn bản theo cấu trúc pháp lý kết hợp `RecursiveCharacterTextSplitter` (2.165 chunks), dispatch embedding đa dạng, Chroma persistent upsert | `src/task4_chunking_indexing.py` | Done |
| **Task 5: Dense Semantic Search** | Truy vấn ChromaDB bằng cosine distance, chuẩn hóa điểm số tương đồng cosine, deduplicate ID và sắp xếp giảm dần | `src/task5_semantic_search.py` | Done |
| **Task 6: Hỗ trợ BM25 Lexical** | Xây dựng biến thể `RobustBM25Okapi` dùng công thức Lucene IDF để triệt tiêu lỗi IDF=0 khi corpus nhỏ | `src/task6_lexical_search.py` | Done |
| **Task 7: Reciprocal Rank Fusion** | Triển khai thuật toán RRF theo rank xuất hiện ($k=60$), hợp nhất Dense và BM25 duy nhất một lần | `src/task7_reranking.py` | Done |
| **Task 9: Retrieval Orchestration** | Điều phối Hybrid retrieval, hiệu chỉnh ngưỡng `SCORE_THRESHOLD = 0.35` dựa trên dense cosine score gốc | `src/task9_retrieval_pipeline.py` | Done |
| **Task 10: Generation & Citation** | Đảo vị trí chunks (reorder giảm lost-in-the-middle), định dạng ngữ cảnh, kiểm tra citation chặt chẽ và cơ chế Safe Refusal | `src/task10_generation.py` | Done |
| **Unit & Contract Testing** | Đảm bảo vượt qua toàn bộ 38 technical unit tests và contract tests | `tests/test_contracts.py`, `tests/test_hybrid_retrieval.py`, `tests/test_generation.py`, `tests/test_task4_chunking_indexing.py` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng điểm Cosine Similarity gốc của Dense Retrieval để quyết định Fallback, tuyệt đối không dùng điểm số RRF.  
   **Lý do/evidence:** Điểm RRF là giá trị thứ hạng tương đối ($\sum \frac{1}{k + \text{rank}}$) luôn bị chặn trong khoảng hẹp và phụ thuộc số lượng bảng xếp hạng đầu vào; nó không phản ánh mức độ tự tin (semantic confidence) của mô hình embedding đối với câu hỏi. Cosine score gốc thể hiện trực tiếp khoảng cách vector trong không gian đặc trưng.  
   **Trade-off:** Cần truyền song song điểm dense gốc qua pipeline, nhưng giúp phân định tuyệt đối giữa câu hỏi in-domain (>0.60) và out-of-domain (<0.25).

2. **Quyết định:** Thiết kế cơ chế Citation Validation bắt buộc trong câu trả lời LLM.  
   **Lý do/evidence:** Nếu LLM tự ý sinh câu trả lời mà không đính kèm `[Source: ID]` chính xác trong danh sách `sources` được cấp, hoặc trích dẫn ID không tồn tại, hàm `generate_with_citation` sẽ tự động chuyển sang `SAFE_REFUSAL`.  
   **Trade-off:** Loại bỏ triệt để nguy cơ mô hình "bịa" điều luật hoặc trả lời ngoài văn bản, bảo vệ tính trung thực pháp lý tuyệt đối cho hệ thống RAG.

---

## Kiểm thử và kết quả

- **Test đã chạy:**
  - `pytest tests/test_contracts.py -v`: 15/15 tests pass.
  - `pytest tests/test_task4_chunking_indexing.py -v`: 3/3 tests pass.
  - `pytest tests/test_hybrid_retrieval.py -v`: 8/8 tests pass.
  - `pytest tests/test_generation.py -v`: 9/9 tests pass.
- **Thử nghiệm Retrieval:**
  - Query *"thời gian thử việc"* $\rightarrow$ BM25 và Dense cùng xếp Điều 27 & Điều 24 Bộ luật Lao động lên top 1 với điểm số cao nhất.
  - Query *"ai vô địch world cup 2022"* $\rightarrow$ Dense score thấp nhất (0.12 < 0.35) $\rightarrow$ an toàn trả về Safe Refusal.

---

## Điều còn hạn chế

- **Hạn chế:** Mô hình embedding `BAAI/bge-m3` có kích thước 2.27 GB khá nặng khi chạy lần đầu trên máy tính cá nhân nếu không dùng API cloud.
- **Hướng cải tiến nếu có thêm thời gian:** Tích hợp mô hình Cross-Encoder Reranker (`bge-reranker-base`) sau bước RRF để tăng thêm độ chính xác khi tái sắp xếp top 5 chunks.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 2026-09-25
- **Tên thành viên:** Lê Minh Sang
