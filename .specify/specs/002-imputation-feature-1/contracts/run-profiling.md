# Contract: run_profiling

**FR(s):** FR-004 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

## Purpose

Runs ydata-profiling on the validated CSV. Produces the HTML profile report and extracts profiling statistics for downstream consumption. Runs after dependency installation and input validation.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df | pandas DataFrame | Loaded during validation | Yes |
| validation_result | dict | DM-002 | Yes |

## Outputs

On success:

1. Writes HTML report to sandbox: `{run_id}-profile.html`
2. Returns `profiling_statistics` dict (DM-006 schema)
3. Returns `profiling_mode` string (`"full"` or `"minimal"`)

On success — console output:

```
📊 Running ydata-profiling ({mode} mode)...
   This may take a moment for larger datasets.
✅ HTML profile report generated.
```

## Logic

1. Determine profiling mode: `minimal = True` if `cell_count > 50,000`, else `False`
2. Build configuration dict (DM-005 schema) — always include both `sensitive=True` and `samples={"head": 0, "tail": 0}` as belt-and-suspenders privacy protection:

```python
config = {
    "title": f"Data Profile: {filename}",
    "minimal": cell_count > 50_000,
    "explorative": False,
    "sensitive": True,
    "correlations": {
        "pearson": {"calculate": True},
        "spearman": {"calculate": False},
        "kendall": {"calculate": False},
        "phi_k": {"calculate": False}
    },
    "missing_diagrams": {
        "bar": True,
        "matrix": False,
        "heatmap": False
    },
    "samples": {
        "head": 0,
        "tail": 0
    }
}
```

3. Run `ProfileReport(df, **config)`
4. Export HTML: `report.to_html("{run_id}-profile.html")`
5. Extract statistics from `report.get_description()` into DM-006 schema

## Error Conditions

| Condition | Message |
|-----------|---------|
| ydata-profiling not installed | "Pipeline error: ydata-profiling is not available. Re-run from the beginning." |
| ProfileReport raises exception | "Profiling failed: {error}. Please try again in a new session, or try uploading a smaller sample." |
| HTML export fails | "Profiling error: could not generate HTML report. Please try again in a new session." |

If profiling fails, the pipeline halts — downstream steps depend on profiling output.

## Dependencies

- `ydata_profiling` — installed in Step 1
- `pandas` — pre-installed (post ydata-profiling install version)
