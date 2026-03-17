"""Interactive schema editor — lets users add/remove/rename fields before extraction."""

import streamlit as st
from models import RefinedSchema, FieldSpec

FIELD_TYPES = ["str", "int", "float", "list[str]"]


def render_schema_editor(schema: RefinedSchema, key_prefix: str = "schema_editor") -> RefinedSchema | None:
    """Render an editable schema form. Returns edited RefinedSchema on confirm, None otherwise."""

    st.subheader("Schema Editor")
    st.caption("Review and edit the AI-inferred schema before extraction.")

    with st.form(key=f"{key_prefix}_form"):
        # Record description
        record_desc = st.text_input(
            "Record Description",
            value=schema.record_description,
            help="What constitutes a single record/item on the page",
        )

        st.markdown("---")
        st.markdown("**Fields**")

        edited_fields = []
        fields_to_delete = []

        for i, field in enumerate(schema.fields):
            cols = st.columns([3, 2, 4, 1])

            name = cols[0].text_input(
                "Name",
                value=field.name,
                key=f"{key_prefix}_name_{i}",
            )

            type_idx = FIELD_TYPES.index(field.field_type) if field.field_type in FIELD_TYPES else 0
            field_type = cols[1].selectbox(
                "Type",
                options=FIELD_TYPES,
                index=type_idx,
                key=f"{key_prefix}_type_{i}",
            )

            desc = cols[2].text_input(
                "Description",
                value=field.description,
                key=f"{key_prefix}_desc_{i}",
            )

            delete = cols[3].checkbox(
                "Del",
                key=f"{key_prefix}_del_{i}",
            )

            if delete:
                fields_to_delete.append(i)
            else:
                edited_fields.append(FieldSpec(
                    name=name.strip().replace(" ", "_").lower(),
                    field_type=field_type,
                    description=desc,
                ))

        # New field section
        st.markdown("---")
        st.markdown("**Add New Field**")
        new_cols = st.columns([3, 2, 4])
        new_name = new_cols[0].text_input("New Field Name", key=f"{key_prefix}_new_name")
        new_type = new_cols[1].selectbox("New Field Type", options=FIELD_TYPES, key=f"{key_prefix}_new_type")
        new_desc = new_cols[2].text_input("New Field Description", key=f"{key_prefix}_new_desc")

        submitted = st.form_submit_button("Confirm & Extract", type="primary", use_container_width=True)

        if submitted:
            # Add new field if name provided
            if new_name.strip():
                edited_fields.append(FieldSpec(
                    name=new_name.strip().replace(" ", "_").lower(),
                    field_type=new_type,
                    description=new_desc or f"User-added field: {new_name}",
                ))

            if not edited_fields:
                st.error("At least one field is required.")
                return None

            return RefinedSchema(
                fields=edited_fields,
                record_description=record_desc,
            )

    return None
