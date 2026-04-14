# Transformation Catalog (DM-103)

This file is the authoritative reference for the catalog of approved
transformation strategies in Feature 2 (Data Cleaning). It is embedded
in the `propose_transformations` LLM system prompt so the LLM knows
which strategies are pre-approved and what parameters each one needs.

The catalog is also available programmatically as
`scripts/catalog.TRANSFORMATION_CATALOG`. Both sources MUST stay in
sync — when you add or modify a strategy, update both files.

---

## Structure

Every catalog entry maps one of the 7 pipeline steps to its list of
approved strategies:

```python
TRANSFORMATION_CATALOG = {
    <step_number>: {
        "step_name": "<snake_case_name>",
        "strategies": ["<strategy_1>", "<strategy_2>", ...]
    },
    ...
}
```

Strategies are case-sensitive snake_case identifiers. The LLM must use
the exact strategy name when producing a transformation plan
(DM-104). The execution engine dispatches step functions based on
these names.

---

## The 7 Steps

### Step 1 — Column Name Standardization

**Purpose**: fix non-standard column names so downstream code can
reference columns reliably.

| Strategy | What It Does |
|----------|--------------|
| `standardize_to_snake_case` | Lowercase, convert spaces and separators to underscores, strip leading/trailing whitespace |
| `remove_special_characters` | Remove non-alphanumeric characters (keeping underscores); applied together with `standardize_to_snake_case` |
| `rename_duplicates_with_suffix` | When two columns share the same normalized name, append `_1`, `_2`, etc. to disambiguate |

**Parameters**: none required for any strategy.

---

### Step 2 — Drop All-Missing Columns

**Purpose**: remove columns that contain no data.

| Strategy | What It Does |
|----------|--------------|
| `drop_column` | Remove columns where 100% of values are missing |

**Parameters**: none required.

**Safety check**: the step function validates that targeted columns
are in fact 100% missing before dropping. If a column is not entirely
missing, the step raises an exception rather than silently dropping
data that has signal.

---

### Step 3 — Type Coercion

**Purpose**: resolve mixed types and parse strings into their
intended types.

| Strategy | What It Does | Required Parameters |
|----------|--------------|---------------------|
| `coerce_to_target_type` | `df[col].astype(target_type)` with `errors='coerce'` — values that can't be converted become NaN | `target_type` |
| `parse_dates_infer_format` | `pd.to_datetime()` with `format='mixed'`, fallback to NaT | — |
| `parse_currency_strip_symbols` | Regex strip `$`, `,`, whitespace; cast to float | `currency_symbol` (optional, default `$`) |
| `parse_percent_to_float` | Regex strip `%`; cast to float; divide by 100 | — |

**Parameter note**: `parse_dates_infer_format` historically used
pandas's `infer_datetime_format=True`. That kwarg was removed in
recent pandas — use `format='mixed'` instead. The implementation
falls back to `NaT` for unparseable values.

**Execution**: step 3 dispatches internally based on the `strategy`
field. Each sub-strategy is a separate internal function called by
the `step_3_type_coercion` dispatcher.

---

### Step 4 — Invalid Category Cleanup

**Purpose**: normalize categorical values that have inconsistent
spellings, capitalization, or rare outlier categories.

| Strategy | What It Does | Required Parameters |
|----------|--------------|---------------------|
| `map_to_canonical_value` | Apply a dict of `{variant: canonical}` to the column | `canonical_mapping` |
| `group_rare_into_other` | Replace values whose frequency is below the threshold with `"Other"` | `threshold_pct` (0–100) |
| `flag_for_human_review` | No data modification — just log the column for human attention | — |

**Notes**:

- `canonical_mapping` must be a dict. The LLM proposal MUST provide
  the mapping explicitly; the execution engine does not guess.
- `group_rare_into_other` with `threshold_pct: 1.0` means any
  category appearing in less than 1% of rows is grouped.

---

### Step 5 — Missing Value Imputation

**Purpose**: handle missing values in columns with some but not all
data.

| Strategy | What It Does | Required Parameters |
|----------|--------------|---------------------|
| `drop_rows` | Drop rows where any of the affected columns is missing | — |
| `drop_column` | Drop the entire column (used when missing % is too high to impute reliably) | — |
| `impute_mean` | Fill NaN with column mean (numeric only) | — |
| `impute_median` | Fill NaN with column median (numeric only) | — |
| `impute_mode` | Fill NaN with column mode (categorical or numeric) | — |
| `impute_constant` | Fill NaN with an explicit value | `fill_value` |
| `impute_most_frequent` | Alias for `impute_mode` using scikit-learn `SimpleImputer(strategy="most_frequent")` | — |
| `impute_unknown` | Fill NaN with the string `"Unknown"` (categorical only) | `fill_value` (optional, default `"Unknown"`) |

