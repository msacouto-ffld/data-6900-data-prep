---
name: data-profiling-and-cleaning
description: Use this skill when a user uploads a raw CSV and wants to understand, clean, or prepare it for analysis — including requests like "profile this dataset", "analyze the data quality", "clean this CSV", "fix the issues in this data", "run data profiling", or any similar natural-language request to inspect, diagnose, or repair tabular data. This skill always runs the full Skill A pipeline end-to-end. It first profiles the CSV (statistical summary, quality checks, PII scan, natural-language report) and then cleans it through a persona-validated 7-step transformation pipeline, producing the Skill A → Skill B handoff package (cleaned CSV, transformation report, transform metadata JSON, mistake log). Profiling and cleaning run as a single continuous pipeline — even requests framed as profiling-only continue through cleaning. Do NOT trigger for feature engineering (new columns, encodings, scaling) — that is Skill B.
---

# Data Profiling and Cleaning (Skill A)

## Purpose

Takes a raw CSV and produces a cleaned dataset plus a three-artifact handoff package for Skill B. Runs two features in sequence: profiling (stages 1–9) then cleaning (stages 10–17).

## Prerequisites

- Raw CSV uploaded to the session
- Hard limit: 500,000 cells. Warning at 100,000+.

## Workflow

Copy this checklist and track progress:

```
Pipeline Progress:
- [ ] Feature 1: Install ydata-profiling
- [ ] Feature 1: Validate input
- [ ] Feature 1: Detect quality issues
- [ ] Feature 1: Run ydata-profiling
- [ ] Feature 1: Scan for PII
- [ ] Feature 1: Generate charts
- [ ] Feature 1: Generate NL report (LLM)
- [ ] Feature 1: Verify report (LLM)
- [ ] Feature 1: Deliver profiling outputs
- [ ] Feature 2: Load Feature 1 outputs
- [ ] Feature 2: Propose transformations (LLM)
- [ ] Feature 2: Review panel validates (LLM)
- [ ] Feature 2: Execute transformations
- [ ] Feature 2: Verify output (LLM)
- [ ] Feature 2: Generate report (LLM)
- [ ] Feature 2: Jargon scan
- [ ] Feature 2: Deliver cleaning outputs
```

Always continue from Feature 1 into Feature 2 — never stop after profiling.

### Feature 1 — Data Profiling

**Stage 1: Install dependencies**

```bash
pip install ydata-profiling -q
```

Verify import succeeds. Must complete before anything else.

**Stage 2: Validate input**

Run `scripts/validate_input.py`. Eight checks in order: file exists → CSV parses → ≥1 column → ≥1 row → cell count ≤ 500K → cell count warning → single-row warning. Generates run ID `profile-YYYYMMDD-HHMMSS-XXXX`. Hard-gate failures halt with actionable messages.

**Stage 3: Detect quality issues**

Run `scripts/detect_quality_issues.py`. Four pandas-based checks: duplicate column names, special characters, all-missing columns, mixed types. Results are informational — they do not halt the pipeline.

**Stage 4: Run ydata-profiling**

Run `scripts/run_profiling.py`. Uses `sensitive=True` and `samples={"head": 0, "tail": 0}`. Minimal mode if >50K cells. Exports HTML report and extracts statistics into DM-006. Halts on failure.

**Stage 5: Scan for PII**

Run `scripts/scan_pii.py`. Layer 1 (script): word-boundary match on column names against 5 PII token lists. Layer 2 (LLM): inspect first 5 non-null values per unflagged column. See [PROMPTS.md](PROMPTS.md) § PII Layer 2 for the prompt. Raw values are never persisted — only shown to the LLM in memory.

**Stage 6: Generate charts**

Run `scripts/generate_charts.py`. Three charts (missing values, dtype distribution, numeric histograms). Non-blocking — failures set `included: false`.

**Stage 7: Generate NL report**

LLM call using [PROMPTS.md](PROMPTS.md) § NL Report Generation. Pass profiling statistics, quality detections, PII scan, and chart metadata. The LLM produces a 7-section markdown report. Never fabricate issues.

**Stage 8: Verify report**

LLM call using [PROMPTS.md](PROMPTS.md) § Report Verification. Data Analyst persona applies 7-item checklist. Appends Verification Summary section.

**Stage 9: Deliver profiling outputs**

Run `scripts/deliver_outputs.py`. Writes `{run_id}-profile.html`, `{run_id}-summary.md`, `{run_id}-profiling-data.json`. Displays report inline with 📥 download links.

### Feature 2 — Data Cleaning

**Stage 10: Load Feature 1 outputs**

Run `scripts/load_inputs.py`. Globs for `profile-*-profiling-data.json`, loads NL report and raw CSV, generates `transform-YYYYMMDD-HHMMSS-XXXX` run ID.

