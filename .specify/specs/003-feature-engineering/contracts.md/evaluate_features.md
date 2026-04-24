# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-24 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

### Contract: evaluate_features
**FR(s):** Project spec §Testing — "performance delta" | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

### Purpose
Trains a baseline model on original features only, then the same model with engineered features added, and reports the performance delta using 5-fold cross-validation. This is the external quality control that proves the engineered features add measurable value — the personas validate the process, but only a model comparison validates the outcome. Runs after verification, before report generation. Results are included in the transformation report's Feature Value Comparison section.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df_engineered | pandas DataFrame | Post-verification output | Yes |
| original_columns | list[str] | From validation_result["column_names"] | Yes |
| log_path | string | Mistake log path | Yes |
| target_column | string | Auto-detected or user-specified | Optional |

### Outputs

Returns comparison_result dict or None if comparison could not run.

Console output:

📊 Evaluating feature value...
   Target column: {column}
   Task type: {classification | regression}
   Model: RandomForest (n_estimators=100, max_depth=30)
   Evaluation: 5-fold cross-validation

   BASELINE ({n} original features)
     {Primary Metric}: {value} (±{std})
     {Secondary Metric}: {value} (±{std})

   WITH ENGINEERED FEATURES ({n} total features)
     {Primary Metric}: {value} (±{std})
     {Secondary Metric}: {value} (±{std})

   DELTA
     {Primary Metric}: {+/-value}
     {Secondary Metric}: {+/-value}

   ✅ Engineered features improved {metric} by {value}

### Logic

1. Identify feat_ columns in the engineered DataFrame
2. If none exist, skip with message
3. Auto-detect target column: check common names (target, label, class, nobeyesdad, etc.), then fall back to last categorical column with 2–20 unique values
4. If no target found, skip gracefully (non-blocking)
5. Determine task type: classification if target is string/categorical or has ≤20 unique values, else regression
6. Prepare baseline feature matrix: original columns minus target, categoricals label-encoded
7. Prepare engineered feature matrix: baseline + all feat_ columns
8. Run 5-fold cross-validation with RandomForest on both
9. Compute delta
10. Return comparison_result dict

### Guardrails

- **Non-blocking**: comparison failure never halts the pipeline
- **No data leakage in comparison**: uses cross-validation, not train-on-all
- **Target column is never engineered**: only feat_ columns are added to the feature matrix
- **Minimal encoding**: categoricals get label encoding only — just enough to feed the model

### Error Conditions

| Condition | Message |
|-----------|---------|
| No feat_ columns in output | "Feature value comparison: skipped — no engineered features." Non-blocking. |
| No target column detected | "Feature value comparison: skipped — could not identify a target column." Non-blocking. |
| Model training fails | "Feature value comparison: skipped — model training failed ({error})." Non-blocking. Logged in mistake log. |

### Dependencies

- pandas, numpy, scikit-learn — all pre-installed
