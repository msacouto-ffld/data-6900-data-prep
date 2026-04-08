# Contract: light_verification

**FR(s)**: FR-121 | **Owner**: LLM | **Freedom**: Medium | **Runtime**: LLM-executed

---

## Purpose

Abbreviated persona review for the no-issues workflow. Confirms that the profiling report correctly identified no cleaning needs. Outputs the original CSV unchanged.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| profiling_data | dict | DM-101 JSON | Yes |
| nl_report | string | Feature 1 NL report | Yes |
| raw_df | DataFrame | Original CSV | Yes |
| run_metadata | dict | DM-102 | Yes |

## Outputs

On confirmation: Pipeline proceeds to generate a "no cleaning required" report and deliver the original CSV as the cleaned output.

Console output:

```
🔎 Running light verification to confirm...
✅ Verified: data is clean. No transformations required.
```

## LLM Prompt

"You are a Data Analyst reviewing whether this dataset truly requires no cleaning. You have the profiling data and the NL report. Confirm that no quality issues were missed, or flag any concerns. Look for: unreported mixed types, hidden duplicates, potential type coercion needs, missing value patterns the profiling may have missed."

## Fallback Behavior

If the persona flags a concern, the pipeline does not silently fall back. Instead, it displays:

```
🔎 The initial check found no issues, but verification identified
   a potential concern: {concern}. Proceeding with standard
   cleaning workflow to address this.
```

Then enters the standard propose → review → execute pipeline.

## Report Generation

A simplified report is generated with:

- **Executive Summary**: "No data quality issues were identified."
- **Dataset Comparison**: Before and after are identical
- **Transformations Applied**: "None"
- **Next Steps**: Normalization, encoding recommendations for Skill B
- **Verification Summary**: PASS

## Output Files

Same 4 files as the standard workflow, but the cleaned CSV is identical to the input CSV.

## Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to produce verification | Proceed with standard workflow as fallback |

## Dependencies

- LLM (Claude 4.5 Sonnet)
