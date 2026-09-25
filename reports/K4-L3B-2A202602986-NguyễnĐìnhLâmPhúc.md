# Individual Contribution Report — Nguyễn Đình Lâm Phúc

## Thông tin

- **Họ và tên:** Nguyễn Đình Lâm Phúc
- **Mã học viên:** 2A202602986
- **Nhóm:** 3Ironman
- **Repository/branch:** `feat/phuc-integration-ui` / `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Setup & Team Workflow | Thiết lập repository nhóm, quản lý branches, cấu hình môi trường uv, .env.example, điều phối phân công 3 thành viên | `KE_HOACH_DAY8_RAG_3_THANH_VIEN.md`, `.env.example` | Done |
| Data Quality Gate | Kiểm duyệt dữ liệu crawl và chuẩn hóa của Phát (4 văn bản luật, 5 bài viết), xác thực metadata, provenance và manifest | `data/standardized/manifest.json` | Done |
| Task 8: PageIndex Fallback | Xây dựng PageIndex vectorless fallback provider, chuyển đổi sang PDF tạm, upload, truy vấn node, xử lý timeout và ngoại lệ an toàn | `src/task8_pageindex_vectorless.py` | Done |
| Streamlit Chatbot UI | Thiết kế giao diện ứng dụng Streamlit hoàn chỉnh, hiển thị câu trả lời, nguồn trích dẫn, điểm score, phương thức truy xuất và câu hỏi mẫu | `app.py` | Done |
| Evaluation Synthesis | Tổng hợp kết quả đánh giá 4 metrics từ Ragas, phân tích A/B comparison giữa Dense-only và Hybrid RRF, hoàn thiện RESULT.md | `group_project/evaluation/RESULT.md`, `reports/RESULT.md` | Done |
| Test Gate & Delivery | Quản lý bộ acceptance tests, kiểm thử end-to-end 40/40 tests và hoàn thiện tài liệu README dự án | `tests/test_acceptance.py`, `README.md` | Done |

## Quyết định kỹ thuật quan trọng

Mô tả tối đa hai quyết định mà bạn trực tiếp tham gia:

1. **Quyết định:** Thiết kế cơ chế Graceful Fallback cho PageIndex provider ở Task 8 và Task 9.  
   **Lý do/evidence:** PageIndex là dịch vụ đám mây bên ngoài phụ thuộc kết nối mạng và quota API. Khi xảy ra lỗi hoặc timeout, pipeline bắt buộc phải giữ lại kết quả Hybrid retrieval hoặc chuyển sang Safe Refusal chứ không được làm crash UI của người dùng.  
   **Trade-off:** Cần thêm code xử lý ngoại lệ và luồng điều kiện fallback, nhưng đổi lại hệ thống có độ tin cậy (reliability) và độ ổn định rất cao trong buổi demo.

2. **Quyết định:** Thiết kế UI Streamlit hiển thị chi tiết căn cứ pháp lý dạng Expandable Cards.  
   **Lý do/evidence:** Với bài toán tư vấn pháp luật, người dùng không chỉ cần câu trả lời tóm tắt mà bắt buộc phải kiểm chứng được điều luật, tên văn bản và điểm tương đồng (score).  
   **Trade-off:** UI cần render nhiều trường dữ liệu hơn, nhưng mang lại trải nghiệm chuyên nghiệp và minh bạch tuyệt đối cho người dùng.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: Chạy bộ kiểm thử acceptance `pytest tests/test_acceptance.py -v` (5/5 tests passed) và toàn bộ test suite `pytest -v` (40/40 tests passed). Thử nghiệm truy vấn trên giao diện Streamlit với cả câu hỏi in-domain ("thời gian thử việc") và out-of-domain ("World Cup 2022").
- Kết quả trước/sau nếu có: Trước đó test acceptance bị thiếu `golden_dataset.json` và `RESULT.md` dẫn đến fail; sau khi hoàn thiện đầy đủ dữ liệu và báo cáo kết quả, toàn bộ 40 test cases đều đạt 100%.
- Lỗi đã phát hiện và cách xử lý: Phát hiện nguy cơ crash UI khi PageIndex API gặp lỗi mạng hoặc chưa cấu hình API key; đã xử lý bằng khối try-catch an toàn trong `pageindex_search` và `retrieve`, ghi log cảnh báo và giữ kết quả hybrid.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Tốc độ upload tài liệu PDF lên PageIndex phụ thuộc vào mạng ngoài và font chữ hệ thống.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Tích hợp bộ nhớ hội thoại nhiều lượt (Conversation Memory) để chatbot có thể ghi nhớ ngữ cảnh câu hỏi trước đó của người dùng.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-25
- Tên thành viên: Nguyễn Đình Lâm Phúc
