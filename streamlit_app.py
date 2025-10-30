import pandas as pd
import streamlit as st

# -----------------------------
# 1. Page & Layout Settings
# -----------------------------
st.set_page_config(
    page_title="IMP Packaging Compliance Tool",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📦 IMP Packaging Compliance Tool")
st.caption("Business-oriented EU/NL packaging compliance overview (updated Oct 2025)")

# -----------------------------
# 2. Load Data
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("data/final_table.xlsx")
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# -----------------------------
# 3. Sidebar Filters
# -----------------------------
st.sidebar.header("🔎 Filters")

# --- Department (multi-select)
departments = sorted(df["Department"].dropna().unique().tolist())
selected_depts = st.sidebar.multiselect(
    "Department(s)",
    options=departments,
    default=[]
)

# --- Company Type (multi-select)
company_types = sorted(
    set(sum((str(x).split(";") for x in df["Company type"].dropna()), []))
)
company_types = [x.strip() for x in company_types if x.strip()]
selected_company_types = st.sidebar.multiselect(
    "Company Type(s)",
    options=company_types,
    default=[]
)

# --- Packaging Type (single select)
packaging_types = ["General (All Packaging)", "Food Packaging"]
selected_packaging = st.sidebar.selectbox("Packaging Type", options=["All"] + packaging_types)

# Map new labels back to original data values
type_mapping = {
    "General (All Packaging)": "General (All Products)",
    "Food Packaging": "Food"
}

# --- Keyword search
search_term = st.sidebar.text_input("Keyword Search", placeholder="Search any text...")

# -----------------------------
# 4. Filtering Logic
# -----------------------------
filtered = df.copy()

if selected_depts:
    filtered = filtered[filtered["Department"].isin(selected_depts)]

if selected_company_types:
    mask = filtered["Company type"].apply(
        lambda x: any(ct in str(x) for ct in selected_company_types)
    )
    filtered = filtered[mask]

if selected_packaging != "All":
    mapped_value = type_mapping[selected_packaging]
    filtered = filtered[filtered["Product Type"] == mapped_value]

if search_term:
    mask = filtered.apply(
        lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(),
        axis=1
    )
    filtered = filtered[mask]

# -----------------------------
# 5. Display Table
# -----------------------------
st.markdown(f"### Filtered Results — {len(filtered)} records shown")

# Visible columns (your new order)
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

# Column width config (approximate)
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

# Read-only, full-width table (no internal scroll)
st.data_editor(
    filtered[display_cols],
    hide_index=True,
    use_container_width=True,
    disabled=True,
    column_config=column_config,
    key="compliance_table",
)

# -----------------------------
# 6. Download CSV Button
# -----------------------------
csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="💾 Download Filtered Results (CSV)",
    data=csv,
    file_name="filtered_compliance_results.csv",
    mime="text/csv"
)

# -----------------------------
# 7. Styling
# -----------------------------
st.markdown("""
<style>
/* Remove inner scrollbars */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    overflow: visible !important;
}

/* Table styling */
[data-testid="stDataFrame"] table, [data-testid="stDataEditor"] table {
    border-collapse: collapse !important;
    width: 100% !important;
}

[data-testid="stDataFrame"] th, [data-testid="stDataEditor"] th {
    background-color: #f7f7f7 !important;
    font-weight: 600 !important;
    color: #333 !important;
    border-bottom: 1px solid #ddd !important;
}

[data-testid="stDataFrame"] td, [data-testid="stDataEditor"] td {
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    line-height: 1.4 !important;
    font-size: 0.9rem !important;
    border-bottom: 1px solid #eee !important;
    vertical-align: top !important;
}

/* Make the entire table naturally expand (no separate scroll) */
section[data-testid="stSidebar"] {
    min-width: 320px !important;
}
</style>
""", unsafe_allow_html=True)
