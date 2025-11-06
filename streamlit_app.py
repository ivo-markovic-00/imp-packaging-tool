import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import date, datetime, timezone, timedelta
import re

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
# 2) Data (with cache auto-refresh)
# -----------------------------
@st.cache_data
def load_data(data_path: str, cache_bust: float):
    df = pd.read_excel(data_path)
    df.columns = df.columns.str.strip()
    return df

DATA_PATH = "data/final_table.xlsx"
cache_bust = Path(DATA_PATH).stat().st_mtime  # auto-refresh cache when file changes
df = load_data(DATA_PATH, cache_bust)

# -----------------------------
# 3) Robust deadline parsing (DEADLINE-DRIVEN)
# -----------------------------
TODAY = date.today()

# Extract ISO date anywhere in text (handles "Estimated 2028-01-01" and "2026-09-27 00:00:00")
ISO_IN_TEXT = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

def extract_date_from_any(val):
    """Return a date from diverse inputs: datetime/date, 'YYYY-MM-DD', 'Estimated YYYY-MM-DD', '... 00:00:00'."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    # Direct datetime/date
    if isinstance(val, pd.Timestamp):
        return val.date()
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    s = str(val).strip()
    if not s:
        return None

    # Find ISO yyyy-mm-dd anywhere in the text
    m = ISO_IN_TEXT.search(s)
    if m:
        try:
            return pd.to_datetime(m.group(1), errors="raise").date()
        except Exception:
            pass

    # Last resort: generic parser
    try:
        ts = pd.to_datetime(s, errors="coerce")
        if pd.notna(ts):
            return ts.date()
    except Exception:
        pass

    return None

def categorize_deadline_from_row(row):
    """
    Three buckets based on ACTUAL values found in your table:
    - Deadline: 'In Force' (any case/spacing)         → In force
    - Deadline: 'Estimated YYYY-MM-DD' or 'YYYY-MM-DD' → parse & bucket
    - Fallback to Status if it contains a usable date.
    """
    raw_deadline = row.get("Deadline", "")
    deadline_txt = str(raw_deadline or "").strip().lower().replace("\u00a0", " ")

    # 1) Primary: DEADLINE says "In Force" → always In force
    if deadline_txt == "in force":
        return "In force"

    # 2) Try to extract a date from DEADLINE first (covers Estimated + plain dates)
    d = extract_date_from_any(raw_deadline)

    # 3) Fallback: try STATUS (in case a date is there)
    if d is None:
        d = extract_date_from_any(row.get("Status"))

    # 4) Bucket
    if d is None:
        # With only 3 buckets, treat unknowns as farther out (safer than mislabeling In force)
        return "Due > 1 year"

    if d <= TODAY:
        return "In force"
    elif (d - TODAY).days <= 365:
        return "Due < 1 year"
    else:
        return "Due > 1 year"

# Compute once for the dataset
df["Deadline Category"] = df.apply(categorize_deadline_from_row, axis=1)

# -----------------------------
# 4) Sidebar Filters (incl. Deadline)
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

# Deadline (single, 3 buckets)
deadline_options = ["All", "In force", "Due < 1 year", "Due > 1 year"]
selected_deadline = st.sidebar.selectbox("Deadline", options=deadline_options, index=0)

# Keyword search
search_term = st.sidebar.text_input("Keyword Search", placeholder="Search any text...")

# -----------------------------
# 5) Filtering
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

if selected_deadline != "All":
    filtered = filtered[filtered["Deadline Category"] == selected_deadline]

if search_term:
    mask = filtered.apply(
        lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(),
        axis=1,
    )
    filtered = filtered[mask]

# -----------------------------
# 6) Table
# -----------------------------
st.markdown(f"### Filtered Results — {len(filtered)} records shown")

display_cols = [
    "Trigger",
    "Description",
    "Regulation",
    "Reference",
    "Applicability",
    "Consequence",
    "Deadline",           # show original text as-is
    "Status",
    "Evidence to Collect",
]

# Ensure Deadline prints nicely (no 00:00:00); if datetime slipped through
if "Deadline" in filtered.columns:
    if pd.api.types.is_datetime64_any_dtype(filtered["Deadline"]):
        filtered["Deadline"] = filtered["Deadline"].dt.date
    filtered["Deadline"] = filtered["Deadline"].astype(str).replace("NaT", "")

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
# 7) Styling (wrap + no inner scroll + expand on collapse)
# -----------------------------
st.markdown(
    """
<style>
.block-container, [data-testid="stAppViewContainer"] {
    max-width: 100% !important;
    width: 100% !important;
}
[data-testid="stDataEditor"], [data-testid="stDataFrame"] {
    overflow: visible !important;
}
[data-testid="stDataEditor"] th, [data-testid="stDataFrame"] th {
    background-color: #f7f7f7 !important;
    font-weight: 600 !important;
    color: #333 !important;
    border-bottom: 1px solid #ddd !important;
}
[data-testid="stDataEditor"] [role="gridcell"],
[data-testid="stDataEditor"] [role="gridcell"] * {
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
    text-overflow: clip !important;
    overflow: visible !important;
}
[data-testid="stDataEditor"] [role="row"] {
    align-items: flex-start !important;
}
[data-testid="stDataEditor"] td, [data-testid="stDataFrame"] td {
    line-height: 1.5 !important;
    vertical-align: top !important;
    border-bottom: 1px solid #eee !important;
}
section[data-testid="stSidebar"] { min-width: 320px !important; }
[data-testid="stSidebarCollapsedControl"] ~ div, 
[data-testid="collapsedControl"] ~ div,
[data-testid="stAppViewContainer"] > div:first-child {
    margin-left: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
}
[data-testid="stDataEditor"] > div:has([role="grid"]) { overflow-x: hidden !important; }
</style>
""",
    unsafe_allow_html=True,
)
