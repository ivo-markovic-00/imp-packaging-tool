import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import date, datetime, timezone, timedelta
import re
import math

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
# 3) Robust deadline parsing
# -----------------------------
TODAY = date.today()

Q_PAT = re.compile(r"\bq([1-4])\s*(\d{4})\b", re.IGNORECASE)
YEAR_PAT = re.compile(r"^\s*(\d{4})\s*$")
DATE_IN_TEXT_PAT = re.compile(
    r"(\d{4}-\d{2}-\d{2})|(\d{2}[-/]\d{2}[-/]\d{4})|(\d{4}/\d{2}/\d{2})"
)

def _end_of_quarter(y: int, q: int) -> date:
    month = {1: 3, 2: 6, 3: 9, 4: 12}[q]
    # last day of month
    if month in (1,3,5,7,8,10,12):
        day = 31
    elif month in (4,6,9,11):
        day = 30
    else:
        # Feb
        day = 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28
    return date(y, month, day)

def _excel_serial_to_date(x: float) -> date | None:
    # Excel origin 1899-12-30 (handles Excel's leap-year bug)
    try:
        base = datetime(1899, 12, 30, tzinfo=timezone.utc)
        dt = base + timedelta(days=float(x))
        return dt.date()
    except Exception:
        return None

def extract_deadline_as_date(val) -> date | None:
    """Return a date for clean dates, 'Estimated 2026-..', 'Q2 2026', Excel serials, or None."""
    if pd.isna(val):
        return None

    # If already a date/datetime
    if isinstance(val, pd.Timestamp):
        return val.date()
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    s = str(val).strip()
    if not s:
        return None

    # Quarter notation (Q1 2026)
    m = Q_PAT.search(s)
    if m:
        q = int(m.group(1)); y = int(m.group(2))
        return _end_of_quarter(y, q)

    # Year only ("2026")
    m = YEAR_PAT.match(s)
    if m:
        y = int(m.group(1))
        return date(y, 12, 31)

    # Any ISO or common date found in text (e.g., "Estimated 2026-01-01")
    m = DATE_IN_TEXT_PAT.search(s)
    if m:
        frag = m.group(0)
        # Try multiple parsers
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(frag, fmt).date()
            except Exception:
                pass
        # Fallback: pandas is good at free parsing
        try:
            return pd.to_datetime(frag, errors="raise").date()
        except Exception:
            pass

    # Pure numeric (possibly Excel serial)
    try:
        if isinstance(val, (int, float)) or (isinstance(s, str) and re.fullmatch(r"\d+(\.\d+)?", s)):
            num = float(val)
            # Heuristic: Excel serials are usually > 20000
            if num > 20000:
                d = _excel_serial_to_date(num)
                if d:
                    return d
    except Exception:
        pass

    # Last resort: pandas generic parser
    try:
        parsed = pd.to_datetime(s, errors="coerce")
        if pd.notna(parsed):
            return parsed.date()
    except Exception:
        pass

    return None

def categorize_deadline(deadline_val, status_val) -> str:
    """Three buckets: In force / Due < 1 year / Due > 1 year."""
    # Respect explicit status
    if isinstance(status_val, str) and "in force" in status_val.lower():
        return "In force"

    d = extract_deadline_as_date(deadline_val)
    if d is None:
        # With only 3 buckets, treat unknowns as long horizon (safer than 'in force')
        return "Due > 1 year"

    if d <= TODAY:
        return "In force"
    elif (d - TODAY).days <= 365:
        return "Due < 1 year"
    else:
        return "Due > 1 year"

# Compute once
df["__deadline_date__"] = df["Deadline"].apply(extract_deadline_as_date)
df["Deadline Category"] = df.apply(
    lambda r: categorize_deadline(r.get("Deadline"), r.get("Status")), axis=1
)

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
    "Deadline",           # show original text
    "Status",
    "Evidence to Collect",
]

# Show a clean date preview underneath if you ever want (hidden by default)
# filtered["Parsed Deadline"] = filtered["__deadline_date__"].astype(str).replace("NaT", "")

# Ensure Deadline prints nicely (no 00:00:00); if datetime slipped through
if "Deadline" in filtered.columns:
    # If a Timestamp sneaks in, convert to date string
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
