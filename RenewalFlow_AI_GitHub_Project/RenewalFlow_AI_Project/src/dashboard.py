from pathlib import Path
import json
import pandas as pd
import streamlit as st
from reconcile import run

BASE = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="RenewalFlow AI | Ops Dashboard", layout="wide")
st.title("RenewalFlow AI")
st.caption("Student renewal reconciliation • Prototype dashboard")
st.warning("This is a decision-support prototype. It does not write to live schedules or independently approve financial transactions.")

if st.button("Run reconciliation", type="primary"):
    try:
        summary = run()
        st.success("Reconciliation completed. Outputs have been refreshed.")
    except Exception as e:
        st.error(str(e))

summary_path = BASE / "outputs" / "reconciliation_summary.json"
if summary_path.exists():
    summary = json.loads(summary_path.read_text())
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Invoices processed", summary.get("invoice_rows", 0))
    c2.metric("Auto-approval candidates", summary.get("auto_approved_candidates", 0))
    c3.metric("Exception rows", summary.get("flagged_exception_rows", 0))
    c4.metric("Message drafts", summary.get("follow_up_drafts", 0))
else:
    st.info("Run the reconciliation to populate dashboard metrics.")

tabs = st.tabs(["Auto-approved candidates", "Flagged exceptions", "Follow-up drafts"])
for tab, filename in zip(tabs, ["auto_approved.csv", "flagged_exceptions.csv", "follow_up_messages.csv"]):
    with tab:
        path = BASE / "outputs" / filename
        if path.exists():
            df = pd.read_csv(path).fillna("")
            st.dataframe(df, use_container_width=True)
            st.download_button(f"Download {filename}", df.to_csv(index=False), file_name=filename, mime="text/csv")
        else:
            st.caption("No output yet.")
