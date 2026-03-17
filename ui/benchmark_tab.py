"""Pre-computed accuracy display for the Benchmark tab."""

import json
import os
import streamlit as st
import pandas as pd


RESULTS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmark", "results.json")


def render_benchmark_tab():
    """Display pre-computed benchmark results."""

    st.header("Benchmark Results")
    st.markdown("Pre-computed accuracy metrics across 3 demo sites (20 ground truth records each).")

    if not os.path.exists(RESULTS_PATH):
        st.warning("No benchmark results found. Run the benchmark first to generate results.")
        st.code("python -m benchmark.comparator", language="bash")
        return

    with open(RESULTS_PATH) as f:
        results = json.load(f)

    # Overall metrics table
    st.subheader("Overall Metrics")
    overview = []
    for site in results.get("sites", []):
        overview.append({
            "Site": site["site"],
            "Precision": f"{site['precision']:.1%}",
            "Recall": f"{site['recall']:.1%}",
            "F1 Score": f"{site['f1']:.1%}",
        })

    if overview:
        df = pd.DataFrame(overview)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Aggregate
    if results.get("aggregate"):
        agg = results["aggregate"]
        cols = st.columns(3)
        cols[0].metric("Avg Precision", f"{agg.get('precision', 0):.1%}")
        cols[1].metric("Avg Recall", f"{agg.get('recall', 0):.1%}")
        cols[2].metric("Avg F1", f"{agg.get('f1', 0):.1%}")

    # Per-field breakdown
    st.subheader("Per-Field Accuracy")
    for site in results.get("sites", []):
        if site.get("field_scores"):
            with st.expander(f"{site['site']} — Field Breakdown"):
                field_data = []
                for field, scores in site["field_scores"].items():
                    field_data.append({
                        "Field": field,
                        "Precision": f"{scores.get('precision', 0):.1%}",
                        "Recall": f"{scores.get('recall', 0):.1%}",
                    })
                st.dataframe(pd.DataFrame(field_data), use_container_width=True, hide_index=True)
