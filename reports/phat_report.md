# Individual Contribution Report — Nguyễn Tấn Phát

## Thông tin

- **Họ và tên:** Nguyễn Tấn Phát
- **Mã học viên:** AI20K-PHAT-03
- **Nhóm:** Nhóm 3 thành viên (Phúc · Sang · Phát)
- **Vai trò:** Data Engineer / Lexical Retrieval / Evaluation Data
- **Repository / Branch:** `NguyenDinhLamPhuc/K4-L3B-RAG-Pipeline-3Ironman` / `feat/phat-data-ingestion`

---

## Phần việc đã thực hiện

| Module / Deliverable | Việc tôi trực tiếp làm | File / Commit / PR | Trạng thái |
|---|---|---|:---:|
| **Task 1: Thu thập tài liệu pháp lý** | Thu thập 4 văn bản luật gốc từ TVPL và Cổng TTĐT Chính phủ (BLLĐ 2019, Luật BHXH 2024, NĐ 145/2020, NĐ 158/2025) | `data/landing/legal/`, `src/task1_collect_legal_docs.py` | Done |
| **Task 2: Crawl bài viết tham chiếu** | Crawl 5 bài viết giải thích và hướng dẫn pháp luật lưu dưới định dạng JSON đầy đủ metadata | `data/landing/news/`, `src/task2_crawl_news.py` | Done |
| **Task 3: Chuẩn hóa Markdown** | Chuyển đổi toàn bộ tài liệu sang Markdown, gắn YAML frontmatter chuẩn (`source`, `title`, `law_number`, `url`,...) | `data/standardized/`, `src/task3_convert_markdown.py` | Done |
| **Task 6: BM25 Lexical Search** | Xây dựng bộ tách từ và thuật toán tìm kiếm từ khóa BM25 trên tập chunks chuẩn hóa | `src/task6_lexical_search.py` | Done |
| **Golden Dataset** | Biên soạn bộ 20 câu hỏi - đáp - ngữ cảnh căn cứ chuẩn xác theo văn bản quy phạm pháp luật | `group_project/evaluation/golden_dataset.json` | Done |
| **Data Quality Audit** | Kiểm tra tính toàn vẹn, kích thước và không rỗng của 9 tài liệu trong manifest | `data/standardized/manifest.json`, `tests/test_acceptance.py` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Chọn Luật Bảo hiểm xã hội 2024 (số hiệu 41/2024/QH15) làm nguồn pháp lý hiện hành chính thức, không đưa Luật BHXH 2014 vào làm nguồn chính.  
   **Lý do/evidence:** Luật BHXH 2024 đã được thông qua và có hiệu lực thi hành từ ngày 01/07/2025 với rất nhiều điểm mới cốt lõi (như trợ cấp hưu trí xã hội, giảm số năm đóng BHXH tối thiểu để hưởng lương hưu, mức tham chiếu thay lương cơ sở). Đưa luật cũ vào sẽ gây mâu thuẫn tri thức nghiêm trọng cho chatbot.  
   **Trade-off:** Dữ liệu mới cần nguồn trích dẫn đối chiếu kỹ lưỡng hơn, nhưng đảm bảo giá trị thực tiễn và tính chính xác lâu dài của sản phẩm.

2. **Quyết định:** Thiết kế bộ Golden Dataset bao phủ cả 4 dạng câu hỏi: câu hỏi luật trực tiếp, câu hỏi paraphrase, câu hỏi liên kết văn bản (cross-document) và câu hỏi ngoài phạm vi (out-of-domain).  
   **Lý do/evidence:** Nếu bộ kiểm thử chỉ gồm các câu hỏi sao chép nguyên văn điều luật, điểm số sẽ cao giả tạo và không đo lường được khả năng chịu lỗi và tính an toàn của hệ thống.  
   **Trade-off:** Mất nhiều thời gian biên soạn ngữ cảnh và đáp án chuẩn hơn, nhưng giúp đo đạc khách quan và phát hiện chính xác các trường hợp worst performers.

---

## Kiểm thử và kết quả

- **Test đã chạy:**
  - `test_acceptance.py::test_corpus_has_required_legal_documents`: 4/4 legal docs pass.
  - `test_acceptance.py::test_corpus_has_required_news_with_metadata`: 5/5 news articles pass.
  - `test_acceptance.py::test_standardized_output_covers_both_source_types`: 9/9 files Markdown pass.
  - `test_acceptance.py::test_golden_dataset_has_15_grounded_cases`: 20/20 grounded cases pass.
- **Kết quả BM25:**
  - Tìm kiếm chính xác các cụm từ khó: *"nghỉ việc riêng hưởng nguyên lương"*, *"mức tham chiếu"*, *"40 giờ trong 01 tháng"*.

---

## Điều còn hạn chế

- **Hạn chế:** Bộ tách từ tiếng Việt của BM25 hiện tại tách theo khoảng trắng và ký tự phân cách, chưa dùng mô hình từ điển ghép từ (compound words).
- **Hướng cải tiến nếu có thêm thời gian:** Tích hợp bộ thư viện `pyvi` hoặc `underthesea` để tách từ ghép tiếng Việt chuẩn xác hơn cho BM25.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 2026-09-25
- **Tên thành viên:** Nguyễn Tấn Phát
