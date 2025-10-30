import pandas as pd
import streamlit as st

# -----------------------------
# 1) Page & Layout
# -----------------------------
st.set_page_config(
    page_title="Packaging Compliance Tool",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("📦 Packaging Compliance Tool")
st.caption(
    "Business-oriented EU/NL packaging compliance overview (updated Oct 2025) — built by Ivo Markovic Piñol"
)

# -----------------------------
# 2) Data
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("data/final_table.xlsx")
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# -----------------------------
# 3) Sidebar Filters (order)
# -----------------------------
st.sidebar.header("🔎 Filters")

# Company Type (multi, semicolon split, dedup)
company_types_raw = set()
for val in df["Company type"].dropna():
    for part in str(val).split(";"):
        p = part.strip()
        if p:
            company_types_raw.add(p)
company_types = sorted(company_types_raw)
selected_company_types = st.sidebar.multiselect(
    "Company Type(s)", options=company_types, default=[]
)

# Department (multi)
departments = sorted(df["Department"].dropna().unique().tolist())
selected_depts = st.sidebar.multiselect(
    "Department(s)", options=departments, default=[]
)

# Packaging Type (single)
selected_packaging = st.sidebar.selectbox(
    "Packaging Type", options=["All", "Food Packaging"]
)

# Keyword search
search_term = st.sidebar.text_input("Keyword Search", placeholder="Search any text...")

# -----------------------------
# 4) Filtering
# -----------------------------
filtered = df.copy()

if selected_company_types:
    mask = filtered["Company type"].apply(
        lambda x: any(ct in str(x) for ct in selected_company_types)
    )
    filtered = filtered[mask]

if selected_depts:
    filtered = filtered[filtered["Department"].isin(selected_depts)]

if selected_packaging == "Food Packaging":
    filtered = filtered[filtered["Product Type"] == "Food"]

if search_term:
    mask = filtered.apply(
        lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(),
        axis=1,
    )
    filtered = filtered[mask]

# -----------------------------
# 5) Table
# -----------------------------
st.markdown(f"### Filtered Results — {len(filtered)} records shown")

display_cols = [
    "Trigger",
    "Description",
    "Regulation",
    "Reference",
    "Applicability",
    "Consequence",
    "Deadline",
    "Status",
    "Evidence to Collect",
]

column_config = {
    "Trigger": st.column_config.TextColumn(width="small"),
    "Description": st.column_config.TextColumn(width="large"),
    "Regulation": st.column_config.TextColumn(width="small"),
    "Reference": st.column_config.TextColumn(width="small"),
    "Applicability": st.column_config.TextColumn(width="medium"),
    "Consequence": st.column_config.TextColumn(width="small"),
    "Deadline": st.column_config.TextColumn(width="small"),
    "Status": st.column_config.TextColumn(width="small"),
    "Evidence to Collect": st.column_config.TextColumn(width="medium"),
}

st.data_editor(
    filtered[display_cols],
    hide_index=True,
    use_container_width=True,
    disabled=True,
    column_config=column_config,
    key="compliance_table",
)

# Download
csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="💾 Download Filtered Results (CSV)",
    data=csv,
    file_name="filtered_compliance_results.csv",
    mime="text/csv",
)

# -----------------------------
# 6) Styling: real wrap + no inner scroll + full width on collapse
# -----------------------------
st.markdown(
    """
<style>
/* --- Global container: always take full width --- */
.block-container, [data-testid="stAppViewContainer"] {
    max-width: 100% !important;
    width: 100% !important;
}

/* --- No inner scrollbars, let the page scroll --- */
[data-testid="stDataEditor"], [data-testid="stDataFrame"] {
    overflow: visible !important;
}

/* --- Header style --- */
[data-testid="stDataEditor"] th, [data-testid="stDataFrame"] th {
    background-color: #f7f7f7 !important;
    font-weight: 600 !important;
    color: #333 !important;
    border-bottom: 1px solid #ddd !important;
}

/* 
Force true WRAP in editor cells:
Streamlit renders a grid with role="gridcell". The inner content sits in multiple nested divs/spans.
We override all layers to allow wrapping and vertical growth.
*/
[data-testid="stDataEditor"] [role="gridcell"],
[data-testid="stDataEditor"] [role="gridcell"] * {
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
    text-overflow: clip !important;
    overflow: visible !important;
}

/* Make rows auto-height and align to the top so multiple lines are visible */
[data-testid="stDataEditor"] [role="row"] {
    align-items: flex-start !important;
}
[data-testid="stDataEditor"] [role="gridcell"] {
    align-items: flex-start !important;
}

/* Slightly taller baseline for readability */
[data-testid="stDataEditor"] td, [data-testid="stDataFrame"] td {
    line-height: 1.5 !important;
    vertical-align: top !important;
    border-bottom: 1px solid #eee !important;
}

/* --- Sidebar normal width --- */
section[data-testid="stSidebar"] {
    min-width: 320px !important;
}

/* --- When sidebar collapses, reclaim ALL left space --- */
[data-testid="stSidebarCollapsedControl"] ~ div, 
[data-testid="collapsedControl"] ~ div,
[data-testid="stAppViewContainer"] > div:first-child {
    margin-left: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
}

/* --- Kill any horizontal scrollbar remnants in the editor wrapper --- */
[data-testid="stDataEditor"] > div:has([role="grid"]) {
    overflow-x: hidden !important;
}
</style>
""",
    unsafe_allow_html=True,
)
