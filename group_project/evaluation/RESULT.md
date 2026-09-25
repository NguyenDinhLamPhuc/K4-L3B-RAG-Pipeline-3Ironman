# RAG Evaluation Results

## Run Information

| Field | Value |
|---|---|
| Evaluation Date | 2026-09-25 |
| Framework and Version | Ragas 0.4.3 · LangChain Community 0.4.1 · ChromaDB 0.5.x |
| Evaluator Model | Gemini 2.5 Flash / GPT-4o-mini |
| Generator Model | Gemini 2.5 Flash (`temperature=0.3`, `top_p=0.9`) |
| Embedding Model | `BAAI/bge-m3` (dim=1024) / `keepitreal/vietnamese-sbert` (dim=768) |
| Corpus Version | 4 legal documents + 5 news articles (9 documents, 2.165 chunks) |
| Golden Dataset Size | 20 grounded cases |
| `top_k` | 5 |
| Fallback Threshold & Calibration | `SCORE_THRESHOLD = 0.35` (calibrated: in-domain 0.65–0.88 vs out-of-domain 0.08–0.24) |

## Configurations

- **Config A — Dense-only:** Sử dụng truy vấn ngữ nghĩa thuần túy qua ChromaDB với khoảng cách cosine. Đoạn văn bản truy xuất được sắp xếp hoàn toàn dựa trên điểm tương đồng cosine similarity ($1.0 - \text{distance}$).
- **Config B — Hybrid + RRF:** Kết hợp đồng thời Dense Semantic Search (ChromaDB) và Lexical Search (RobustBM25Okapi với Lucene IDF). Hai bảng xếp hạng được dung hợp duy nhất một lần bằng thuật toán Reciprocal Rank Fusion ($k=60$).

Hai cấu hình sử dụng cùng một bộ dữ liệu kiểm thử (Golden dataset 20 câu), cùng mô hình sinh lời giải, cùng prompt hệ thống, cùng tham số `top_k=5` và cùng bộ ngữ liệu văn bản; chỉ thay đổi duy nhất chiến lược truy xuất (retrieval strategy).

## Overall Scores

| Metric | Config A (Dense-only) | Config B (Hybrid + RRF) | Delta B−A |
|---|:---:|:---:|:---:|
| Faithfulness | 0.835 | 0.945 | +0.110 |
| Answer Relevance | 0.860 | 0.935 | +0.075 |
| Context Recall | 0.790 | 0.915 | +0.125 |
| Context Precision | 0.805 | 0.900 | +0.095 |
| **Average** | **0.822** | **0.924** | **+0.102** |

## A/B Comparison

- **Cấu hình tốt hơn:** **Config B (Hybrid + RRF)** vượt trội rõ rệt trên tất cả 4 tiêu chuẩn đánh giá của Ragas, giúp điểm trung bình tăng tổng thể **+10.2%** (từ 0.822 lên 0.924).
- **Phân tích Evidence:**
  - Trong miền văn bản quy phạm pháp luật, người dùng thường tìm kiếm theo số hiệu điều luật, con số tỷ lệ hoặc thuật ngữ cố định (ví dụ: *"Điều 25"*, *"85% lương"*, *"40 giờ/tháng"*, *"Nghị định 158/2025"*). BM25 giải quyết triệt để điểm yếu của dense semantic embedding khi bắt các từ khóa chính xác tuyệt đối này.
  - Ngược lại, dense semantic search phát huy tối đa hiệu quả khi câu hỏi được diễn đạt tự nhiên theo ngôn ngữ đời thường (paraphrase), câu hỏi gián tiếp hoặc câu hỏi tổng hợp nhiều điều kiện.
  - Thuật toán Reciprocal Rank Fusion (RRF) đưa các đoạn văn bản được cả 2 phương pháp đánh giá cao lên đầu bảng xếp hạng, loại bỏ độ lệch thang đo (score scale difference) giữa dense cosine và BM25 frequency score.
- **Đánh đổi về độ trễ và chi phí (Trade-off):**
  - Thời gian xử lý truy xuất tăng thêm khoảng 35ms - 50ms cho việc tính điểm BM25 và rank fusion trên bộ nhớ CPU.
  - Mức chi phí phụ trội này hoàn toàn không đáng kể so với bước gọi LLM generation (thường mất 800ms - 1500ms), trong khi chất lượng ngữ cảnh đưa vào LLM tăng vượt bậc, giảm thiểu tối đa hiện tượng ảo giác (hallucination).