**Important**:

- `impute_mean`, `impute_median`, `impute_mode`, `impute_most_frequent`
  all go through scikit-learn's `SimpleImputer` with `random_state=42`
  where the imputer accepts a random state. This is a determinism
  requirement from DM-102.
- Mixing `drop_column` in step 5 with `drop_column` in step 2 is
  allowed. Step 2 handles 100% missing; step 5 may drop a column with
  e.g. 85% missing when imputation is not trustworthy.

---

### Step 6 — Deduplication

**Purpose**: remove or flag duplicate rows.

| Strategy | What It Does |
|----------|--------------|
| `drop_exact_keep_first` | `df.drop_duplicates(keep='first')` |
| `drop_exact_keep_last` | `df.drop_duplicates(keep='last')` |
| `keep_most_recent` | Sort by a user-specified timestamp column, keep the most recent duplicate |
| `keep_most_complete` | Of a group of duplicates, keep the row with the fewest NaN values |
| `flag_for_human_review` | No modification — log duplicate groups for review |

**Parameters**: none required for the first two; the last three may
require a column hint. See DM-104 for the full parameter table.

---

### Step 7 — Outlier Treatment

**Purpose**: handle values in the extreme tails of numeric
distributions.

| Strategy | What It Does | Required Parameters |
|----------|--------------|---------------------|
| `cap_at_percentile` | Replace values above `percentile_upper` with that percentile's value; same for below `percentile_lower` | `percentile_lower`, `percentile_upper` |
| `remove_rows` | Drop rows whose value is outside the percentile bounds | `percentile_lower`, `percentile_upper` |
| `flag_only` | No modification — record the outlier rows for downstream review | — |
| `winsorize` | Alias for `cap_at_percentile` using `scipy.stats.mstats.winsorize`-style semantics (but implemented with pandas quantile) | `percentile_lower`, `percentile_upper` |

**Percentile values**: both `percentile_lower` and `percentile_upper`
are floats in [0, 100]. Typical values are 1 and 99, or 5 and 95. The
LLM MUST propose explicit values; the execution engine does not
default them.

---

## Custom Strategies

If the LLM determines that no catalog strategy fits a specific issue,
it MAY propose a custom strategy by setting `is_custom: true` in the
DM-104 output. Custom strategies receive extra scrutiny from the
review panel (DM-105) and trigger a lower confidence score ceiling
(max 82 instead of 95).

**The execution engine does NOT dispatch custom strategies to
LLM-generated code.** Custom strategies either:

1. Resolve to one of the catalog strategies during review (the panel
   suggests an alternative from the catalog), OR
2. Are escalated to human review (confidence = 35) and either
   resolved to a catalog strategy or skipped.

This is a non-negotiable safety rule from the constitution:
LLM-generated code is never executed directly.

---

## Required Parameters Table (Quick Reference)

This table duplicates the per-step parameter columns above for
convenience when parsing DM-104 output.

| Strategy | Required Parameters |
|----------|---------------------|
| `coerce_to_target_type` | `target_type` |
| `parse_dates_infer_format` | — |
| `parse_currency_strip_symbols` | — |
| `parse_percent_to_float` | — |
| `map_to_canonical_value` | `canonical_mapping` |
| `group_rare_into_other` | `threshold_pct` |
| `flag_for_human_review` | — |
| `drop_rows` | — |
| `drop_column` | — |
| `impute_mean` | — |
| `impute_median` | — |
| `impute_mode` | — |
| `impute_constant` | `fill_value` |
| `impute_most_frequent` | — |
| `impute_unknown` | — |
| `drop_exact_keep_first` | — |
| `drop_exact_keep_last` | — |
| `keep_most_recent` | — |
| `keep_most_complete` | — |
| `cap_at_percentile` | `percentile_lower`, `percentile_upper` |
| `remove_rows` | — |
| `flag_only` | — |
| `winsorize` | `percentile_lower`, `percentile_upper` |
| `standardize_to_snake_case` | — |
| `remove_special_characters` | — |
| `rename_duplicates_with_suffix` | — |

The execution engine validates parameter presence before running each
step. Missing required parameters → halt with:
`"Pipeline error: missing required parameter '{param}' for strategy '{strategy}' in step {n}."`
