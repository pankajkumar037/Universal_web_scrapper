"""Post-scrape Q&A with Gemini on extracted data."""

import json
import streamlit as st
import google.generativeai as genai
from config import settings


def render_chat_panel(records: list[dict]):
    """Chat panel for Q&A about extracted data."""

    if not records:
        return

    st.subheader("Chat with Your Data")
    st.caption("Ask questions about the extracted data using natural language.")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input
    user_query = st.chat_input("Ask about your data...")

    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.write(user_query)

        # Build context from records
        data_context = json.dumps(records[:50], indent=2, default=str)  # Cap at 50 records

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=f"models/{settings.GEMINI_MODEL}")

        prompt = f"""You are a helpful data analyst. The user has scraped the following data from a website.
Answer their question based on this data. Be concise and specific.

Data ({len(records)} records):
{data_context}

User question: {user_query}"""

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = model.generate_content(prompt)
                answer = response.text
                st.write(answer)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
