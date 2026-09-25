import streamlit as st
from dotenv import load_dotenv
from src.task10_generation import generate_with_citation

load_dotenv()


def render_sources(sources, retrieval_source):
    if not sources:
        return
    st.caption(f"🔍 **Phương thức truy xuất:** `{retrieval_source.upper()}` · Tìm thấy **{len(sources)}** đoạn trích dẫn căn cứ:")
    for idx, source in enumerate(sources, 1):
        metadata = source.get("metadata", {})
        title = metadata.get("title", "Tài liệu pháp lý")
        score = source.get("score", 0.0)
        method = source.get("retrieval_method", "unknown")
        src_file = metadata.get("source", "")
        url = metadata.get("url")

        expander_title = f"📄 [{idx}] {title} — (Score: {score:.4f} | Method: {method})"
        with st.expander(expander_title):
            st.markdown(f"**Nguồn văn bản:** `{src_file}`")
            if url:
                st.markdown(f"**Liên kết tham chiếu:** [{url}]({url})")
            if "law_number" in metadata:
                st.markdown(f"**Số hiệu:** `{metadata['law_number']}` · **Hiệu lực:** `{metadata.get('effective_date', 'N/A')}`")
            st.text_area("Nội dung trích đoạn (Snippet):", value=source.get("content", ""), height=130, disabled=True)


st.set_page_config(
    page_title="Trợ Lý Pháp Luật Lao Động & BHXH 2024",
    page_icon="⚖️",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar giới thiệu và cấu hình
with st.sidebar:
    st.title("⚖️ RAG Pháp Luật")
    st.markdown("**Đề tài:** Tra cứu **Bộ luật Lao động 2019** & **Luật Bảo hiểm xã hội 2024**")
    st.markdown("---")
    st.markdown("**Thành viên nhóm:**")
    st.markdown("- 👑 **Nguyễn Đình Lâm Phúc** *(Lead / UI / Integration)*")
    st.markdown("- 💻 **Lê Minh Sang** *(Core RAG Engineer)*")
    st.markdown("- 📊 **Nguyễn Tiến Phát** *(Data & Lexical Retrieval)*")
    st.markdown("---")
    st.subheader("⚙️ Cấu hình hệ thống")
    top_k = st.slider("Số lượng đoạn trích (top_k)", min_value=3, max_value=10, value=5)
    st.caption("Pipeline: `Dense + BM25` ➔ `RRF Fusion` ➔ `Fallback Check` ➔ `LLM Generation`")
    st.markdown("---")
    st.subheader("💡 Câu hỏi mẫu")
    st.info(
        "1. *Thời gian thử việc tối đa đối với trình độ cao đẳng là bao lâu?*\n"
        "2. *Người lao động làm thêm giờ ngày nghỉ tuần được trả bao nhiêu?*\n"
        "3. *Luật BHXH 2024 có hiệu lực từ ngày nào và gồm những chế độ gì?*\n"
        "4. *Ai vô địch World Cup 2022? (Thử nghiệm ngoài phạm vi)*"
    )

st.title("⚖️ Trợ Lý Pháp Luật Lao Động & Bảo Hiểm Xã Hội Việt Nam")
st.markdown(
    "> Hệ thống hỏi đáp thông minh dựa trên kỹ thuật **Hybrid RAG** (Dense Semantic Search + BM25 Lexical Search + RRF + Graceful Fallback). "
    "Mọi câu trả lời đều được kiểm chứng và trích dẫn trực tiếp từ văn bản quy phạm pháp luật hiện hành."
)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_sources(message.get("sources", []), message.get("retrieval_source", "none"))

query = st.chat_input("Nhập câu hỏi pháp lý của bạn (ví dụ: Quy định thời gian thử việc, làm thêm giờ, chế độ thai sản...)...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tra cứu cơ sở dữ liệu pháp luật và phân tích câu trả lời..."):
            result = generate_with_citation(query, top_k=top_k)
        st.markdown(result["answer"])
        render_sources(result["sources"], result["retrieval_source"])

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
        "retrieval_source": result["retrieval_source"],
    })
