"""Streamlit entry point — Universal Scraper AI."""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

# Apply nest_asyncio globally before any async code runs
import nest_asyncio
nest_asyncio.apply()

import streamlit as st
from ui.sidebar import render_sidebar
from ui.progress_feed import ProgressFeed
from ui.results_table import render_results_table
from ui.chat_panel import render_chat_panel
from ui.export import render_export
from ui.quality_dashboard import render_quality_dashboard
from ui.transparency_panel import render_transparency_panel
from ui.schema_editor import render_schema_editor
from ui.insights_tab import render_insights

st.set_page_config(
    page_title="Universal Scraper AI",
    page_icon="🔍",
    layout="wide",
)

# Initialize session state
if "results" not in st.session_state:
    st.session_state.results = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_extraction" not in st.session_state:
    st.session_state.pending_extraction = None
if "auto_detect_types" not in st.session_state:
    st.session_state.auto_detect_types = None
if "selected_schema" not in st.session_state:
    st.session_state.selected_schema = None


def _run_standard_pipeline(config):
    """Standard mode: URL + description -> full pipeline."""
    progress = ProgressFeed()

    try:
        from agents.crew import run_crew_pipeline

        results = run_crew_pipeline(
            url=config["url"],
            description=config["description"],
            num_pages=config["num_pages"],
            callback=progress.get_callback(),
        )
        st.session_state.results = results

    except Exception as e:
        progress.update("error", {"message": str(e)})
        st.error(f"Pipeline error: {e}")
        import traceback
        st.code(traceback.format_exc())


def _run_auto_detect(config):
    """Auto-detect mode: URL only -> detect data types -> user picks -> extract."""
    from agents.crew import run_crawl_and_plan
    from extraction.auto_detect import detect_page_content

    progress = ProgressFeed()

    try:
        # Phase 1: Crawl the page
        plan_result = run_crawl_and_plan(
            url=config["url"],
            description="",
            num_pages=config["num_pages"],
            callback=progress.get_callback(),
        )

        # Detect content types
        progress.update("auto_detect_start", {"message": "AI is analyzing page content..."})
        detected_types = detect_page_content(plan_result["markdown"])
        progress.update("auto_detect_complete", {"types": len(detected_types)})

        # Store for selection
        st.session_state.auto_detect_types = detected_types
        st.session_state.pending_extraction = {
            "plan_result": plan_result,
            "config": config,
        }

    except Exception as e:
        progress.update("error", {"message": str(e)})
        st.error(f"Auto-detect error: {e}")
        import traceback
        st.code(traceback.format_exc())


def _render_auto_detect_selection():
    """Show detected data types as selectable cards."""
    detected_types = st.session_state.auto_detect_types

    st.subheader("Detected Data Types")
    st.caption("AI found the following data structures on the page. Select one to extract.")

    cols = st.columns(min(len(detected_types), 3))

    for i, dtype in enumerate(detected_types):
        col = cols[i % len(cols)]
        with col:
            with st.container(border=True):
                st.markdown(f"### {dtype.name}")
                st.markdown(dtype.description)
                st.markdown(f"**Record:** {dtype.record_description}")
                st.markdown(f"**Fields ({len(dtype.suggested_fields)}):**")
                for f in dtype.suggested_fields[:6]:
                    st.markdown(f"- `{f.name}` ({f.field_type})")
                if len(dtype.suggested_fields) > 6:
                    st.caption(f"...and {len(dtype.suggested_fields) - 6} more")

                if st.button(f"Select \"{dtype.name}\"", key=f"select_type_{i}", use_container_width=True):
                    from extraction.auto_detect import detected_to_schema
                    schema = detected_to_schema(dtype)
                    # Store schema for editor phase
                    st.session_state.selected_schema = schema
                    st.rerun()


