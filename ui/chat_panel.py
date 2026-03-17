"""Post-scrape Q&A with Gemini on extracted data."""

import json
import streamlit as st
import google.generativeai as genai
from config import settings


def render_chat_panel(records: list[dict]):
    """Chat panel for Q&A about extracted data."""

    if not records:
        return

    st.subheader("💬 Chat with Your Data")
    st.caption(f"Ask questions about {len(records)} extracted records using natural language.")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Fixed-height scrollable chat container
    chat_container = st.container(height=450)

    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                "<div style='text-align:center; color:#888; padding:40px 0;'>"
                "No messages yet — ask something below!</div>",
                unsafe_allow_html=True,
            )
        else:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

    # Chat input (stays pinned below the container)
    user_query = st.chat_input("Ask about your data...")

    if user_query:
        # Append user message
        st.session_state.chat_history.append({"role": "user", "content": user_query})

        # Build context from records
        data_context = json.dumps(records[:50], indent=2, default=str)

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=f"models/{settings.GEMINI_MODEL}")

        prompt = f"""You are a helpful data analyst. The user has scraped the following data from a website.
Answer their question based on this data. Be concise and specific. Use markdown formatting for clarity.

Data ({len(records)} records, showing first {min(len(records), 50)}):
{data_context}

User question: {user_query}"""

        with st.spinner("Thinking..."):
            response = model.generate_content(prompt)
            answer = response.text

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()
