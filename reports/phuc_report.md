# Individual Contribution Report — Nguyễn Đình Lâm Phúc

## Thông tin

- **Họ và tên:** Nguyễn Đình Lâm Phúc
- **Mã học viên:** AI20K-PHUC-01
- **Nhóm:** Nhóm 3 thành viên (Phúc · Sang · Phát)
- **Vai trò:** Nhóm trưởng / Integration Owner / UI & Delivery
- **Repository / Branch:** `NguyenDinhLamPhuc/K4-L3B-RAG-Pipeline-3Ironman` / `main` & `feat/phuc-integration-ui`

---

## Phần việc đã thực hiện

| Module / Deliverable | Việc tôi trực tiếp làm | File / Commit / PR | Trạng thái |
|---|---|---|:---:|
| **Team Workflow & Environment** | Thiết lập repo, branch protection, hướng dẫn môi trường `uv`, `.env.example`, phân chia task cho 3 thành viên | `KE_HOACH_DAY8_RAG_3_THANH_VIEN.md`, `.env.example` | Done |
| **Data Quality Gate** | Rà soát và nghiệm thu dữ liệu đầu vào của Phát (4 legal docs + 5 news articles), kiểm tra provenance và URL | `data/standardized/manifest.json` | Done |
| **Task 8: PageIndex Fallback** | Xây dựng provider tích hợp PageIndex fallback vectorless, timeout và catch exception an toàn | `src/task8_pageindex_vectorless.py` | Done |
| **Streamlit Chatbot UI** | Thiết kế giao diện tra cứu pháp luật tương tác, hiển thị answer + sources + score + retrieval method | `app.py` | Done |
| **Evaluation Synthesis** | Điều phối đo kiểm 4 metrics, phân tích so sánh A/B và hoàn thiện báo cáo kết quả | `group_project/evaluation/RESULT.md`, `reports/RESULT.md` | Done |
| **Test Gate & Delivery** | Quản lý bộ test acceptance, kiểm thử end-to-end 40/40 tests và hoàn thiện tài liệu nộp bài | `tests/test_acceptance.py`, `README.md` | Done |

---

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Thiết kế cơ chế Graceful Fallback cho PageIndex provider ở Task 8 và Task 9.  
   **Lý do/evidence:** PageIndex là dịch vụ bên ngoài phụ thuộc kết nối mạng và quota API. Khi xảy ra lỗi hoặc timeout, pipeline bắt buộc phải giữ lại kết quả Hybrid retrieval hoặc chuyển sang Safe Refusal chứ không được làm crash UI của người dùng.  
   **Trade-off:** Cần thêm code xử lý ngoại lệ và luồng điều kiện fallback, nhưng đổi lại hệ thống có độ tin cậy (reliability) và độ ổn định rất cao trong buổi demo.

2. **Quyết định:** Thiết kế UI Streamlit hiển thị chi tiết căn cứ pháp lý dạng Expandable Cards.  
   **Lý do/evidence:** Với bài toán tư vấn pháp luật, người dùng không chỉ cần câu trả lời tóm tắt mà bắt buộc phải kiểm chứng được điều luật, tên văn bản và điểm tương đồng (score).  
   **Trade-off:** UI cần render nhiều trường dữ liệu hơn, nhưng mang lại trải nghiệm chuyên nghiệp và minh bạch tuyệt đối cho người dùng.

---

## Kiểm thử và kết quả

- **Test đã chạy:** Chạy và pass 100% `pytest tests/test_acceptance.py -v` (5/5 tests) và toàn bộ suite `pytest -v` (40/40 tests).
- **Manual Test:** Thử nghiệm thành công 3 kịch bản:
  1. *In-domain:* Hỏi chính xác về thời gian thử việc, điều kiện BHXH bắt buộc $\rightarrow$ trả về kết quả chuẩn kèm citation.
  2. *Out-of-domain:* Hỏi về World Cup 2022, nấu phở bò $\rightarrow$ kích hoạt an toàn cơ chế Safe Refusal: *"Tôi không thể xác minh thông tin này từ nguồn hiện có."*
  3. *Chạy index lại:* Kiểm tra tính idempotent, số lượng chunks trong Chroma không bị nhân đôi.

---

## Điều còn hạn chế

- **Hạn chế:** Tốc độ upload tài liệu PDF lên PageIndex phụ thuộc vào mạng ngoài và font chữ hệ thống.
- **Hướng cải tiến nếu có thêm thời gian:** Tích hợp bộ nhớ hội thoại nhiều lượt (Conversation Memory) để chatbot có thể ghi nhớ ngữ cảnh câu hỏi trước đó của người dùng.

---

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- **Ngày:** 2026-09-25
- **Tên thành viên:** Nguyễn Đình Lâm Phúc
