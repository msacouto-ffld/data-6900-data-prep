# Contract: generate_charts

**FR(s):** FR-006 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

## Purpose

Generates 3 inline charts via matplotlib for display in the chat alongside the NL report. Runs after ydata-profiling completes.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df | pandas DataFrame | Loaded during validation | Yes |
| validation_result | dict | DM-002 | Yes |

## Outputs

On success:

1. Writes chart PNGs to sandbox filesystem
2. Returns `chart_metadata` list (DM-007 schema)

On success — console output:

```
📈 Generating visualizations...
{✅ or ℹ️ per chart}
```

## Chart Specifications

| Chart | Filename | Inclusion Rule | Specs |
|-------|----------|---------------|-------|
| Missing values bar | `{run_id}-chart-missing.png` | Omit if zero missing | Horizontal bar; `df.isnull().mean() * 100`; sorted descending; only >0% shown; labeled with column name and percentage |
| Data type distribution bar | `{run_id}-chart-dtypes.png` | Always | Vertical bar; `df.dtypes.value_counts()`; labeled with dtype and count |
| Numeric histograms | `{run_id}-chart-histograms.png` | Omit if no numeric columns | Grid: max 4 columns wide, auto-rows; `df.select_dtypes(include='number')`; capped at top 12 by variance; `bins=30` |

**Histogram cap:** >12 numeric columns → show top 12 by variance. `chart_metadata[].note` records: "Showing top 12 of {n} numeric columns by variance."

## Styling

```python
matplotlib.use('Agg')
try:
    plt.style.use('seaborn-v0_8-whitegrid')
except OSError:
    try:
        plt.style.use('seaborn-whitegrid')
    except OSError:
        pass  # Fall back to matplotlib default
```

- Figure DPI: 150
- Font size: 10pt body, 12pt titles
- Color palette: default matplotlib tab10

## Error Conditions

| Condition | Message |
|-----------|---------|
| matplotlib not available | "Chart generation error: matplotlib is not available. Charts will be skipped." |
| Individual chart fails | Log warning; set `included: false` in metadata; continue with remaining charts |

Chart generation is non-blocking — if a chart fails, the pipeline continues without it. The NL report adapts its chart references based on `chart_metadata[].included`.

## Dependencies

- `matplotlib` — transitive dependency of ydata-profiling
- `pandas` — pre-installed
- `numpy` — pre-installed