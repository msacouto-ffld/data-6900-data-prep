# Contract: propose_transformations

**FR(s)**: FR-102, FR-121 | **Owner**: LLM | **Freedom**: High | **Runtime**: LLM-executed

---

## Purpose

The LLM analyzes the profiling data and proposes a transformation plan following the guided catalog. This is Phase 1 of the Verification Ritual (Read). If no issues are detected, triggers the light verification workflow.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| profiling_data | dict | DM-101 JSON (parsed) | Yes |
| nl_report | string | Feature 1 NL report markdown | Yes |
| run_metadata | dict | DM-102 | Yes |
| rejection_context | list of dict | From review_panel rejections | No — only on re-proposal rounds |

Rejection context entry format (when present):

```python
{
    "transformation_id": "string",
    "rejected_strategy": "string",
    "rejection_reason": "string",
    "suggested_alternative": "string"
}
```

## Outputs

Returns `transformation_plan` (DM-104 schema).

Console output:

```
📋 Analyzing profiling results and proposing transformations...

{7-step proposal listing — all steps shown}

Submitting to review panel for validation...
```

Or, if no issues:

```
📋 Analyzing profiling results...
✅ No data quality issues detected in the profiling report.
```

## LLM System Prompt Requirements

1. Embed the full transformation catalog (DM-103) in the system prompt
2. Embed the fixed 7-step execution order
3. Instruct: "For each quality detection with status 'found', propose a transformation from the catalog. If no catalog strategy fits, propose a custom strategy with `is_custom: true` and extended justification."
4. Instruct: "For each step with no issues, include no transformations for that step."
5. Instruct: "Output a JSON object following the DM-104 schema exactly."
6. Instruct: "The `issue` field must include the detection type as a prefix: `{check_type}: {description}`"
7. Instruct: "Validate that required parameters per strategy are included (see parameter table)."
8. Instruct: "If all quality detections have status 'clean', set `no_issues_detected: true` and return an empty transformations list."
9. For re-proposal rounds: "You will receive rejection context. Use the suggested alternative as guidance, but you may propose a different alternative if you have a better justification."

**No-issues determination:** Based solely on the structured `quality_detections` list in the profiling JSON — not on the NL report narrative. If all entries have `status: 'clean'`, the dataset has no issues regardless of what the NL report says.

**No-issues path:** If `no_issues_detected: true`, the pipeline skips the review panel and execution, and proceeds directly to light verification (contracts/light-verification.md).

## Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to produce valid JSON | "Transformation proposal failed. Please try again." |
| LLM output missing required fields | Retry once; if still invalid, halt with same message |

## Dependencies

- LLM (Claude 4.5 Sonnet)
