"""Extraction quality dashboard — visual proof of accuracy for judges."""

import streamlit as st
import pandas as pd


def render_quality_dashboard(records: list[dict]):
    """Display extraction quality metrics and per-field fill rates."""
    if not records:
        return

    st.subheader("Extraction Quality Dashboard")

    df = pd.DataFrame(records)
    total_records = len(df)
    total_fields = len(df.columns)

    # Per-field fill rates
    fill_rates = {}
    for col in df.columns:
        filled = df[col].apply(lambda x: x is not None and x != "" and x != "NOT_FOUND").sum()
        fill_rates[col] = filled / total_records * 100

    avg_fill = sum(fill_rates.values()) / len(fill_rates) if fill_rates else 0

    # Count fully complete records (all fields populated)
    complete = sum(
        1 for _, row in df.iterrows()
        if all(v is not None and v != "" and v != "NOT_FOUND" for v in row)
    )

    # Top metrics row
    cols = st.columns(4)
    cols[0].metric("Total Records", total_records)
    cols[1].metric("Avg Fill Rate", f"{avg_fill:.1f}%")
    cols[2].metric("Complete Records", f"{complete}/{total_records}")
    cols[3].metric("Fields", total_fields)

    # Per-field fill rate bar chart
    st.markdown("**Per-Field Fill Rates**")
    fill_df = pd.DataFrame({
        "Field": list(fill_rates.keys()),
        "Fill Rate (%)": list(fill_rates.values()),
    })
    fill_df = fill_df.sort_values("Fill Rate (%)", ascending=True)

    # Color-coded status
    def _status(rate):
        if rate >= 80:
            return "High"
        elif rate >= 50:
            return "Medium"
        return "Low"

    fill_df["Status"] = fill_df["Fill Rate (%)"].apply(_status)

    # Display as a horizontal bar using st.bar_chart via column chart
    chart_df = fill_df.set_index("Field")[["Fill Rate (%)"]]
    st.bar_chart(chart_df)

    # Per-field detail table
    with st.expander("Field Details"):
        detail_rows = []
        for _, row in fill_df.iterrows():
            rate = row["Fill Rate (%)"]
            status = row["Status"]
            if status == "High":
                indicator = ":green[HIGH]"
            elif status == "Medium":
                indicator = ":orange[MEDIUM]"
            else:
                indicator = ":red[LOW]"
            detail_rows.append(f"| `{row['Field']}` | {rate:.1f}% | {indicator} |")

        table = "| Field | Fill Rate | Status |\n|-------|-----------|--------|\n" + "\n".join(detail_rows)
        st.markdown(table)

    # Record completeness distribution
    st.markdown("**Record Completeness Distribution**")
    completeness = []
    for _, row in df.iterrows():
        filled = sum(1 for v in row if v is not None and v != "" and v != "NOT_FOUND")
        completeness.append(filled / total_fields * 100)

    comp_df = pd.DataFrame({"Completeness (%)": completeness})
    st.bar_chart(comp_df["Completeness (%)"].value_counts(bins=5).sort_index())
