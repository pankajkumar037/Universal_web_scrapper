"""Under the Hood — transparent AI decision-making panel for judges."""

import streamlit as st


def render_transparency_panel(telemetry: dict, schema: dict, crawl_info: list[dict] = None):
    """Display the full AI reasoning pipeline: risk, escalation, schema, pagination, extraction."""

    st.subheader("Under the Hood")

    # 1. Risk Assessment
    with st.expander("Risk Assessment", expanded=True):
        risk = telemetry.get("risk_level", "UNKNOWN")
        risk_colors = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}
        color = risk_colors.get(risk, "gray")
        st.markdown(f"**Site Risk Level:** :{color}[{risk}]")

        start_layer = telemetry.get("layer_succeeded", 1)
        st.markdown(f"**Starting Layer:** {RISK_START_MAP.get(risk, 1)} | **Succeeded at Layer:** {start_layer}")

    # 2. Crawler Escalation Timeline
    with st.expander("Crawler Escalation Timeline"):
        layers_attempted = telemetry.get("layers_attempted", [])
        if layers_attempted:
            for entry in layers_attempted:
                layer_num = entry.get("layer", "?")
                name = entry.get("name", "Unknown")
                result = entry.get("result", "unknown")
                error = entry.get("error")

                if result == "success":
                    st.markdown(f":green[Layer {layer_num} ({name})] — SUCCESS")
                else:
                    st.markdown(f":red[Layer {layer_num} ({name})] — FAILED: {error}")
        else:
            st.info("No escalation data available.")

        # Also show per-page crawl info
        if crawl_info and len(crawl_info) > 1:
            st.markdown("**Multi-page crawl layers:**")
            for info in crawl_info:
                layer_names = {1: "Stealth", 2: "Undetected", 3: "Proxy", 4: "Jina"}
                layer_num = info.get("layer", 0)
                st.markdown(
                    f"- Page {info.get('page', 1)}: Layer {layer_num} "
                    f"({layer_names.get(layer_num, '?')}), {info.get('words', 0)} words"
                )

    # 3. Schema Intelligence
    with st.expander("Schema Intelligence"):
        source = telemetry.get("schema_source", "user_description")
        st.markdown(f"**Source:** `{source}`")

        fields_inferred = telemetry.get("fields_inferred", [])
        if fields_inferred:
            st.markdown(f"**Fields inferred ({len(fields_inferred)}):**")
            for f in fields_inferred:
                st.markdown(f"- `{f}`")
        elif schema and schema.get("fields"):
            st.markdown(f"**Fields ({len(schema['fields'])}):**")
            for f in schema["fields"]:
                st.markdown(f"- `{f.get('name', '?')}` ({f.get('field_type', 'str')}): {f.get('description', '')}")

        plan_time = telemetry.get("timings", {}).get("plan", 0)
        if plan_time:
            st.caption(f"Schema inference took {plan_time:.1f}s")

    # 4. Pagination
    with st.expander("Pagination Detection"):
        pag_method = telemetry.get("pagination_method", "N/A")
        pag_pattern = telemetry.get("pagination_pattern", "N/A")
        pages_found = telemetry.get("pages_found", 1)

        cols = st.columns(3)
        cols[0].metric("Method", pag_method)
        cols[1].metric("Pattern", pag_pattern[:30] if pag_pattern else "N/A")
        cols[2].metric("Pages", pages_found)

    # 5. Extraction Strategy
    with st.expander("Extraction Strategy"):
        strategy = telemetry.get("extraction_strategy", "N/A")
        st.markdown(f"**Strategy:** `{strategy}`")

        extract_time = telemetry.get("timings", {}).get("extract", 0)
        if extract_time:
            st.caption(f"Extraction took {extract_time:.1f}s")

    # 6. Quality / Dedup
    with st.expander("Deduplication"):
        before = telemetry.get("records_before_dedup", 0)
        after = telemetry.get("records_after_dedup", 0)
        removed = before - after

        cols = st.columns(3)
        cols[0].metric("Before Dedup", before)
        cols[1].metric("After Dedup", after)
        cols[2].metric("Removed", removed)

    # 7. Timing Breakdown
    with st.expander("Timing Breakdown"):
        timings = telemetry.get("timings", {})
        if timings:
            total = sum(timings.values())
            for phase, t in timings.items():
                pct = (t / total * 100) if total > 0 else 0
                st.markdown(f"- **{phase.capitalize()}:** {t:.1f}s ({pct:.0f}%)")
            st.markdown(f"- **Total:** {total:.1f}s")
        else:
            st.info("No timing data available.")


# Risk -> starting layer mapping (for display)
RISK_START_MAP = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
