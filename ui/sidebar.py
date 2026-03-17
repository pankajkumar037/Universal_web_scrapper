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


def render_sidebar() -> dict | None:
    """Render the sidebar controls. Returns config dict when Run is clicked, else None."""

    st.sidebar.title("Universal Scraper AI")
    st.sidebar.markdown("*Describe what you want — no selectors needed*")
    st.sidebar.divider()

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
