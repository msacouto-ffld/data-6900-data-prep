"""Stage 5 — Scan for PII.

Two-layer PII detection:

- **Layer 1** (this script): word-boundary heuristic matching on column names
  against the 5 PII token lists from the contract. Matches produce
  ``confidence: "high"``, ``detection_source: "column_name_pattern"``.

- **Layer 2** (LLM, orchestrated separately): for columns **not flagged by
  Layer 1**, the LLM inspects the first 5 non-null values per column and
  decides whether they match PII patterns. Matches produce
  ``confidence: "medium"``, ``detection_source: "value_pattern_llm"``.

This script implements Layer 1 and exposes ``get_layer_2_candidates()``
to build the set of columns the orchestrator should hand to the LLM.

Contract: ``contracts/scan-pii.md``
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

import pandas as pd


# Delimiter characters used to split column names into tokens.
# From the contract: underscore, hyphen, space, dot.
_DELIMITER_RE = re.compile(r"[_\-\s\.]+")


# Layer 1 token lists per contract §scan-pii.md
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


# Human-readable category labels for DM-004 `pii_category` field
PII_CATEGORY_LABELS: Dict[str, str] = {
    "direct_name": "Direct PII — personal name",
    "direct_contact": "Direct PII — contact information",
    "direct_identifier": "Direct PII — government/official identifier",
    "indirect": "Indirect PII — quasi-identifier",
    "financial": "Financial PII",
}


def _tokenize_column_name(col_name: str) -> List[str]:
    """Lowercase + split on delimiters. Returns non-empty tokens only."""
    lowered = str(col_name).lower().strip()
    tokens = [t for t in _DELIMITER_RE.split(lowered) if t]
    return tokens


def _match_tokens_to_pii(
    tokens: List[str],
) -> List[Tuple[str, str]]:
    """Match a column's tokens against the 5 PII token lists.

    Uses both single-token matching and multi-token phrase matching
    (e.g. ``['first', 'name']`` matches ``first_name``). Returns a
    list of ``(pii_type, matched_token)`` pairs — a column may match
    more than one PII type (e.g. ``home_phone_number`` matches
    ``direct_contact`` via ``phone``).
    """
    if not tokens:
        return []

    token_set = set(tokens)
    # Reconstruct the underscore-joined form for multi-word phrase matching
    joined = "_".join(tokens)

    matches: List[Tuple[str, str]] = []
    seen_pii_types: set[str] = set()

    for pii_type, pattern_tokens in PII_TOKEN_LISTS.items():
        if pii_type in seen_pii_types:
            continue
        for pattern in pattern_tokens:
            # Multi-token patterns in the list use underscores
            if "_" in pattern:
                # Check whether the joined form contains the full pattern
                # as a delimited subsequence (e.g. "customer_name" in
                # "customer_name_full").
                if pattern == joined:
                    matches.append((pii_type, pattern))
                    seen_pii_types.add(pii_type)
                    break
                # Also match if the pattern's tokens are all present and
                # contiguous in the column tokens (e.g. "first_name"
                # matches ['first', 'name', 'clean']).
                pattern_tokens_split = pattern.split("_")
                for i in range(len(tokens) - len(pattern_tokens_split) + 1):
                    if tokens[i:i + len(pattern_tokens_split)] == pattern_tokens_split:
                        matches.append((pii_type, pattern))
                        seen_pii_types.add(pii_type)
                        break
                if pii_type in seen_pii_types:
                    break
            else:
                # Single-token pattern: word-boundary match means the
                # token must appear as a complete delimiter-separated token.
                if pattern in token_set:
                    matches.append((pii_type, pattern))
                    seen_pii_types.add(pii_type)
                    break
    return matches


def scan_pii_layer_1(
    df: pd.DataFrame,
    validation_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Layer 1 — heuristic column-name PII scan.

    Returns a DM-004 list of entries for columns whose names match
    a PII token. Columns with no match are not represented in the
    output (see ``get_layer_2_candidates`` for those).
    """
    if df is None:
        raise ValueError(
            "Pipeline error: no DataFrame available for PII scan. "
            "Re-run from the beginning."
        )

    print("🔒 Scanning for potential PII...")

    results: List[Dict[str, Any]] = []
    for col_name in df.columns:
        tokens = _tokenize_column_name(col_name)
        matches = _match_tokens_to_pii(tokens)
        for pii_type, _matched_token in matches:
            results.append({
                "column_name": str(col_name),
                "pii_type": pii_type,
                "pii_category": PII_CATEGORY_LABELS[pii_type],
                "detection_source": "column_name_pattern",
                "confidence": "high",
            })

    return results


