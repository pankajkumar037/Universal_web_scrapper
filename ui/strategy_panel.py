"""Real-time risk/layer/page status panel."""

import streamlit as st


def render_strategy_panel(crawl_info: list[dict], risk: str = "", pagination: dict | None = None):
    """Display crawl strategy information."""

    st.subheader("Crawl Strategy")

    # Risk level
    if risk:
        risk_colors = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}
        color = risk_colors.get(risk, "gray")
        st.markdown(f"**Risk Level:** :{color}[{risk}]")

    # Pagination info
    if pagination:
        cols = st.columns(3)
        cols[0].metric("Pages", len(pagination.get("urls", [1])))
        cols[1].metric("Pattern", pagination.get("pattern", "N/A"))
        cols[2].metric("Method", pagination.get("method", "N/A"))

    # Layer info per page
    if crawl_info:
        layer_names = {1: "Stealth", 2: "Undetected", 3: "Proxy", 4: "Jina"}
        for info in crawl_info:
            layer_num = info.get("layer", 0)
            layer_name = layer_names.get(layer_num, f"Layer {layer_num}")
            st.markdown(
                f"- **{info['url'][:60]}...** → Layer {layer_num} ({layer_name}), "
                f"{info.get('words', 0)} words"
            )