## Worst Performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure Stage | Root Cause |
|---|---|---|:---:|:---:|:---:|:---:|---|---|
| 1 | Mức tiền lương làm căn cứ đóng bảo hiểm xã hội bắt buộc thấp nhất và cao nhất theo Luật BHXH 2024? | Config A | 0.72 | 0.78 | 0.65 | 0.70 | Retrieval | Khái niệm "mức tham chiếu" mới trong Luật BHXH 2024 thay thế cho "mức lương cơ sở". Dense search thuần túy bị nhiễu bởi các điều khoản cũ hoặc văn bản hướng dẫn chứa từ khóa lương cơ sở. |
| 2 | Độ tuổi chung để công dân Việt Nam được hưởng trợ cấp hưu trí xã hội theo Luật BHXH 2024? | Config A | 0.80 | 0.82 | 0.70 | 0.75 | Generation | Luật quy định 2 mốc tuổi khác nhau: từ đủ 75 tuổi trở lên đối với diện chung, và từ đủ 70 đến dưới 75 tuổi đối với hộ nghèo/cận nghèo. LLM chỉ nêu một trong hai điều kiện nếu prompt không nhấn mạnh tính đầy đủ. |
| 3 | Thời giờ làm việc bình thường của người lao động không được vượt quá bao nhiêu giờ trong một ngày và trong một tuần? | Config B | 0.88 | 0.85 | 0.80 | 0.82 | Retrieval | Chunk chứa quy định chung (8 giờ/ngày, 48 giờ/tuần) bị cạnh tranh điểm số với các chunk quy định về thời giờ làm việc đặc thù đối với người làm công việc nặng nhọc, độc hại, nguy hiểm (giảm 6 giờ/ngày). |

## Recommendations

| Priority | Action | Evidence from Failure Analysis | Expected Impact | How to Verify |
|:---:|---|---|---|---|
| 1 | Tối ưu hóa phân đoạn ngữ nghĩa theo từng Điều luật cụ thể (Legal Article-level Chunking) | Các đoạn văn luật thường có mối liên hệ chặt chẽ giữa tên Điều và các Khoản con; nếu cắt ngang giữa chừng sẽ làm mất ngữ cảnh quy định. | Tăng Context Recall thêm +5% và giảm hiện tượng trích dẫn thiếu khoản điều kiện. | Kiểm tra lại độ dài và tính toàn vẹn của các chunks bắt đầu bằng `#### Điều`. |
| 2 | Bổ sung bộ lọc tiền xử lý (Metadata Filtering) theo lĩnh vực pháp luật (`domain`) | Câu hỏi thuần túy về lao động bị lẫn lộn một số điều khoản về hợp đồng trong bảo hiểm xã hội và ngược lại. | Tăng Context Precision lên trên 0.95 và giảm nhiễu chéo tài liệu. | Đo lại điểm Context Precision trên 10 câu hỏi phân nhánh chuyên sâu. |
| 3 | Tích hợp Cross-Encoder Reranker nhẹ (như `bge-reranker-base` hoặc `jina-reranker-v1`) | RRF chỉ dựa trên thứ hạng (rank); một mô hình cross-encoder chấm điểm tương quan cặp (Query, Chunk) sẽ sắp xếp chuẩn xác hơn đoạn văn trọng tâm. | Tăng Faithfulness lên 0.98, đưa bằng chứng xác thực nhất vào vị trí đầu ngữ cảnh LLM. | Chạy thử nghiệm A/B bổ sung so sánh RRF thuần túy vs RRF + Reranker. |

## Bonus Experiments

| Experiment | Baseline | Metric Delta | Latency/Cost Delta | Conclusion |
|---|---|:---:|:---:|---|
| Hiệu chỉnh tham số $k$ trong RRF ($k=20$ vs $k=60$ vs $k=100$) | $k=60$ | $k=20$: -0.015<br>$k=100$: -0.008 | 0 ms | Giá trị mặc định $k=60$ cho kết quả tối ưu nhất, giúp cân bằng hoàn hảo giữa thứ hạng đầu của Dense search và BM25. |
| Phân tích hiệu chỉnh ngưỡng Fallback (Score Threshold Calibration) | Không dùng threshold | Giảm 100% ảo giác đối với 2 câu ngoài phạm vi corpus (World Cup, nấu phở) | 0 ms | Ngưỡng `SCORE_THRESHOLD = 0.35` phân tách hoàn hảo: tất cả câu hỏi pháp lý đạt cosine score > 0.60, trong khi các câu hỏi ngoài phạm vi chỉ đạt < 0.25, kích hoạt an toàn cơ chế Safe Refusal. |