def get_layer_2_candidates(
    df: pd.DataFrame,
    layer_1_results: List[Dict[str, Any]],
) -> Dict[str, List[Any]]:
    """Build the payload for Layer 2 LLM inspection.

    Returns a dict mapping column name → up to 5 non-null sample values.
    Only columns NOT already flagged by Layer 1 are included — per the
    contract's optimization note.

    The orchestrator passes this dict to the LLM along with the system
    prompt from PROMPTS.md § PII Layer 2. The LLM responds with a list
    of detected PII columns, which is then appended to the scan results
    via ``append_layer_2_results``.
    """
    flagged = {entry["column_name"] for entry in layer_1_results}
    candidates: Dict[str, List[Any]] = {}
    for col_name in df.columns:
        col_name_str = str(col_name)
        if col_name_str in flagged:
            continue
        # Skip all-missing columns — nothing to inspect
        non_null = df[col_name].dropna()
        if len(non_null) == 0:
            continue
        samples = non_null.head(5).tolist()
        candidates[col_name_str] = samples
    return candidates


def append_layer_2_results(
    layer_1_results: List[Dict[str, Any]],
    layer_2_findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge Layer 2 LLM findings into the DM-004 result list.

    Each entry in ``layer_2_findings`` should come from the LLM with
    at least ``column_name`` and ``pii_type``. This function fills in
    ``pii_category``, ``detection_source``, and ``confidence``.
    """
    merged = list(layer_1_results)
    for finding in layer_2_findings or []:
        col_name = finding.get("column_name")
        pii_type = finding.get("pii_type")
        if not col_name or pii_type not in PII_TOKEN_LISTS:
            continue
        merged.append({
            "column_name": str(col_name),
            "pii_type": pii_type,
            "pii_category": PII_CATEGORY_LABELS[pii_type],
            "detection_source": "value_pattern_llm",
            "confidence": "medium",
        })
    return merged


def print_scan_summary(results: List[Dict[str, Any]]) -> None:
    """Emit the console output described in the contract."""
    if not results:
        print("✅ No potential PII detected in this dataset.")
        return

    # One line per finding
    seen_pairs: set[Tuple[str, str]] = set()
    for entry in results:
        pair = (entry["column_name"], entry["pii_type"])
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        source_label = (
            "column name pattern"
            if entry["detection_source"] == "column_name_pattern"
            else "value pattern detected by LLM"
        )
        print(
            f"⚠️ PII Warning: Column '{entry['column_name']}' may contain "
            f"{entry['pii_type']} PII ({source_label}). Proceed with caution."
        )
    unique_cols = {r["column_name"] for r in results}
    print(f"\nPII scan complete. {len(unique_cols)} column(s) flagged.")


if __name__ == "__main__":
    import sys
    from validate_input import validate_input

    if len(sys.argv) != 2:
        print("Usage: python scan_pii.py <path-to-csv>")
        sys.exit(1)

    df, vr = validate_input(sys.argv[1])
    layer_1 = scan_pii_layer_1(df, vr)
    print_scan_summary(layer_1)

    candidates = get_layer_2_candidates(df, layer_1)
    print(f"\nLayer 2 candidates: {len(candidates)} columns")
    for col, samples in list(candidates.items())[:3]:
        print(f"  {col}: {samples}")
