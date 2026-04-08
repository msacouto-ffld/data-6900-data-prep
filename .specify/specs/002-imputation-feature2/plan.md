# Implementation Plan: Data Transformation with Persona Validation

**Branch**: `002-data-transformation` | **Date**: 2026-04-08 | **Spec**: spec_002_02.md
**Input**: Feature specification from spec_002_02.md (Skill A — Feature 2)

---

## Summary

Feature 2 transforms a profiled dataset into a clean, decision-ready CSV through a 7-step pipeline orchestrated by Claude 4.5 Sonnet with multi-perspective persona validation. The LLM proposes cleaning transformations from a guided catalog, a review panel challenges assumptions from three perspectives (Conservative, Business, Technical), and approved transformations are executed deterministically via pandas/numpy/scikit-learn. Every decision is documented with a 3-part justification template, confidence scores, and before/after comparisons. The cleaned CSV, transformation report, and metadata JSON are delivered as the Skill B handoff package.

## Technical Context

**Language/Version**: Python (Claude.ai sandbox version, post ydata-profiling install)
**Primary Dependencies**: pandas, numpy, scikit-learn (pre-installed or installed by Feature 1)
**Storage**: No persistent storage — session-only (sandbox filesystem)
**Testing**: LLM Data Analyst persona verification (MVP); manual verification via transformation report; automated tests deferred to V2 (pytest, pandera, hypothesis)
**Target Platform**: Claude.ai with built-in Python tools (sandboxed) — MVP
**Project Type**: Conversational data pipeline (LLM-orchestrated)
**Performance Goals**: Complete transformation pipeline within a single Claude.ai session
**Constraints**: No pip install beyond approved libraries; no cloud; no persistent state; LLM non-deterministic (Python execution deterministic with fixed seeds)
**Scale/Scope**: Single CSV; up to 500,000 cells (hard limit from Feature 1)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Guardrail | Status | Notes |
|-----------|--------|-------|
| Python only | ✅ PASS | All code in Python |
| Approved libraries only | ✅ PASS | pandas, numpy, scikit-learn only (Feature 1 installs ydata-profiling for profiling; Feature 2 does not need additional installs) |
| pip install permitted | ✅ PASS | Constitution amendment from Feature 1 — permitted for approved libraries |
| No persistent storage | ✅ PASS | All state in-memory; files written to sandbox |
| No cloud/Docker | ✅ PASS | Runs entirely in Claude.ai sandbox |
| PII: basic warning only | ✅ PASS | PII warnings carried forward from Feature 1 in handoff metadata; no new PII scan |
| Secrets: never hardcoded | ✅ PASS | No secrets needed |
| Verification Ritual | ✅ PASS | Read → Run → Test → Commit implemented via propose → review panel → execute → Data Analyst verify |
| Persona validation | ✅ PASS | Two-phase: propose + multi-perspective review panel. No transformation passes unchallenged. |
| Confidence scores | ✅ PASS | 0–100 with fixed values per band; every transformation scored |
| Plain language | ✅ PASS | 3-part what/why/impact template; hybrid jargon scan; Level B user target |
| Skill Handoff Contract | ✅ PASS | Three-artifact handoff with provenance marker; Skill B validation logic defined |
| Mistake logging | ✅ PASS | JSON log per run; try/finally write; no raw data |
| V1 robustness | ✅ PASS | Edge cases: no-issues, consensus failure, high-impact, dependency-aware skip, max rejection loops |
| Determinism | ✅ PASS | Fixed RNG (seed 42); stable sort; explicit parameters. LLM decisions documented as recipe. Replay deferred to V2. |

**Constitution amendment required:** pip install permitted for approved libraries in MVP (carried from Feature 1; already documented).

## Project Structure

### Documentation (this feature)

