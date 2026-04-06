# Implementation Plan: Data Profiling & Exploratory Report

**Branch**: `001-data-profiling` | **Date**: 2026-04-06 | **Spec**: Feature 001 — Data Profiling
**Input**: User uploads a raw CSV file to Claude.ai

## Summary

This plan covers the full V1 Data Profiling & Exploratory Report feature: a pipeline that accepts a raw CSV upload in Claude.ai, runs ydata-profiling to generate an HTML statistical profile, executes four data quality checks, performs a two-layer PII scan, generates 3 inline charts via matplotlib, and produces a 7-section natural language report verified by a Data Analyst persona. The primary technical approach is a hybrid pipeline — deterministic Python scripts for validation, quality detection, profiling, and chart generation, with LLM (Claude 4.5 Sonnet) responsible for PII value inspection, natural language report generation, and persona-based verification. All outputs (HTML report, markdown summary, structured JSON) are delivered inline and made available for download. The structured JSON handoff artifact enables Feature 2 (Data Cleaning) to consume profiling results programmatically.

## Technical Context

**Language/Version**: Python (Claude.ai sandbox version — no version pinning available)
**Primary Dependencies**:

- `pandas` — pre-installed; version may change after ydata-profiling install
- `numpy` — pre-installed; version may change after ydata-profiling install
- `matplotlib` — transitive dependency of ydata-profiling
- `ydata-profiling` ≥ 4.18.1 — installed via pip at pipeline start (approved library per constitution amendment)
- `scikit-learn` — pre-installed (not used in Feature 1 but available)

**Storage**: No persistent storage — all data lives in the Claude.ai session. Session-ephemeral files written to sandbox filesystem for download.
**Testing**: Manual verification via evaluation suite (4 structured eval cases). Automated testing deferred to V2 (pytest, pandera, hypothesis not available in Claude.ai sandbox).
**Target Platform**: Claude.ai web interface with built-in Python tools (sandboxed)
**Project Type**: LLM-powered data analysis pipeline (conversational interface)
**Performance Goals**: Complete profiling pipeline (validation → report delivery) within a single Claude.ai session. No re-upload or re-submission required.
**Constraints**:

- No pip install except for approved libraries (ydata-profiling)
- ydata-profiling install mutates pre-installed package versions — must install first
- No persistent storage beyond the active session
- No cloud, Docker, or containerization
- No external API keys needed (Claude.ai handles authentication)
- PII: basic warning only in V1; raw data values never in logs or reports
- All reports must pass plain-language compliance (Level B user)
- LLM persona validation loop required for NL report accuracy
- File size limits: hard reject >500K cells; warn 100K–500K cells

**Scale/Scope**: Single CSV, single user, single session. MVP quality — robust edge case handling required per constitution. Not production-ready for consumer credit banking data (deferred to post-MVP).

## Constitution Check

*GATE: Checked before Phase 0 research. Re-checked after Phase 1 design.*

| Check | Status | Note |
|-------|--------|------|
| Python only | ✅ PASS | Claude.ai sandbox Python; no other languages |
| Approved libraries only | ✅ PASS | pandas, numpy, matplotlib, ydata-profiling, scikit-learn — all on approved list |
| pip install permitted | ✅ PASS | Constitution amended: pip install allowed for approved libraries in MVP |
| No prohibited frameworks | ✅ PASS | No frameworks outside approved list |
| No persistent storage | ✅ PASS | Session-ephemeral files only; no database |
| No cloud or Docker | ✅ PASS | Data processed via Claude.ai/Anthropic API only |
| No API keys needed | ✅ PASS | Claude.ai handles authentication; no .env required for MVP |
| PII — basic warning only | ✅ PASS | Two-layer detection with warning; no pipeline halt in V1 |
| PII — never in logs | ✅ PASS | FR-016 enforced; raw data values excluded from logs and reports; `sensitive=True` + `samples=0` in ydata-profiling config |
| LLM verification ritual | ✅ PASS | Data Analyst persona validates NL report against profiling data |
| Plain-language commitment | ✅ PASS | FR-007 enforced in LLM prompt constraints; what/why/impact template required |
| Mandatory justification template | ✅ PASS | What/why/impact applied to Key Findings and Recommendations |
| Edge cases handled | ✅ PASS | Empty CSV, single-row, duplicate columns, special chars, all-missing columns, mixed types, non-CSV files — all covered |
| V1 Definition of Done | ✅ PASS | 3 constitution CSVs (NYC TLC, Instacart/Dunnhumby, UCI) validated as end-to-end acceptance tests in Phase 3 |
| Output format — markdown reports | ✅ PASS | NL report as markdown; HTML profiling report; JSON handoff |
| Skill handoff contract | ✅ PASS | DM-010 defines Feature 2 handoff: NL report markdown + structured JSON |

No FAIL items. Constitution Check: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/001-data-profiling/
├── plan.md                          # This file
├── research.md                      # Phase 0 — 8 research questions resolved
├── data-model.md                    # Phase 1 — 10 schemas (DM-001 to DM-010)
├── quickstart.md                    # Phase 1 — end-to-end walkthrough
└── contracts/                       # Phase 1 — pipeline step contracts
    ├── install-dependencies.md
    ├── validate-input.md
    ├── detect-quality-issues.md
    ├── scan-pii.md
    ├── run-profiling.md
    ├── generate-charts.md
    ├── generate-nl-report.md
    ├── verify-report.md
    ├── deliver-outputs.md
    └── evaluation-suite.md
