# Contract: execute_transformations

**FR(s)**: FR-103 (Run), FR-106, FR-107, FR-108, FR-113, FR-116 | **Owner**: Script | **Freedom**: Low | **Runtime**: Executed

---

## Purpose

Executes approved transformations in the fixed 7-step order using pandas, numpy, and scikit-learn. Captures before/after metrics and high-impact flags at each step. Produces the cleaned CSV.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| raw_df | pandas DataFrame | Original CSV loaded in step 1 | Yes |
| approved_plan | dict | DM-106 — approved transformation plan | Yes |
| run_metadata | dict | DM-102 | Yes |

## Outputs

On success: Returns `cleaned_df` (pandas DataFrame), `step_results` (list of DM-107), writes cleaned CSV to sandbox.

Console output per step:

```
⚙️ Executing approved transformations...

Step {n}: {step_name}... ✅
  • {summary of changes}
  {⚠️ high-impact flags if triggered}
```

## Execution Engine

```python
STEP_ORDER = [
    (1, "column_name_standardization", step_1_column_names),
    (2, "drop_all_missing_columns", step_2_drop_missing),
    (3, "type_coercion", step_3_type_coercion),
    (4, "invalid_category_cleanup", step_4_invalid_categories),
    (5, "missing_value_imputation", step_5_imputation),
    (6, "deduplication", step_6_deduplication),
    (7, "outlier_treatment", step_7_outliers),
]

rng = numpy.random.default_rng(42)
```

## Per-Step Function Contract

Each step function has the signature:

```python
def step_N_name(df: pd.DataFrame, transformations: list[dict], rng) -> pd.DataFrame
```

- Receives the DataFrame, the list of approved transformations for this step, and the RNG
- Returns the modified DataFrame
- Must not modify columns not listed in `affected_columns`
- Must validate required parameters before executing
- Raises exception on failure — does not return partial results

**Step 3 internal dispatch:** The `step_3_type_coercion` function dispatches internally based on the `strategy` field:

- `coerce_to_target_type` → generic pandas `astype()` with error handling
- `parse_dates_infer_format` → `pd.to_datetime()` with `infer_datetime_format=True`
- `parse_currency_strip_symbols` → regex strip + float conversion
- `parse_percent_to_float` → regex strip '%' + divide by 100

Each sub-strategy is a separate internal function called by the step 3 dispatcher.

## Parameter Validation

Before executing each step, the engine validates that all required parameters (per the DM-104 parameter table) are present. Missing parameters → halt with: "Pipeline error: missing required parameter '{param}' for strategy '{strategy}' in step {n}."

## Determinism

- Explicit RNG: `numpy.random.default_rng(42)` passed to step functions
- scikit-learn imputers receive `random_state=42` directly
- Pandas sort uses `kind='mergesort'` for stable sort
- Deduplication uses `keep='first'` consistently

## Before/After Metrics

`capture_metrics()` (from RQ-004) runs before and after each step. Captures dataset-level metrics (row count, column count, total missing, total duplicates) for all steps; column-level metrics for affected columns only.

## High-Impact Checks

`check_high_impact()` (from RQ-005) runs after each step using DM-108 thresholds. Flags collected in `step_results[].high_impact_flags`.

## Skipped Steps

If a step has no approved transformations (including user-skipped), it is recorded with `skipped: true` in the step result. If the skipped step has dependent steps (per DM-106 dependency map), a warning is issued and logged: "⚠️ Skipping {step_name} may affect the accuracy of {dependent_step_name}. Proceeding with caution."

## Output CSV

Written to sandbox as `{transform_run_id}-cleaned.csv` using `df.to_csv(index=False)`.

## Error Conditions

| Condition | Message |
|-----------|---------|
| Missing required parameter | "Pipeline error: missing required parameter '{param}' for strategy '{strategy}' in step {n}." |
| Step function raises exception | "Transformation failed at step {n} ({step_name}): {error}. Please try again in a new session." |
| Output DataFrame is empty | "Pipeline error: all rows were removed during transformation. Please review the approved plan." |

Pipeline halts immediately on any error. Mistake log is written via try/finally.

## Dependencies

- pandas
- numpy
- scikit-learn
- json (standard library)
