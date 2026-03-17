"""Results table display."""

import streamlit as st
import pandas as pd


def render_results_table(records: list[dict]):
    """Display extraction results as a table."""

    if not records:
        st.info("No records extracted.")
        return

    st.subheader(f"Extracted Records ({len(records)})")

    df = pd.DataFrame(records)

    # Flatten list cells to comma-separated strings (prevents ArrowInvalid)
    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: ", ".join(str(item) for item in x) if isinstance(x, list) else x
        )

    # Replace None with dash; cast to string to prevent Arrow mixed-type errors
    df = df.fillna("—").astype(str)

    st.dataframe(df, use_container_width=True, hide_index=True)
