import streamlit as st
from dotenv import load_dotenv
from src.task10_generation import generate_with_citation


load_dotenv()


def render_sources(sources, retrieval_source):
    if not sources:
        return
    st.caption(f"Retrieval: {retrieval_source}")
    for source in sources:
        metadata = source["metadata"]
        with st.expander(f"[Source: {source['id']}] — {metadata['title']}"):
            st.text(f"Source: {metadata['source']}")
            st.text(f"Score: {source['score']:.6f} | Method: {source['retrieval_method']}")
            if metadata.get("url"):
                st.text(metadata["url"])
            st.text(source["content"])

st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("RAG Chatbot")
    st.caption("Thay mô tả theo đề tài của nhóm")
    top_k = st.slider("Số chunks", 3, 10, 5)

st.title("RAG Chatbot")
st.caption("Thay tiêu đề và hướng dẫn sử dụng")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_sources(message.get("sources", []), message.get("retrieval_source", "none"))

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm nguồn và tạo câu trả lời..."):
            result = generate_with_citation(query, top_k=top_k)
        st.markdown(result["answer"])
        render_sources(result["sources"], result["retrieval_source"])

    st.session_state.messages.append({
        "role": "assistant", "content": result["answer"],
        "sources": result["sources"], "retrieval_source": result["retrieval_source"],
    })
