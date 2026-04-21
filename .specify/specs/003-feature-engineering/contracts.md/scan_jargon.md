# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

### Contract: scan_jargon
**FR(s):** FR-214 | **Owner:** Script (Layer 1) + LLM (Layer 2) | **Freedom:** Low | **Runtime:** Mixed

### Purpose
Ensures the transformation report and data dictionary are readable by non-specialist users (data-adjacent analysts, stakeholders, clients). Runs a two-layer check: a script flags technical terms missing plain-language explanations, and a single targeted LLM call rewrites flagged sections. Non-blocking — the Data Analyst verification (Stage 7) is Layer 2 and catches anything the script misses.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| transformation_report | string | DM-010 (raw markdown before delivery) | Yes |
| data_dictionary | string | DM-011 (raw markdown before delivery) | Yes |
| JARGON_TERMS | list[str] | Constant defined in this contract | Yes |

### Outputs

Returns a tuple `(rewritten_report, rewritten_dictionary, jargon_findings)`. `jargon_findings` is a list of dicts matching:
```
{
  "term": str,          # e.g. "z-score"
  "location": str,      # "report" | "dictionary"
  "context_window": str, # ~200 chars around the term
  "explanation_found": bool,
  "rewritten": bool
}
```

Console output (no findings):
```
🔍 Jargon scan: no technical terms missing explanations.
```

Console output (findings, rewrite invoked):
```
🔍 Jargon scan: {n} term(s) need plain-language explanation.
   Terms flagged: {comma-separated list}
   Rewriting affected sections...
✅ Sections rewritten. No meaning changes, only added clarity.
```

### JARGON_TERMS List (~20 terms)

The script scans for these exact terms (case-insensitive, word-boundary matching):

| Term | Domain |
|------|--------|
| one-hot encoding | categorical encoding |
| label encoding | categorical encoding |
| z-score | scaling |
| standard score | scaling |
| min-max scaling | scaling |
| normalization | scaling |
| standardization | scaling |
| cardinality | categorical |
| target encoding | categorical |
| groupby | aggregation |
| aggregation | aggregation |
| percentile | statistics |
| interquartile range | statistics |
| IQR | statistics |
| standard deviation | statistics |
| monotonic | statistics |
| correlation | statistics |
| target leakage | modeling |
| data leakage | modeling |
| dtype | data types |
| NaN | data types |

Teams may extend this list in a separate config file without changing this contract.

### Layer 1: Script Scan

For each term in `JARGON_TERMS`:
1. Search `transformation_report` and `data_dictionary` (case-insensitive) with word-boundary regex `r'\b{term}\b'` — substring matches don't count (avoids flagging "standardization" when the text already says "standard" in an unrelated context).
2. For each match, extract ~200 characters of surrounding context (100 before, 100 after).
3. Check whether an explanation is present within that window. An "explanation" is defined as ANY of:
   - A parenthetical right after the term: `z-score (standardized value where 0 is the mean and 1 is one standard deviation away)`
   - An em-dash definition: `z-score — the number of standard deviations from the mean`
   - An "i.e." or "that is" clause: `z-score, i.e. the standardized value`
   - The term appears inside a parenthetical that's already defining it: `(z-score — ...)`
4. If no explanation is found in the window, record the term + location + context in `jargon_findings`.

Layer 1 is pure regex + string matching. No LLM call.

### Layer 2: LLM Rewrite (only if Layer 1 finds flags)

If `jargon_findings` is non-empty, make **one** LLM call (batched — all findings in a single prompt, not one call per term):

**System prompt:**
```
You are a technical editor. The following document contains technical
terms that lack plain-language explanations. Add a brief explanation
to each flagged term — a parenthetical, em-dash definition, or "i.e."
clause — without changing the document's meaning or structure.

Rules:
- Only modify the flagged passages. Leave everything else unchanged.
- Explanations should be readable by someone with basic data literacy
  but no ML training.
- Explanations should be under 20 words each.
- Do not add new sections, headings, or bullet points.
- Return the full rewritten document, not a diff.

Flagged terms with context: {jargon_findings}
```

The LLM returns rewritten versions of the report and dictionary. The script does NOT parse a diff — it replaces the raw strings wholesale, trusting the LLM to preserve structure. If the rewritten document is more than 20% longer than the original, treat as over-correction and fall back to the original (log a `jargon_scan_flag` event).

### Guardrails

- **Non-blocking**: jargon findings never halt the pipeline. If Layer 2 fails, the original documents are delivered unchanged.
- **Max one LLM call per run**: all findings batched into one prompt.
- **No meaning changes**: the LLM is instructed to add clarity only. Structural integrity is checked with length delta (<20% growth) and a sanity check that section headers are preserved.
- **Does not write to disk**: rewritten strings are passed to the delivery stage (Stage 11). The mistake log captures the scan findings.

### Error Conditions

| Condition | Message |
|-----------|---------|
| Layer 2 LLM fails to return a valid rewrite | "Jargon rewrite failed — delivering original document. Terms flagged: {list}." Documents delivered as-is. |
| Rewritten document exceeds 20% length growth | "Jargon rewrite exceeded size budget — reverting to original. Flagged: {list}." Documents delivered as-is. |
| Rewritten document missing a top-level header that was in the original | "Jargon rewrite altered document structure — reverting to original." Documents delivered as-is. |

All three conditions write a `jargon_scan_flag` event to the mistake log and are non-blocking.

### Dependencies

- re — standard library (Layer 1)
- LLM (Claude 4.5 Sonnet) — Layer 2 only, conditional
