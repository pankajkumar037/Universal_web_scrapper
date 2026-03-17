"""Post-extraction data insights — auto-generated analysis of extracted data."""

import streamlit as st
import pandas as pd


def render_insights(records: list[dict]):
    """Display auto-generated insights about the extracted data."""
    if not records:
        return

    st.subheader("Data Insights")

    df = pd.DataFrame(records)

    findings = []

    # Analyze each column
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue

        # Try numeric analysis
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if len(numeric) > 1:
            st.markdown(f"**`{col}`** (Numeric)")
            cols = st.columns(4)
            cols[0].metric("Min", f"{numeric.min():,.2f}")
            cols[1].metric("Max", f"{numeric.max():,.2f}")
            cols[2].metric("Mean", f"{numeric.mean():,.2f}")
            cols[3].metric("Median", f"{numeric.median():,.2f}")

            # Interesting finding
            if numeric.max() > numeric.mean() * 3:
                idx = numeric.idxmax()
                findings.append(f"**Outlier in `{col}`**: max value ({numeric.max():,.2f}) is {numeric.max()/numeric.mean():.1f}x the average")
            continue

        # String analysis
        if series.dtype == object:
            # Check if it's list-type
            list_series = series[series.apply(lambda x: isinstance(x, list))]
            if len(list_series) > 0:
                avg_items = list_series.apply(len).mean()
                st.markdown(f"**`{col}`** (List)")
                lcols = st.columns(3)
                lcols[0].metric("Avg Items", f"{avg_items:.1f}")
                lcols[1].metric("Max Items", int(list_series.apply(len).max()))
                lcols[2].metric("Total Unique", len(set(item for lst in list_series for item in lst)))
                continue

            # Regular string
            str_series = series.astype(str)
            unique_count = str_series.nunique()
            most_common = str_series.mode().iloc[0] if not str_series.mode().empty else "N/A"
            most_common_count = (str_series == most_common).sum()

            st.markdown(f"**`{col}`** (Text)")
            tcols = st.columns(3)
            tcols[0].metric("Unique Values", unique_count)
            tcols[1].metric("Most Common", most_common[:25] + ("..." if len(str(most_common)) > 25 else ""))
            tcols[2].metric("Frequency", f"{most_common_count}/{len(str_series)}")

            if unique_count == 1:
                findings.append(f"**All same in `{col}`**: every record has \"{most_common[:40]}\"")
            elif unique_count == len(str_series):
                findings.append(f"**All unique in `{col}`**: every value is distinct")

    # Interesting findings summary
    if findings:
        st.markdown("---")
        st.markdown("**Interesting Findings**")
        for f in findings:
            st.markdown(f"- {f}")