```

### Pipeline Architecture

```text
Pipeline Execution Order (orchestrated by LLM in Claude.ai session):

1. install_dependencies      [Pre-pipeline]  — pip install ydata-profiling
2. validate_input             [FR-001–003,013,015] — CSV validation + run ID
3. detect_quality_issues      [FR-009–012]    — 4 pandas-based quality checks
4. run_profiling              [FR-004]        — ydata-profiling → HTML + stats
5. scan_pii                   [FR-008]        — heuristic + LLM PII detection
6. generate_charts            [FR-006]        — 3 matplotlib charts
7. generate_nl_report         [FR-005,007]    — LLM draft NL report (Phase 1)
8. verify_report              [Constitution]  — Data Analyst persona review (Phase 2)
9. deliver_outputs            [FR-014]        — inline delivery + file downloads
```

### Output Files (session-ephemeral)

```text
{run_id}-profile.html                — ydata-profiling HTML report
{run_id}-summary.md                  — Final NL report (post-verification)
{run_id}-profiling-data.json         — Structured handoff for Feature 2
{run_id}-chart-missing.png           — Missing values bar chart (conditional)
{run_id}-chart-dtypes.png            — Data type distribution bar chart
{run_id}-chart-histograms.png        — Numeric distribution histograms (conditional)
```

All files are session-ephemeral — they exist only in the Claude.ai sandbox for the duration of the session.

## Complexity Tracking

No constitution violations. One constitution amendment required and approved:

| Amendment | Rationale | Resolution |
|-----------|-----------|------------|
| pip install permitted in MVP for approved libraries | ydata-profiling is on the approved list but not pre-installed; install succeeds and is required for FR-004 | Constitution v1.1.0 to be updated to allow pip install for approved libraries |

## Phase 3 Sequencing Constraints

The following dependency order MUST be enforced when tasks.md is produced in Phase 2.

**Gate 1 — Evaluation fixtures before implementation testing:**

```
MUST COMPLETE FIRST:
  - All 7 evaluation fixture CSVs created (synthetic, anonymized)
  - All 4 evaluation .md files authored with pass criteria confirmed
THEN AND ONLY THEN:
  - Pipeline implementation tested against evaluation suite
```

**Gate 2 — Pipeline steps in dependency order:**

```
MUST COMPLETE FIRST:
  - install_dependencies implemented and verified
  - validate_input implemented and tested
THEN:
  - detect_quality_issues implemented and tested
  - run_profiling implemented and tested
THEN:
  - scan_pii implemented and tested
  - generate_charts implemented and tested
THEN:
  - generate_nl_report prompt engineered and tested
  - verify_report prompt engineered and tested
THEN AND ONLY THEN:
  - deliver_outputs implemented and tested
  - Full pipeline end-to-end test
```

**Gate 3 — Constitution CSV acceptance tests:**

```
MUST COMPLETE FIRST:
  - Full pipeline passing all 4 evaluation suite cases
THEN AND ONLY THEN:
  - End-to-end acceptance tests with:
    1. NYC TLC Trip Records
    2. Kaggle Instacart / Dunnhumby "The Complete Journey"
    3. UCI dataset (mixed numeric and categorical)
  - All 3 must produce complete profiling outputs
```

---

## Delivered — Phase 0 + Phase 1

| Artifact | Status |
|----------|--------|
| Scratch pad (v1.0 — all 8 questions resolved) | ✅ Complete |
| Assumption log (12 assumptions — all approved) | ✅ Complete |
| plan.md — filled-in header | ✅ Complete |
| research.md — 8 research questions resolved | ✅ Complete |
| data-model.md — 10 schemas (DM-001 to DM-010) | ✅ Complete |
| quickstart.md — end-to-end walkthrough | ✅ Complete |
| contracts/install-dependencies.md | ✅ Complete |
| contracts/validate-input.md | ✅ Complete |
| contracts/detect-quality-issues.md | ✅ Complete |
| contracts/scan-pii.md | ✅ Complete |
| contracts/run-profiling.md | ✅ Complete |
| contracts/generate-charts.md | ✅ Complete |
| contracts/generate-nl-report.md | ✅ Complete |
| contracts/verify-report.md | ✅ Complete |
| contracts/deliver-outputs.md | ✅ Complete |
| contracts/evaluation-suite.md — 4 evaluations with binary pass criteria | ✅ Complete |

## Deferred — Phase 2 + Phase 3

| Artifact | Phase | Notes |
|----------|-------|-------|
| tasks.md — sequenced implementation tasks | Phase 2 | Produced by `/speckit.tasks` command |
| Pipeline implementation (all 9 steps) | Phase 3 | Contracts complete; implementation TBD |
| Evaluation fixture CSVs (7 files) | Phase 3 | Specifications defined; content TBD |
| LLM prompt engineering (NL report + verification) | Phase 3 | Constraints defined; prompts TBD |
| Constitution CSV acceptance tests (NYC TLC, Instacart, UCI) | Phase 3 | Gate 3 — after pipeline passes eval suite |
| Constitution amendment (pip install) | Phase 3 | Text update to constitution.md v1.1.0 |