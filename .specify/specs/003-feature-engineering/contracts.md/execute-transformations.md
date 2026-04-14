# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

### Contract: execute_transformations
**FR(s):** FR-208, FR-209, FR-210, FR-211 | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

### Purpose
Executes all approved feature engineering transformations on the cleaned CSV. Uses only pandas, numpy, and scikit-learn. Produces the feature-engineered CSV (DM-009). Applies transformations in the fixed execution order. Adds the `feat_` prefix to all new columns.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df | pandas DataFrame | Loaded during validation | Yes |
| approved_features | list | DM-007 | Yes |
| validation_result | dict | DM-003 | Yes |

### Outputs

On success: Returns modified DataFrame with engineered columns appended. Writes `{run_id}-engineered.csv` to sandbox filesystem.

Console output:
```
⚙️ Executing approved transformations...
   Batch 1: Date/Time Extraction — {n} features ✅
   Batch 2: Text Features — {skipped | n features ✅}
   ...
✅ All transformations executed. {total} new features created.
   Output shape: {rows} rows × {cols} columns
```

### Execution Rules

**Order:** Transformations applied in batch order (1→6). Within a batch, features applied in alphabetical order by feature name.

**Prefix:** Script adds `feat_` prefix to every new column name. The LLM never applies the prefix.

**Column preservation (FR-210):** All original columns remain unchanged unless an approved decision explicitly removes one (e.g., dropping the original categorical column after one-hot encoding). The script verifies original columns are intact after each batch.

**Transformation implementations (pre-built, not LLM-generated):**

| transformation_method | Implementation |
|----------------------|----------------|
| extract_day_of_week | `pd.to_datetime(df[col]).dt.dayofweek` |
| extract_hour | `pd.to_datetime(df[col]).dt.hour` |
| extract_month | `pd.to_datetime(df[col]).dt.month` |
| extract_quarter | `pd.to_datetime(df[col]).dt.quarter` |
| text_string_length | `df[col].astype(str).str.len()` |
| text_word_count | `df[col].astype(str).str.split().str.len()` |
| groupby_agg | `df.groupby(key)[col].agg(func).reset_index()` then merge back |
| derived_ratio | `df[col_a] / df[col_b]` with division-by-zero → NaN handling |
| derived_difference | `df[col_a] - df[col_b]` |
| one_hot_encode | `pd.get_dummies(df, columns=[col], prefix='feat_' + name)` — prefix applied directly by get_dummies |
| label_encode | `sklearn.preprocessing.LabelEncoder().fit_transform(df[col])` |
| min_max_scale | `sklearn.preprocessing.MinMaxScaler().fit_transform(df[[col]])` |
| z_score_scale | `sklearn.preprocessing.StandardScaler().fit_transform(df[[col]])` |

**Edge case handling (built into each implementation):**
- Division by zero → NaN, logged in mistake log
- Infinity values → NaN, logged
- NaN from failed datetime parsing → NaN, logged
- Unknown categories during encoding → logged, pipeline continues
- Zero-variance column during scaling → skip scaling, logged

### Error Conditions

| Condition | Message |
|-----------|---------|
| Transformation raises exception | "Execution error in Batch {n}: {error}. Action: {handling}. Logged in mistake log." Pipeline continues with remaining transformations. |
| Critical failure (DataFrame corrupted) | "Critical execution error — pipeline halted. No output CSV produced. See mistake log." |
| No approved features to execute | Proceeds to FR-225 no-opportunity path. |

### Dependencies

- pandas — pre-installed
- numpy — pre-installed
- scikit-learn — pre-installed

---
