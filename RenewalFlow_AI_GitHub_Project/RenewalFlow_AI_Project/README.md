# RenewalFlow AI — Student Renewal Reconciliation Prototype

A practical, auditable prototype for the Bambinos.live AI Program Manager (Operations) take-home case.

## What it does
- Reads the four operational CSV tables and the active student/batch reference file.
- Normalises common column-name variations.
- Reconciles invoices, teacher renewal forms, booking requests, existing schedules, and student/batch references.
- Produces:
  1. `outputs/auto_approved.csv` — clean same-batch continuation candidates ready for scheduling.
  2. `outputs/flagged_exceptions.csv` — held records with reason codes and owner suggestions.
  3. `outputs/follow_up_messages.csv` — draft teacher/parent/Ops messages.
  4. `outputs/reconciliation_summary.json` — counts and run metadata.
- Includes a Streamlit dashboard for running and inspecting the reconciliation.

## Important dataset note
The `data/sample/` files are **synthetic demonstration data** created for local testing. They are not the official Bambinos assessment data and must not be represented as such. Before submission, download the five official CSVs from the assessment repository and replace the sample files while preserving the filenames (or update the paths in `config.json`). Then run the tests and inspect every output.

Official repository: https://github.com/bambinoslive/AI-PM-hiring-take-home-assignments

## Requirements
- Python 3.10+
- Install dependencies: `pip install -r requirements.txt`

## Run from project folder
For a quick demonstration using the included synthetic data, first copy the sample files into `data/`:
```bash
python src/use_sample_data.py
python src/reconcile.py
```
For the actual assessment, replace those copied files with the five official CSVs before running reconciliation.

Run the dashboard:
```bash
streamlit run src/dashboard.py
```

Run tests:
```bash
python -m unittest discover -s tests -v
```

## Input files
Place the official CSVs in `data/`:
- `1_invoices.csv`
- `2_faculty_form_unapproved.csv`
- `3_booking_requests.csv`
- `4_class_schedule_bookings.csv`
- `reference_active_batches_and_students.csv`

The program supports common column aliases, but real assessment headers may differ. If a required field is not detected, the program stops with a clear message rather than silently guessing. Update `src/reconcile.py`'s `ALIASES` map after reviewing the official headers.

## Decision policy
The prototype is deliberately conservative:
- Only an explicitly paid/settled invoice can pass payment validation.
- A student must resolve uniquely against the active reference.
- A teacher form and booking request must exist.
- The current and requested batch must match for the fast path.
- Existing schedule duplicates are held.
- Ambiguous identity, amount mismatch, missing evidence, partial/refunded/pending payment and batch changes are exceptions.
- It does not write to a live scheduling system. Approved output is a review-ready file for controlled downstream use.

An LLM is not used to approve payments. Financial and eligibility decisions are deterministic rules. AI can later assist with classifying free-text notes and drafting human-reviewed messages.

## Suggested GitHub structure
Keep the five official input CSVs private unless the assessment explicitly permits public sharing. Do not publish real student names, parent contacts, payment references or other personal data. Use synthetic samples in a public repository.

## Submission checklist
- [ ] Replace sample data with official data locally.
- [ ] Confirm actual column names and update aliases.
- [ ] Run reconciliation and inspect all exceptions.
- [ ] Run tests.
- [ ] Include anonymised/synthetic output examples only in public GitHub.
- [ ] Update the report with actual dataset findings.