**Stage 11: Propose transformations**

LLM call using [PROMPTS.md](PROMPTS.md) § Propose Transformations. The LLM reads profiling data and the full transformation catalog from [CATALOG.md](CATALOG.md), then proposes one transformation per detected issue. Output is DM-104 JSON.

If `no_issues_detected: true`, branch to light verification — see [PROMPTS.md](PROMPTS.md) § Light Verification. Skip stages 12–16 and output the original CSV unchanged.

**Stage 12: Review panel**

LLM call using [PROMPTS.md](PROMPTS.md) § Review Panel. Three perspectives (Conservative, Business, Technical) evaluate each proposed transformation. Confidence scores are deterministic fixed values: 95, 82, 67, 50, 35.

On rejection: re-propose with rejection context (max 2 loops). After 2 loops still rejected → score 35 → present options to user inline. User picks a number, types "skip", or provides guidance.

**Stage 13: Execute transformations**

Run `scripts/execute_transformations.py`. Dispatches to 7 pre-built step functions in fixed order:

| Step | Script | What it does |
|------|--------|-------------|
| 1 | `scripts/step_1_column_names.py` | snake_case + dedup |
| 2 | `scripts/step_2_drop_missing.py` | Drop 100%-missing columns |
| 3 | `scripts/step_3_type_coercion.py` | 4 sub-dispatchers |
| 4 | `scripts/step_4_invalid_categories.py` | Canonical mapping, rare grouping |
| 5 | `scripts/step_5_imputation.py` | 8 strategies via sklearn |
| 6 | `scripts/step_6_deduplication.py` | 5 strategies |
| 7 | `scripts/step_7_outliers.py` | Percentile cap, remove, flag |

Each step captures before/after metrics via `scripts/metrics.py` and checks thresholds via `scripts/high_impact.py`. Never execute LLM-generated code — only pre-built code paths.

Writes `{run_id}-cleaned.csv`.

**Stage 14: Verify output**

LLM call using [PROMPTS.md](PROMPTS.md) § Verify Output. Data Analyst checks row/column counts, unapproved changes, metric consistency.

**Stage 15: Generate report**

LLM call using [PROMPTS.md](PROMPTS.md) § Generate Report. Follow [REPORT-TEMPLATE.md](REPORT-TEMPLATE.md) exactly. Every transformation gets 3-part template (What/Why/Impact) + confidence score + before/after metrics. High-impact flags show both actual value and threshold.

**Stage 16: Jargon scan**

Run `scripts/scan_jargon.py`. Finds undefined uppercase acronyms. Whitelisted: CSV, HTML, JSON, NaN, PII, ID, LLM, NL, ASCII, UTC, ISO, PDF, API, PASS, FAIL, OK. If violations found, one LLM call to add definitions.

**Stage 17: Deliver cleaning outputs**

Run `scripts/deliver_cleaning_outputs.py`. Writes:
- `{run_id}-cleaned.csv` (already written in stage 13)
- `{run_id}-transform-report.md`
- `{run_id}-transform-metadata.json` (Skill B handoff)
- `{run_id}-mistake-log.json` (via try/finally)

Display report inline with 📥 download links. Point user to Skill B as next step.

## Guardrails

- **Never execute LLM-generated code.** Dispatch to pre-built code paths by strategy name only.
- **Never apply unapproved transformations.** Every transformation passes through the review panel.
- **Never include raw data values** in reports, logs, or exported files. Column names and aggregates only.
- **Never silently apply high-impact transformations.** Surface flags with actual value vs threshold.
- **Never fabricate issues.** If data is clean, say so.
- **Determinism**: `random_seed=42`, fixed confidence scores, `matplotlib.use('Agg')`, `sensitive=True`.

## Error Reference

| Error | What to do |
|-------|------------|
| ydata-profiling install failed | New session, retry |
| Not a valid CSV / empty CSV | Re-upload a valid CSV with data |
| Exceeds 500K cells | Sample or split the dataset |
| Profiling failed | New session, try smaller sample |
| No profiling data found | Run Feature 1 first |
| Transformation failed at step N | New session, re-upload, re-run full pipeline |
| Review panel no consensus (score 35) | User chooses option, skips, or provides guidance |
| High-impact flag triggered | Review report before handing to Skill B |

## Reference Files

- [PROMPTS.md](PROMPTS.md) — all LLM prompt templates (8 sections)
- [CATALOG.md](CATALOG.md) — transformation catalog with 26 strategies and parameter table
- [REPORT-TEMPLATE.md](REPORT-TEMPLATE.md) — DM-109 report template
- `scripts/` — all pipeline scripts and utilities
