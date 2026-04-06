# Contract: scan_pii

**FR(s):** FR-008 | **Owner:** Script + LLM | **Freedom:** Medium | **Runtime:** Executed

## Purpose

Two-layer PII detection: heuristic pre-scan on column names (Script) + LLM value inspection on unflagged columns only. Produces PII scan results consumed by the LLM for the NL report. Runs after ydata-profiling completes.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df | pandas DataFrame | Loaded during validation | Yes |
| validation_result | dict | DM-002 | Yes |

## Outputs

On success: Returns `pii_scan` list (DM-004 schema):

```python
[
    {
        "column_name": "string",
        "pii_type": "string",
        "pii_category": "string",
        "detection_source": "string",
        "confidence": "string"
    }
]
```

On success — console output (PII found):

```
🔒 Scanning for potential PII...
⚠️ PII Warning: Column '{col}' may contain {PII_type} PII
   ({detection_source}). Proceed with caution.
...
PII scan complete. {n} columns flagged.
```

On success — console output (no PII):

```
🔒 Scanning for potential PII...
✅ No potential PII detected in this dataset.
```

## Layer 1 — Heuristic Pre-Scan (Script)

Word-boundary matching on column names. Column names normalized to lowercase and split on delimiters (`_`, `-`, ` `, `.`).

| PII Type | Match Tokens |
|----------|-------------|
| direct_name | name, first_name, last_name, full_name, surname, customer_name, person |
| direct_contact | email, phone, telephone, mobile, cell, address, street, city, state, country |
| direct_identifier | ssn, social_security, passport, driver_license, national_id, license_number |
| indirect | dob, date_of_birth, birth_date, birthday, zip, zip_code, postal_code, job_title, occupation, age, gender, sex, race, ethnicity, religion |
| financial | account_number, account_no, credit_card, card_number, routing_number, iban, transaction_id, bank, salary, income |

Matches produce `confidence: "high"`, `detection_source: "column_name_pattern"`.

## Layer 2 — LLM Value Inspection

**Optimization:** The LLM value inspection runs only on columns **not already flagged by Layer 1**. Columns flagged by the heuristic pre-scan are already identified — sending their values to the LLM adds cost without benefit. Layer 2 focuses on columns with non-descriptive names where the heuristic has no signal.

The LLM receives the first 5 non-null values per unflagged column (from `df[col].dropna().head(5).tolist()`). The LLM analyzes whether values resemble PII patterns (email format, phone format, SSN format, etc.).

Matches produce `confidence: "medium"`, `detection_source: "value_pattern_llm"`.

**Privacy constraint:** The NL report must include column names and PII categories only — never raw PII values.

## Error Conditions

| Condition | Message |
|-----------|---------|
| DataFrame is None or empty | "Pipeline error: no DataFrame available for PII scan. Re-run from the beginning." |

PII scan does not halt the pipeline — findings are warnings only (V1 behavior per constitution).

## Dependencies

- `pandas` — pre-installed
- `re` — standard library
- LLM (Claude 4.5 Sonnet) — for Layer 2