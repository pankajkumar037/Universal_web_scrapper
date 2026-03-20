"""Sidebar: Mode, URL, description, pages, strategy, run button."""

import streamlit as st

EXAMPLE_PRESETS = [
    {
        "label": "Naukri - Jobs",
        "url": "https://www.naukri.com/python-developer-jobs",
        "description": "Get all job listings with title, company, salary, location, and experience required",
    },
    {
        "label": "Flipkart - Laptops",
        "url": "https://www.flipkart.com/laptops/pr?sid=6bo,b5g",
        "description": "Get all laptop listings with name, price, rating, processor, RAM, and storage",
    },
    {
        "label": "Scholar - ML Papers",
        "url": "https://scholar.google.com/scholar?q=machine+learning",
        "description": "Get all papers with title, authors, year, citation count, and snippet",
    },
    {
        "label": "Books to Scrape",
        "url": "https://books.toscrape.com/",
        "description": "Get all books with title, price, rating, and availability",
    },
    {
        "label": "LinkedIn - Jobs",
        "url": "https://www.linkedin.com/jobs/search/?keywords=python+developer&location=India",
        "description": "Get all job listings with title, company, location, employment type, and posting date",
    },
]


def _render_smart_mode() -> dict | None:
    """Render the Smart Mode conversational UI. Returns config dict when Run is clicked."""
    from extraction.intent_agent import IntentState, resolve_url, run_intent_turn

    # Initialize session state for smart mode
    if "intent_state" not in st.session_state:
        st.session_state.intent_state = IntentState()
    if "intent_messages" not in st.session_state:
        st.session_state.intent_messages = []
    if "resolved_config" not in st.session_state:
        st.session_state.resolved_config = None

    st.sidebar.markdown("**Smart Mode** — just describe what to scrape")

    # Show conversation history
    for msg in st.session_state.intent_messages:
        role_icon = "**You:**" if msg["role"] == "user" else "**AI:**"
        st.sidebar.markdown(f"{role_icon} {msg['content']}")

    # If already resolved, show editable config + Run button
    if st.session_state.resolved_config:
        rc = st.session_state.resolved_config
        st.sidebar.divider()

        if rc.get("source") == "tavily_error":
            st.sidebar.error(f"Could not find URL: {rc['error']}")
            st.sidebar.caption("Enter the URL manually below.")
        elif rc.get("source") == "tavily":
            st.sidebar.info(f"Found via web search: {rc['url']}")
        elif rc.get("source") == "llm_inferred":
            st.sidebar.info(f"URL inferred by AI: {rc['url']}")

        url = st.sidebar.text_input("URL", value=rc["url"], key="smart_url")
        description = st.sidebar.text_area(
            "What to extract (optional)",
            value=rc.get("description") or "",
            height=80,
            key="smart_desc",
        )
        num_pages = st.sidebar.slider(
            "Number of pages", min_value=1, max_value=10, value=rc.get("num_pages", 1), key="smart_pages"
        )

        col1, col2 = st.sidebar.columns(2)
        run_clicked = col1.button("Run Scraper", type="primary", use_container_width=True)
        col2.button(
            "Start Over",
            use_container_width=True,
            on_click=_reset_smart_mode,
        )

        if run_clicked and url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            return {
                "url": url,
                "description": description,
                "num_pages": num_pages,
                "mode": "standard",
            }
        return None

    # Show the initial prompt or next follow-up
    if not st.session_state.intent_messages:
        st.sidebar.caption("Example: \"python developer jobs on LinkedIn for 3 pages\"")

    # Input form
    with st.sidebar.form("smart_chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Your message",
            placeholder="Tell me what to scrape...",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted and user_input.strip():
        msg_text = user_input.strip()
        st.session_state.intent_messages.append({"role": "user", "content": msg_text})

        with st.spinner("Thinking..."):
            state, follow_up = run_intent_turn(st.session_state.intent_state, msg_text)

        st.session_state.intent_state = state

        if follow_up:
            st.session_state.intent_messages.append({"role": "assistant", "content": follow_up})
        else:
            # Agent is done — resolve URL
            site = state.site or ""
            query = state.query or ""
            if site and query:
                with st.spinner("Resolving URL..."):
                    url, source = resolve_url(site, query, state.location)
            else:
                url, source = "", "tavily"

            if source == "tavily_error":
                error_msg = url.replace("__error__:", "")
                st.session_state.resolved_config = {
                    "url": "",
                    "source": "tavily_error",
                    "error": error_msg,
                    "description": state.description or "",
                    "num_pages": state.num_pages or 1,
                }
            else:
                st.session_state.resolved_config = {
                    "url": url,
                    "source": source,
                    "description": state.description or "",
                    "num_pages": state.num_pages or 1,
                }

        st.rerun()

    # Start Over button (only while chatting)
    if st.session_state.intent_messages:
        st.sidebar.button("Start Over", on_click=_reset_smart_mode, use_container_width=True)

    return None


def _reset_smart_mode():
    """Clear all smart mode session state."""
    st.session_state.intent_state = None
    st.session_state.intent_messages = []
    st.session_state.resolved_config = None


def render_sidebar() -> dict | None:
    """Render the sidebar controls. Returns config dict when Run is clicked, else None."""

    st.sidebar.title("Universal Scraper AI")
    st.sidebar.markdown("*Describe what you want — no selectors needed*")
    st.sidebar.divider()

    # Smart Mode toggle (above Auto-Detect)
    smart_mode = st.sidebar.toggle(
        "Smart Mode",
        help="Chat with AI to describe what to scrape — no URL needed to start!",
        key="smart_mode",
    )

    if smart_mode:
        st.sidebar.divider()
        return _render_smart_mode()

    # Auto-detect toggle
    auto_detect = st.sidebar.toggle(
        "Auto-Detect Mode",
        help="Just provide a URL — AI will detect what data exists and suggest schemas. No description needed!",
    )

    if auto_detect:
        st.sidebar.info("URL-only mode: AI will analyze the page and suggest data types to extract.")

    st.sidebar.divider()

    # Example presets
    if "preset_url" not in st.session_state:
        st.session_state.preset_url = ""
    if "preset_desc" not in st.session_state:
        st.session_state.preset_desc = ""

    st.sidebar.markdown("**Quick Examples**")
    cols = st.sidebar.columns(2)
    for i, preset in enumerate(EXAMPLE_PRESETS):
        col = cols[i % 2]
        if col.button(preset["label"], key=f"preset_{i}", use_container_width=True):
            st.session_state.preset_url = preset["url"]
            st.session_state.preset_desc = preset["description"]
            st.rerun()

    st.sidebar.divider()

    # URL input
    url = st.sidebar.text_input(
        "Target URL",
        value=st.session_state.get("preset_url", ""),
        placeholder="https://www.naukri.com/python-developer-jobs",
    )

    # Description (optional in auto-detect mode)
    description = st.sidebar.text_area(
        "What do you want to extract?" + (" (optional)" if auto_detect else ""),
        value=st.session_state.get("preset_desc", ""),
        placeholder="Get all job listings with title, company, salary, location, and experience required",
        height=100,
    )

    st.sidebar.divider()

    # Pages slider
    num_pages = st.sidebar.slider("Number of pages", min_value=1, max_value=10, value=1)

    st.sidebar.divider()

    # Run button — enabled if URL provided (auto-detect) or URL+description (normal)
    can_run = bool(url and description) or bool(url and auto_detect)
    run_clicked = st.sidebar.button(
        "Run Scraper",
        type="primary",
        use_container_width=True,
        disabled=not can_run,
    )

    if run_clicked and can_run:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        config = {
            "url": url,
            "description": description,
            "num_pages": num_pages,
        }
        if auto_detect and not description:
            config["mode"] = "auto_detect"
        else:
            config["mode"] = "standard"
        return config

    return None
