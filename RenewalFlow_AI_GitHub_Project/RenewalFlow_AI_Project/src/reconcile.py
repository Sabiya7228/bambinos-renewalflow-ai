#!/usr/bin/env python3
"""Conservative CSV reconciliation engine for student renewal workflows."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

ALIASES = {
    "invoice_id": ["invoice_id", "invoiceid", "invoice", "invoice_number", "invoice_no", "id"],
    "student_id": ["student_id", "studentid", "child_id", "learner_id"],
    "teacher_id": ["teacher_id", "faculty_id", "teacherid", "facultyid"],
    "parent_name": ["parent_name", "guardian_name", "customer_name"],
    "student_name": ["student_name", "child_name", "learner_name", "name"],
    "phone": ["phone", "phone_number", "mobile", "parent_phone", "contact_number"],
    "email": ["email", "email_id", "parent_email"],
    "amount": ["amount", "paid_amount", "invoice_amount", "total_amount", "amount_paid"],
    "payment_status": ["payment_status", "status", "invoice_status", "payment_state"],
    "batch_id": ["batch_id", "batchid", "current_batch_id", "requested_batch_id"],
    "requested_batch_id": ["requested_batch_id", "new_batch_id", "batch_id", "batch"],
    "booking_request_id": ["booking_request_id", "request_id", "booking_id", "id"],
    "schedule_id": ["schedule_id", "class_schedule_booking_id", "booking_id"],
    "form_id": ["form_id", "faculty_form_id", "id"],
    "created_at": ["created_at", "submitted_at", "created_date", "timestamp"],
    "days": ["days", "class_days", "preferred_days"],
    "time": ["time", "class_time", "preferred_time", "slot"],
    "active_status": ["active_status", "student_status", "status", "is_active"],
}
def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).strip().lower()).strip("_")

def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    return pd.read_csv(path, dtype=str).fillna("")

def find_col(df, key, required=False):
    cols = {norm(c): c for c in df.columns}
    for alias in ALIASES.get(key, [key]):
        if norm(alias) in cols:
            return cols[norm(alias)]
    if required:
        raise ValueError(f"Could not find required column '{key}'. Available columns: {list(df.columns)}. Update ALIASES in src/reconcile.py.")
    return None

def val(row, df, key, default=""):
    c = find_col(df, key)
    return str(row[c]).strip() if c else default

def clean_amount(x):
    try:
        return round(float(re.sub(r"[^0-9.\\-]", "", str(x))), 2)
    except Exception:
        return None

def is_paid(status, paid_statuses):
    return norm(status) in {norm(x) for x in paid_statuses}

def first_by_key(df, key):
    c = find_col(df, key)
    if not c:
        return {}
    out = {}
    for _, r in df.iterrows():
        k = val(r, df, key)
        if k and k not in out:
            out[k] = r
    return out

def run(config_path=None):
    base = Path(__file__).resolve().parents[1]
    cfg = json.loads((config_path or base / "config.json").read_text())
    inp, out = base / cfg["input_dir"], base / cfg["output_dir"]
    out.mkdir(parents=True, exist_ok=True)
    f = cfg["files"]
    invoices = load_csv(inp / f["invoices"])
    forms = load_csv(inp / f["faculty_forms"])
    requests = load_csv(inp / f["booking_requests"])
    schedules = load_csv(inp / f["schedule_bookings"])
    ref = load_csv(inp / f["reference"])
    # Required fields are checked explicitly before processing.
    invoice_id_col = find_col(invoices, "invoice_id", True)
    form_invoice_col = find_col(forms, "invoice_id", True)
    request_invoice_col = find_col(requests, "invoice_id", True)
    ref_student_col = find_col(ref, "student_id", True)
    invoice_map = first_by_key(invoices, "invoice_id")
    form_map = first_by_key(forms, "invoice_id")
    request_map = first_by_key(requests, "invoice_id")
    student_map = first_by_key(ref, "student_id")
    schedule_student_col = find_col(schedules, "student_id")
    existing_scheduled = set()
    if schedule_student_col:
        existing_scheduled = set(schedules[schedule_student_col].astype(str).str.strip()) - {""}

    approved, exceptions, messages = [], [], []
    paid_statuses = cfg.get("paid_statuses", ["paid", "success", "settled", "completed"])

    for _, inv in invoices.iterrows():
        iid = val(inv, invoices, "invoice_id")
        sid = val(inv, invoices, "student_id")
        status = val(inv, invoices, "payment_status")
        amount = clean_amount(val(inv, invoices, "amount"))
        reasons = []
        owner = "Operations"
        action = "Review invoice and linked renewal evidence."

        if not iid:
            reasons.append("MISSING_INVOICE_ID")
        if not is_paid(status, paid_statuses):
            reasons.append("PAYMENT_NOT_SETTLED")
            owner, action = "Finance / Operations", "Verify authoritative payment status; do not schedule."
        form = form_map.get(iid)
        req = request_map.get(iid)
        if not form:
            reasons.append("MISSING_TEACHER_FORM")
            owner, action = "Teacher", "Submit or correct the renewal form with the correct invoice reference."
        if not req:
            reasons.append("MISSING_BOOKING_REQUEST")
            owner, action = "Operations", "Create or investigate the missing booking request after validating the form."

        if form:
            fsid = val(form, forms, "student_id")
            if sid and fsid and sid != fsid:
                reasons.append("STUDENT_ID_MISMATCH")
                owner, action = "Operations", "Verify the student identity against the source records."
            fa = clean_amount(val(form, forms, "amount"))
            if amount is not None and fa is not None and amount != fa:
                reasons.append("AMOUNT_MISMATCH")
                owner, action = "Finance / Operations", "Compare invoice and form amounts; resolve before approval."

        if not sid or sid not in student_map:
            reasons.append("STUDENT_NOT_UNIQUELY_MATCHED")
            owner, action = "Operations", "Resolve the student against the active student reference; do not guess from contact details."

        if req and sid:
            req_batch = val(req, requests, "requested_batch_id")
            ref_row = student_map.get(sid)
            current_batch = val(ref_row, ref, "batch_id") if ref_row is not None else ""
            if req_batch and current_batch and req_batch != current_batch:
                reasons.append("BATCH_CHANGE_REQUIRED")
                owner, action = "Scheduling / Operations", "Review requested batch, eligibility and available capacity."
            if not req_batch or not current_batch:
                reasons.append("BATCH_DATA_MISSING")
                owner, action = "Scheduling / Operations", "Confirm current and requested batch before scheduling."

        if sid and sid in existing_scheduled:
            reasons.append("EXISTING_SCHEDULE_REVIEW")
            owner, action = "Operations", "Check whether this is a valid continuation or duplicate before creating another schedule."

        # De-duplicate reason codes while preserving order.
        reasons = list(dict.fromkeys(reasons))
        common = {
            "invoice_id": iid, "student_id": sid,
            "student_name": val(inv, invoices, "student_name"),
            "payment_status": status, "invoice_amount": amount,
            "teacher_id": val(form, forms, "teacher_id") if form is not None else "",
            "booking_request_id": val(req, requests, "booking_request_id") if req is not None else "",
        }
        if reasons:
            exceptions.append({**common, "reason_codes": "|".join(reasons),
                               "assigned_owner": owner, "recommended_next_action": action})
            messages.append({
                "invoice_id": iid, "recipient": owner,
                "message_type": "exception_alert",
                "draft_message": f"Renewal review required for invoice {iid}, student {sid or 'unmatched'}. Reason(s): {', '.join(reasons)}. Next action: {action}"
            })
        else:
            approved.append({**common,
                "requested_batch_id": val(req, requests, "requested_batch_id"),
                "days": val(req, requests, "days"),
                "time": val(req, requests, "time"),
                "decision": "AUTO_APPROVED_CANDIDATE",
                "note": "All configured prototype checks passed. Verify live capacity and schedule-write permissions before production use."
            })
            messages.append({
                "invoice_id": iid, "recipient": "Parent",
                "message_type": "schedule_ready_draft",
                "draft_message": f"Hello {val(inv, invoices, 'parent_name') or 'there'}, your renewal payment has been verified. We are preparing the next class schedule and will send confirmation once the booking is completed."
            })

    # Detect duplicate invoice IDs explicitly.
    inv_id_series = invoices[invoice_id_col].astype(str).str.strip()
    duplicates = set(inv_id_series[inv_id_series.duplicated(keep=False)]) - {""}
    if duplicates:
        for iid in sorted(duplicates):
            exceptions.append({"invoice_id": iid, "student_id": "", "reason_codes": "DUPLICATE_INVOICE_ID",
                               "assigned_owner": "Operations", "recommended_next_action": "Investigate duplicate invoice records before processing."})

    pd.DataFrame(approved).to_csv(out / "auto_approved.csv", index=False)
    pd.DataFrame(exceptions).to_csv(out / "flagged_exceptions.csv", index=False)
    pd.DataFrame(messages).to_csv(out / "follow_up_messages.csv", index=False)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "invoice_rows": int(len(invoices)),
        "auto_approved_candidates": int(len(approved)),
        "flagged_exception_rows": int(len(exceptions)),
        "follow_up_drafts": int(len(messages)),
        "important_note": "Candidates are not live bookings. Review rules and source data before any production write."
    }
    (out / "reconciliation_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()
    run(args.config)
