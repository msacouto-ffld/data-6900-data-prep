# Contract: scan_jargon

**FR(s)**: FR-120 | **Owner**: Script + LLM | **Freedom**: Medium | **Runtime**: Executed + LLM (conditional)

---

## Purpose

Hybrid jargon scan — script regex catches undefined acronyms, LLM fixes any violations found. Runs on the final report after persona verification.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| report_text | string | From generate_report | Yes |

## Outputs

Returns `final_report_text` (string — corrected if needed, unchanged if clean).

Console output:

```
🔎 Running jargon scan...
✅ Report complete — no jargon violations found.
```

Or:

```
🔎 Running jargon scan...
⚠️ {n} undefined term(s) found: {list} — adding definitions.
✅ Report complete — {n} term(s) corrected.
```

## Script Scan Logic

```python
ACRONYM_WHITELIST = {
    "CSV", "HTML", "JSON", "NaN", "PII", "ID", "LLM", "NL",
    "ASCII", "UTC", "ISO", "PDF", "API"
}
```

1. Find all uppercase sequences (2+ chars) via `\b[A-Z]{2,}\b`
2. Remove whitelisted terms
3. Check if remaining terms are defined on first use (pattern: `TERM (Full Name)` or `Full Name (TERM)`)
4. Return list of truly undefined terms

## LLM Fix (Conditional)

If undefined terms found:

- One targeted LLM call: "The following acronyms appear undefined in the report: {list}. For each, either define it on first use or replace it with plain language."
- LLM returns corrected sections
- Script applies corrections
- No second scan — one pass is sufficient

The persona verification step already checks for unexplained method-specific terms (e.g., "winsorize," "IQR") as part of its plain-language check. The script scan catches what the persona might miss (acronyms are easier to detect programmatically).

## Error Conditions

| Condition | Message |
|-----------|---------|
| Script scan fails | Skip scan; deliver report as-is with note: "Jargon scan could not be completed." |
| LLM fix call fails | Deliver report with undefined terms flagged: "⚠️ The following terms may need definition: {list}" |

Non-blocking — jargon scan failure does not halt the pipeline.

## Dependencies

- re (standard library)
- LLM (conditional)
