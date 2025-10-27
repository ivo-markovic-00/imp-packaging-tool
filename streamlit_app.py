import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="NL/EU Packaging Compliance — Prototype", layout="wide")

# ---------- 0) Settings ----------
DATA_PATH = Path("data/final_table.xlsx")  # put your file here

# Department choices + short explanations (tooltips)
DEPT_DESCRIPTIONS = {
    "Design & R&D": "Develops formats/materials; ensures recyclability, minimisation, and composition rules.",
    "Supply Chain & Procurement": "Sources compliant materials/suppliers; manages recycled content, certifications, and chemical restrictions via contracts.",
    "Marketing & Labelling": "Manages environmental claims, artwork, and mandatory packaging labels (EU/NL).",
    "Finance & EPR": "Handles producer registration, EPR reporting & fees, and eco-modulation budgets.",
    "Operations & Logistics": "Runs filling, reuse/cleaning/return systems, DRS participation, and collection logistics.",
    "Compliance & Data Reporting": "Maintains DoC/supplier/test evidence, tracks legal changes, and ensures accurate regulatory reporting."
}
DEPT_LIST = ["All (General)"] + list(DEPT_DESCRIPTIONS.keys())

# Keywords → Department mapping (used if your Excel lacks a Department column)
KEYWORD_MAP = [
    (["design","r&d","material","recycl","reuse","labell"], "Design & R&D"),
    (["supply","procure","supplier","sourcing","pcr","contract"], "Supply Chain & Procurement"),
    (["marketing","claim","label","logo","marking"], "Marketing & Labelling"),
    (["finance","epr","fee","producer register","afvalfonds","verpact"], "Finance & EPR"),
    (["operation","logist","drs","return","washing","cleaning","collection"], "Operations & Logistics"),
    (["compliance","legal","doc","fcm","reach","report","csrd","esrs","evidence"], "Compliance & Data Reporting"),
]

# Columns to show in the results
RESULT_COLS = [
    "Trigger", "Regulation", "Reference", "Applicability",
    "Consequence", "Deadline", "Status", "Evidence to Collect"
]

# ---------- 1) Load ----------
@st.cache_data(show_spinner=False)
def load_excel(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    # Normalise column names (trim spaces)
    df.columns = [c.strip() for c in df.columns]
    return df

if not DATA_PATH.exists():
    st.error("Excel not found. Upload your file to `data/final_table.xlsx` in the repo.")
    st.stop()

df = load_excel(DATA_PATH)

# ---------- 2) Ensure we have a Department column ----------
def infer_department(row: pd.Series) -> str:
    # Prefer existing column if present
    for col in ["Department", "Business Function / Focus", "Main Function Impacted"]:
        if col in row.index and pd.notna(row[col]):
            text = str(row[col]).lower()
            for kws, dept in KEYWORD_MAP:
                if any(k in text for k in kws):
                    return dept
    # Fallback: search in Description/Trigger
    for col in ["Description", "Trigger"]:
        if col in row.index and pd.notna(row[col]):
            text = str(row[col]).lower()
            for kws, dept in KEYWORD_MAP:
                if any(k in text for k in kws):
                    return dept
    return "Compliance & Data Reporting"  # safe default owner

if "Department" not in df.columns:
    df["Department"] = df.apply(infer_department, axis=1)

# ---------- 3) Sidebar filters ----------
st.sidebar.header("Filters")

dept_choice = st.sidebar.selectbox("Department", DEPT_LIST, index=0, help="Pick who you are / where you work.")
if dept_choice != "All (General)":
    st.sidebar.info(DEPT_DESCRIPTIONS[dept_choice])

# Optional: quick search
q = st.sidebar.text_input("Search text (optional)", placeholder="Search in Trigger / Description / Regulation")

# ---------- 4) Apply filters ----------
filtered = df.copy()

if dept_choice != "All (General)":
    filtered = filtered[filtered["Department"] == dept_choice]

if q:
    qlow = q.lower()
    hay_cols = [c for c in ["Trigger","Description","Regulation","Applicability","Evidence to Collect"] if c in filtered.columns]
    mask = False
    for c in hay_cols:
        mask = mask | filtered[c].astype(str).str.lower().str.contains(qlow, na=False)
    filtered = filtered[mask]

# Keep only known result columns if they exist
cols_to_show = [c for c in RESULT_COLS if c in filtered.columns]
cols_to_show = (["Department"] if "Department" in filtered.columns else []) + cols_to_show
if not cols_to_show:
    cols_to_show = filtered.columns.tolist()

st.markdown("### Applicable business triggers")
st.caption("Filtered by your selections. Download to CSV for sharing or analysis.")
st.dataframe(filtered[cols_to_show], use_container_width=True, hide_index=True)

# ---------- 5) Download ----------
csv = filtered[cols_to_show].to_csv(index=False).encode("utf-8")
st.download_button("Download filtered CSV", data=csv, file_name="filtered_triggers.csv", mime="text/csv")

# ---------- 6) Footnote ----------
with st.expander("About this prototype"):
    st.write("""
    • Data is loaded read-only from your Excel.  
    • Department is taken from your file if present; otherwise inferred from keywords.  
    • Use the search box to refine results.  
    • Update the Excel and redeploy to refresh content.
    """)
