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

# --- Company Type (multi-select, semicolon-split logic)
company_types = sorted(
    set(sum((str(x).split(";") for x in df["Company type"].dropna()), []))
)
company_types = [x.strip() for x in company_types if x.strip()]
selected_company_types = st.sidebar.multiselect(
    "Company Type(s)",
    options=company_types,
    default=[]
)

# --- Product Type (single select)
product_types = ["General (All Products)", "Food"]
selected_product = st.sidebar.selectbox("Product Type", options=["All"] + product_types)

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

if selected_product != "All":
    filtered = filtered[filtered["Product Type"] == selected_product]

if search_term:
    mask = filtered.apply(
        lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(),
        axis=1
    )
    filtered = filtered[mask]

# -----------------------------
# 5. Display Settings
# -----------------------------
st.subheader(f"Filtered Results ({len(filtered)} records)")

# Choose columns for display
display_cols = [
    "Department",
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

# Define column widths (approximate %)
column_config = {
    "Department": st.column_config.TextColumn(width="small"),
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

# -----------------------------
# 6. Display Table (read-only editor)
# -----------------------------
st.data_editor(
    filtered[display_cols],
    hide_index=True,
    use_container_width=True,
    disabled=True,  # read-only mode
    column_config=column_config,
    key="compliance_table",
)

# -----------------------------
# 7. Download CSV Button
# -----------------------------
csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="💾 Download Filtered Results (CSV)",
    data=csv,
    file_name="filtered_compliance_results.csv",
    mime="text/csv"
)

# -----------------------------
# 8. Optional Styling
# -----------------------------
st.markdown("""
<style>
/* --- Table aesthetics --- */
[data-testid="stDataFrame"] table, [data-testid="stDataEditor"] table {
    border-collapse: collapse !important;
}
[data-testid="stDataFrame"] th, [data-testid="stDataEditor"] th {
    background-color: #f7f7f7 !important;
    font-weight: 600 !important;
    color: #333 !important;
}
[data-testid="stDataFrame"] td, [data-testid="stDataEditor"] td {
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    line-height: 1.4 !important;
    font-size: 0.9rem !important;
}
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    max-height: 70vh;
    overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)
