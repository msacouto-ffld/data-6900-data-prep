# Contract: deliver_outputs

**FR(s):** FR-014 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

## Purpose

Writes the final NL report and structured profiling data to the sandbox filesystem, displays the NL report inline with charts, and presents all files for download.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| final_nl_report | string (markdown) | From verify_report | Yes |
| validation_result | dict | DM-002 | Yes |
| profiling_statistics | dict | DM-006 | Yes |
| quality_detections | list of dicts | DM-003 | Yes |
| pii_scan | list of dicts | DM-004 | Yes |
| chart_metadata | list of dicts | DM-007 | Yes |

## Outputs

1. **Inline delivery:** NL report displayed in chat with inline charts
2. **Files written to sandbox:**

| File | Format | Content |
|------|--------|---------|
| `{run_id}-summary.md` | Markdown | Final NL report |
| `{run_id}-profile.html` | HTML | ydata-profiling output (already written by run_profiling) |
| `{run_id}-profiling-data.json` | JSON | DM-010 handoff schema — contains validation_result, quality_detections, pii_scan, profiling_statistics |

3. **Download presentation (order matches quickstart Step 10):**

```
📥 Your profiling outputs are ready for download:
   • {run_id}-profile.html
     — Full statistical profile (interactive HTML report)
   • {run_id}-summary.md
     — Natural language analysis (the report shown above)
   • {run_id}-profiling-data.json
     — Structured profiling data (for technical users or
       downstream data cleaning tools)

Your profiling is complete. You can now proceed to data cleaning,
or download these files to share with your team.
```

## Error Conditions

| Condition | Message |
|-----------|---------|
| File write fails | "Output error: could not save {filename}. The report has been delivered inline — please copy it manually." |

File write failure is non-blocking for inline delivery — the user still sees the report in chat.

## Dependencies

- `json` — standard library
- Claude.ai file presentation mechanism