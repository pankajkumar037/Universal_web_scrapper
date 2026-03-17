"""JSON + CSV download buttons."""

import json
import io
import streamlit as st
import pandas as pd


def render_export(records: list[dict]):
    """Render download buttons for JSON and CSV export."""

    if not records:
        return

    st.subheader("Export Data")

    col1, col2 = st.columns(2)

    # JSON export
    json_str = json.dumps(records, indent=2, default=str)
    col1.download_button(
        label="Download JSON",
        data=json_str,
        file_name="scraped_data.json",
        mime="application/json",
        use_container_width=True,
    )

    # CSV export
    df = pd.DataFrame(records)
    # Flatten list cells to comma-separated strings
    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: ", ".join(str(item) for item in x) if isinstance(x, list) else x
        )
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    col2.download_button(
        label="Download CSV",
        data=csv_buffer.getvalue(),
        file_name="scraped_data.csv",
        mime="text/csv",
        use_container_width=True,
    )
