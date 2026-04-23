"""Stage 2 — PII scan for Skill B.

Two paths:
1. If Skill A metadata is present, read pii_warnings from it.
2. If not, run Layer 1 heuristic (same token lists as Skill A).

Does NOT halt the pipeline — warnings only.

Contract: contracts/scan-pii.md
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

import pandas as pd

from mistake_log import log_event


# Same token lists as Skill A — from the constitution
PII_TOKEN_LISTS: Dict[str, List[str]] = {
    "direct_name": [
        "name", "first_name", "last_name", "full_name", "surname",
        "customer_name", "person",
    ],
    "direct_contact": [
        "email", "phone", "telephone", "mobile", "cell",
        "address", "street", "city", "state", "country",
    ],
    "direct_identifier": [
        "ssn", "social_security", "passport", "driver_license",
        "national_id", "license_number",
    ],
    "indirect": [
        "dob", "date_of_birth", "birth_date", "birthday",
        "zip", "zip_code", "postal_code", "job_title", "occupation",
        "age", "gender", "sex", "race", "ethnicity", "religion",
    ],
    "financial": [
        "account_number", "account_no", "credit_card", "card_number",
        "routing_number", "iban", "transaction_id", "bank",
        "salary", "income",
    ],
}

PII_CATEGORY_LABELS = {
    "direct_name": "Direct PII — names",
    "direct_contact": "Direct PII — contact information",
    "direct_identifier": "Direct PII — government ID",
    "indirect": "Indirect PII — quasi-identifier",
    "financial": "Financial PII",
}

_DELIM_RE = re.compile(r"[_\-\s\.]+")


def _heuristic_scan(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Layer 1 heuristic: word-boundary match on column names."""
    flags: List[Dict[str, Any]] = []
    for col in df.columns:
        tokens = [t for t in _DELIM_RE.split(str(col).lower().strip()) if t]
        token_set = set(tokens)
        for pii_type, patterns in PII_TOKEN_LISTS.items():
            matched = False
            for pat in patterns:
                if "_" in pat:
                    pat_tokens = pat.split("_")
                    for i in range(len(tokens) - len(pat_tokens) + 1):
                        if tokens[i:i + len(pat_tokens)] == pat_tokens:
                            matched = True
                            break
                else:
                    if pat in token_set:
                        matched = True
                if matched:
                    break
            if matched:
                flags.append({
                    "column_name": str(col),
                    "pii_type": pii_type,
                    "pii_category": PII_CATEGORY_LABELS[pii_type],
                    "source": "from_heuristic_scan",
                })
                break  # one flag per column
    return flags


def scan_pii(
    df: pd.DataFrame,
    validation_result: Dict[str, Any],
    log_path: str,
) -> List[Dict[str, Any]]:
    """Scan for PII. Returns the pii_flags list for DM-003.

    Populates ``validation_result["pii_flags"]`` in place.
    """
    # Path 1: read from Skill A metadata
    pii_from_metadata = validation_result.get("_pii_from_metadata", [])
    if pii_from_metadata:
        flags: List[Dict[str, Any]] = []
        for entry in pii_from_metadata:
            flags.append({
                "column_name": entry.get("column_name"),
                "pii_type": entry.get("pii_type"),
                "pii_category": entry.get("pii_category", ""),
                "source": "from_skill_a_json",
            })
        print(
            f"🔒 PII scan: loaded {len(flags)} flags from Skill A "
            "transform metadata"
        )
        for f in flags:
            print(
                f"⚠️ Column '{f['column_name']}' — "
                f"{f['pii_type']} PII ({f['pii_category']})"
            )
            log_event(
                log_path, "pii_warning", "scan_pii",
                f"Column '{f['column_name']}' flagged as {f['pii_type']} PII "
                f"(source: Skill A metadata)",
                "LLM will note PII in proposals",
                columns=[f["column_name"]],
            )
        print("The LLM will note these columns when proposing features.")
    else:
        # Path 2: heuristic scan
        print("🔒 Running PII scan (heuristic — column names only)...")
        flags = _heuristic_scan(df)
        if flags:
            for f in flags:
                print(
                    f"⚠️ Column '{f['column_name']}' may contain "
                    f"{f['pii_type']} PII — {f['pii_category']}."
                )
                log_event(
                    log_path, "pii_warning", "scan_pii",
                    f"Column '{f['column_name']}' flagged as "
                    f"{f['pii_type']} PII (heuristic scan)",
                    "Consider excluding from feature engineering",
                    columns=[f["column_name"]],
                )
            n_clear = len(df.columns) - len(flags)
            print(f"✅ {n_clear} of {len(df.columns)} columns clear.")
        else:
            print("🔒 PII scan complete.")
            print("✅ No potential PII detected in this dataset.")

    validation_result["pii_flags"] = flags
    return flags


if __name__ == "__main__":
    df = pd.DataFrame({
        "customer_name": ["Alice"],
        "email": ["a@x.com"],
        "zip_code": [12345],
        "account_number": ["ACC123"],
        "sales_amount": [100.0],
        "quantity": [5],
    })
    vr = {"_pii_from_metadata": []}
    import tempfile, os
    log = os.path.join(tempfile.gettempdir(), "test-pii.md")
    from mistake_log import init_mistake_log
    init_mistake_log(log, "test")
    flags = scan_pii(df, vr, log)
    print(f"\nFlags: {len(flags)}")
    for f in flags:
        print(f"  {f['column_name']}: {f['pii_type']}")
    os.remove(log)