def _run_with_schema(schema):
    """Run extraction with a pre-built schema (from auto-detect or editor)."""
    from agents.crew import run_extract_and_validate

    pending = st.session_state.pending_extraction
    if not pending:
        st.error("No pending extraction context. Please start over.")
        return

    plan_result = pending["plan_result"]
    config = pending["config"]

    # Update the plan_result with the selected/edited schema
    plan_result["schema"] = schema
    plan_result["telemetry"]["schema_source"] = "auto_detect"
    plan_result["telemetry"]["fields_inferred"] = [f.name for f in schema.fields]

    progress = ProgressFeed(start_phase="extract")

    try:
        results = run_extract_and_validate(
            plan_result=plan_result,
            num_pages=config["num_pages"],
            callback=progress.get_callback(),
        )
        st.session_state.results = results
        # Clear pending state
        st.session_state.pending_extraction = None
        st.session_state.auto_detect_types = None
        st.session_state.selected_schema = None

    except Exception as e:
        progress.update("error", {"message": str(e)})
        st.error(f"Extraction error: {e}")
        import traceback
        st.code(traceback.format_exc())


def _run_two_phase_pipeline(config):
    """Two-phase mode: crawl+plan -> show schema editor -> extract on confirm."""
    from agents.crew import run_crawl_and_plan

    progress = ProgressFeed()

    try:
        plan_result = run_crawl_and_plan(
            url=config["url"],
            description=config["description"],
            num_pages=config["num_pages"],
            callback=progress.get_callback(),
        )

        # Store for schema editor phase
        st.session_state.selected_schema = plan_result["schema"]
        st.session_state.pending_extraction = {
            "plan_result": plan_result,
            "config": config,
        }

    except Exception as e:
        progress.update("error", {"message": str(e)})
        st.error(f"Pipeline error: {e}")
        import traceback
        st.code(traceback.format_exc())


def _display_results(results):
    """Display all result panels."""

    # Transparency panel (replaces old strategy panel)
    telemetry = results.get("telemetry", {})
    schema = results.get("schema", {})
    crawl_info = results.get("crawl_info", [])

    if telemetry:
        render_transparency_panel(
            telemetry=telemetry,
            schema=schema,
            crawl_info=crawl_info,
        )
    else:
        # Fallback for backward compatibility if no telemetry
        from ui.strategy_panel import render_strategy_panel
        render_strategy_panel(
            crawl_info=crawl_info,
            risk=crawl_info[0].get("risk", "") if crawl_info else "",
            pagination=results.get("pagination"),
        )

    st.divider()

    # Results table
    render_results_table(records=results["records"])

    st.divider()

    # Quality dashboard
    render_quality_dashboard(results["records"])

    st.divider()

    # Export
    render_export(results["records"])

    st.divider()

    # Data Insights
    with st.expander("Data Insights", expanded=False):
        render_insights(results["records"])

    st.divider()

    # Chat
    render_chat_panel(results["records"])


def main():
    # Sidebar controls
    config = render_sidebar()

    with st.container():
        if config:
            # Reset chat on new scrape
            st.session_state.chat_history = []

            mode = config.get("mode", "standard")

            if mode == "auto_detect":
                _run_auto_detect(config)
            else:
                _run_two_phase_pipeline(config)

        # --- Schema editor phase ---
        if st.session_state.selected_schema and st.session_state.pending_extraction:
            # Show auto-detect cards if they exist and no schema selected yet
            if st.session_state.auto_detect_types and not st.session_state.get("_schema_from_autodetect"):
                _render_auto_detect_selection()
                # If a schema was just selected via auto-detect, it'll be in selected_schema after rerun
                return

            # Show schema editor
            schema = st.session_state.selected_schema
            edited = render_schema_editor(schema)

            if edited:
                _run_with_schema(edited)

        # --- Auto-detect type selection (before schema is chosen) ---
        if st.session_state.auto_detect_types and not st.session_state.selected_schema:
            _render_auto_detect_selection()

        # --- Display results ---
        results = st.session_state.results
        if results and results.get("records"):
            _display_results(results)
        elif results is not None and not results.get("records"):
            st.warning("No records were extracted. Try a different URL or description.")


if __name__ == "__main__":
    main()