```text
specs/002-data-transformation/
├── plan.md                                    # This file
├── research.md                                # Phase 0: 10 research questions resolved
├── data-model.md                              # Phase 1: 13 schemas (DM-101 to DM-113)
├── quickstart.md                              # Phase 1: end-to-end user walkthrough
├── contracts/
│   ├── load-feature1-outputs.md               # FR-101
│   ├── propose-transformations.md             # FR-102, FR-121
│   ├── review-panel.md                        # FR-103, FR-104, FR-105, FR-111, FR-122
│   ├── execute-transformations.md             # FR-103, FR-106, FR-107, FR-108, FR-113, FR-116
│   ├── verify-output.md                       # FR-103, FR-110
│   ├── generate-report.md                     # FR-109, FR-110, FR-111, FR-112, FR-113, FR-119
│   ├── scan-jargon.md                         # FR-120
│   ├── deliver-outputs.md                     # FR-108, FR-114, FR-115
│   ├── light-verification.md                  # FR-121
│   ├── collect-mistake-log.md                 # FR-117, FR-118
│   └── evaluation-suite.md                    # 6 evaluations with binary pass criteria
└── tasks.md                                   # Phase 2 (deferred — via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── pipeline/
│   ├── __init__.py
│   ├── load_inputs.py                         # load_feature1_outputs
│   ├── propose.py                             # propose_transformations (LLM prompt construction)
│   ├── review.py                              # review_panel (LLM prompt construction + rejection loop)
│   ├── execute.py                             # execute_transformations (orchestrator + step functions)
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── step_1_column_names.py
│   │   ├── step_2_drop_missing.py
│   │   ├── step_3_type_coercion.py            # Includes sub-dispatchers for date/currency/percent parsing
│   │   ├── step_4_invalid_categories.py
│   │   ├── step_5_imputation.py
│   │   ├── step_6_deduplication.py
│   │   └── step_7_outliers.py
│   ├── verify.py                              # verify_output (LLM prompt construction)
│   ├── report.py                              # generate_report (LLM prompt construction)
│   ├── jargon.py                              # scan_jargon (script scan + LLM fix)
│   ├── deliver.py                             # deliver_outputs (file writing + presentation)
│   ├── light_verify.py                        # light_verification (no-issues path)
│   └── mistake_log.py                         # collect_mistake_log (in-memory collection + write)
├── models/
│   ├── __init__.py
│   ├── schemas.py                             # DM-101 through DM-113 as dataclasses or TypedDicts
│   ├── catalog.py                             # DM-103 transformation catalog
│   └── thresholds.py                          # DM-108 high-impact thresholds
├── utils/
│   ├── __init__.py
│   ├── metrics.py                             # capture_metrics() function
│   ├── high_impact.py                         # check_high_impact() function
│   └── run_id.py                              # Run ID generation

tests/
├── fixtures/
│   ├── eval-profiling-standard.json
│   ├── eval-raw-500x12.csv
│   ├── eval-approved-plan.json
│   ├── eval-profiling-clean.json
│   ├── eval-profiling-no-consensus.json
│   ├── eval-profiling-high-dedup.json
│   └── eval-cleaned-with-bug.csv
├── eval_101_proposal.py
├── eval_102_execution.py
├── eval_103_report.py
├── eval_104_downloads.py
├── eval_105_verification.py
└── eval_106_edge_cases.py
```

**Structure Decision:** Single project with pipeline/ subdirectory for the main orchestration, models/ for schemas and configuration, utils/ for shared functions, and tests/ for evaluation fixtures and scripts.

## Phase 3 Sequencing Constraints

| Constraint | Reason |
|------------|--------|
| Feature 1 must be implemented and tested before Feature 2 | Feature 2 consumes Feature 1 outputs (DM-101, DM-010) |
| Schemas (DM-101–113) must be implemented before any pipeline code | All contracts depend on schema definitions |
| `capture_metrics()` and `check_high_impact()` must be implemented before step functions | Step execution depends on these utilities |
| Step functions must be implemented in order (1–7) | Each step function can be tested independently, but integration depends on prior steps |
| LLM prompt construction must be implemented after schemas | Prompts reference schema field names |
| Evaluation fixtures must be created before evaluations can run | Evaluations use synthetic data |
| Constitution CSV end-to-end tests run after both Skill A features and Skill B are complete | These are pipeline-level acceptance tests |

## Deferred

- **Phase 2**: tasks.md (via /speckit.tasks command)
- **Phase 3**: All implementation — pipeline code, step functions, LLM prompts, schemas, evaluation fixtures, constitution CSV acceptance tests
- **V2**: Structured recipe with replay mode (Option B determinism), automated testing (pytest/pandera/hypothesis), Claude Code Agent Skills integration
