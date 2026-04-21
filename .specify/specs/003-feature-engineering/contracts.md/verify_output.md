# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

### Contract: verify_output
**FR(s):** FR-212, FR-213 | **Owner:** LLM (Data Analyst persona) + Script (checks) | **Freedom:** Medium | **Runtime:** Mixed

### Purpose
The Data Analyst persona compares the feature-engineered output against the cleaned input and the approved feature set. This is the "Test" step of the Verification Ritual — it runs **before** report generation, so the Verification Summary section of the transformation report is populated with real review results rather than placeholder text.

Each of the 9 checklist items is implemented as a deterministic script check. The persona's role is to interpret results, classify issues as correctable vs uncorrectable, and produce the human-readable verification summary. Correctable issues are auto-fixed and documented. Uncorrectable issues halt the pipeline.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| df_input | pandas DataFrame | Cleaned CSV loaded at Stage 1 (with Skill A dtypes re-applied) | Yes |
| df_output | pandas DataFrame | Engineered DataFrame from Stage 6 | Yes |
| approved_features | list[dict] | DM-007 (running tracker) | Yes |
| validation_result | dict | DM-003 | Yes |

### Outputs

Returns `verification_result` dict (DM-008 schema).

Console output:
```
🔎 Data Analyst verification ({k}/9 checks)
   ✅ row_count_preserved: {detail}
   ✅ original_columns_intact: {detail}
   ✅ feat_prefix_applied: {detail}
   ✅ expected_columns_present: {detail}
   ✅ no_unexpected_nan: {detail}
   ✅ no_infinity_values: {detail}
   ✅ encoding_correct: {detail}
   ✅ scaling_correct: {detail}
   ⚠️ no_data_leakage: {detail}
   
   Overall: PASS (with {n} warning(s))
```

On uncorrectable failure:
```
🔎 Data Analyst verification HALTED
   ❌ {check_name}: {detail}
   Pipeline cannot proceed. See mistake log for full record.
```

### The 9-Item Checklist

| # | Check | Type | Script expression | Pass/warn/fail classification |
|---|-------|------|-------------------|-------------------------------|
| 1 | row_count_preserved | Hard gate | `df_input.shape[0] == df_output.shape[0]` | Fail → halt |
| 2 | original_columns_intact | Hard gate | For each `c` in `df_input.columns`: `c in df_output.columns` AND `df_input[c].equals(df_output[c])` | Fail → halt |
| 3 | feat_prefix_applied | Correctable | All new columns start with `feat_` | Correctable: rename missing prefixes |
| 4 | expected_columns_present | Correctable | Every feature in `approved_features` appears in `df_output.columns` | Correctable: re-run missing transformation |
| 5 | no_unexpected_nan | Soft gate | For each `feat_` column: NaN count matches what the feature's edge-case handler predicted (e.g., derived_ratio may have NaN from div-by-zero; extract_* should have 0) | Warn if over predicted, fail only if orders of magnitude off |
| 6 | no_infinity_values | Hard gate | `np.isinf(df_output[c]).sum() == 0` for every numeric `feat_` column | Fail → halt |
| 7 | encoding_correct | Hard gate | For every one-hot group: row sum == 1 across its dummy columns; dummy count == input `nunique()` | Fail → halt |
| 8 | scaling_correct | Hard gate | For z-score: `abs(mean) < 1e-10 AND abs(std - 1) < 1e-10`. For min-max: `min == 0 AND max == 1` | Fail → halt |
| 9 | no_data_leakage | Soft gate (warning) | Any aggregation or scaling computed across the full dataset is flagged as a forecasting-leakage warning. Not a failure — the user may not be using this for forecasting. | Always warning if any aggregate/scaler features present |

### Correctable vs Uncorrectable

**Correctable (auto-fix, documented in verification_result):**
- Missing `feat_` prefix on a new column → rename
- Missing approved column in output → re-invoke the transformation from Stage 6
- One-hot dummy column with wrong dtype (e.g., bool instead of int) → cast to int

Each auto-fix writes a `verification_correction` event to the mistake log. After correction, the check is re-run; if it passes, continue. If it still fails after one correction attempt, promote to uncorrectable.

**Uncorrectable (halt pipeline):**
- Row count mismatch — indicates data loss or silent filtering
- Original column dropped or values mutated — violates guardrail FR-210
- Infinity values in numeric output — indicates silent math error
- One-hot row sums ≠ 1 — indicates encoding applied incorrectly
- Scaling fails the tolerance check — indicates scaler applied to wrong data

Each uncorrectable failure writes a `verification_issue` event and halts the pipeline. No transformation report is generated for failed runs — the engineered CSV remains on disk but is not delivered; the user sees the mistake log and the halt message.

### Data Analyst Persona System Prompt

```
You are a Data Analyst reviewing an automated feature engineering output.
You have been given:
- The script's deterministic check results (pass/warn/fail per item)
- The approved feature set with confidence scores
- The input and output DataFrame shapes

Your role:
1. Write a one-sentence human-readable summary of each check result.
2. For each warning, explain the practical implication in plain language
   (e.g., "This won't cause training errors, but will give misleading
   accuracy if you use these features in a time-series forecast with a
   held-out test window").
3. Recommend next steps for any warning or correction.

Do NOT re-run the checks — the script has authoritative results.
Do NOT overrule a hard-gate failure — the script has already halted
the pipeline before you were called.

Return your review in this exact JSON format:
{DM-008 schema}
```

### Implementation Notes

**Bool comparison pitfall**: pandas/numpy comparisons return `numpy.bool_`, not Python `bool`. The identity check `if result is True` will silently evaluate False against `numpy.True_` — always wrap comparisons in `bool(...)` or use `== True` when storing pass/fail flags for later display.

**Tolerance for scaling checks**: use `1e-10` absolute tolerance for z-score mean/std. StandardScaler's output has floating-point residue around `1e-17` — don't fail on that.

**Leakage check is always a warning, never a failure**: the pipeline does not know whether the user intends this dataset for forecasting. Surface the risk; don't block use cases where it's irrelevant (cross-sectional modeling, clustering, EDA).

### Error Conditions

| Condition | Message |
|-----------|---------|
| df_output DataFrame corrupted or missing | "Critical: cannot load engineered output. Pipeline halted before verification." |
| More than 3 correctable issues in one run | "Verification found {n} correctable issues. Proceeding with corrections, but review recommended — this may indicate an execution bug." |
| Persona fails to return summary | Retry once. If fails again: use a deterministic script-generated summary and log warning. Does not halt the pipeline. |

### Dependencies

- pandas — pre-installed
- numpy — pre-installed
- LLM (Claude 4.5 Sonnet) — for persona summary only; checks themselves are script-only
