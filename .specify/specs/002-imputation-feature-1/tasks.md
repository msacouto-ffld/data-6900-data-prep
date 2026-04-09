# Tasks: Data Profiling & Exploratory Report

**Input**: Design documents from `/specs/001-data-profiling/`
**Prerequisites**: plan.md (required), evaluation-suite.md (required), research.md, data-model.md, contracts/ (all 9 step contracts)

**Tests**: The evaluation suite defines 4 structured evaluations (eval-001 through eval-004) with binary pass criteria. Each evaluation task creates its own synthetic fixture CSV at test time. Automated unit tests (pytest, pandera) are deferred to V2 — not available in the Claude.ai sandbox.

**Organization**: Tasks are organized by user story to enable incremental delivery. Because Feature 1 is a linear pipeline, pipeline steps are placed in the **first user story that needs them**. Later user stories build on earlier steps incrementally. This preserves the plan's Gate dependencies while keeping each story phase self-contained.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths use `{run_id}` prefix per FR-015

## Path Conventions

- **Pipeline scripts**: Executed inline in the Claude.ai sandbox (no persistent `src/` directory)
- **Output files**: Written to the Claude.ai sandbox filesystem (session-ephemeral)
- **Spec documents**: `/specs/001-data-profiling/` (read-only reference)

---

## Phase 1: Setup

**Purpose**: Install the only external dependency before any pipeline code runs.

- [ ] T001 [US1] Install ydata-profiling per `contracts/install-dependencies.md` — run `pip install ydata-profiling -q`, verify import succeeds, confirm console output matches contract (📦/✅/❌ format). If install fails, halt with the contract's error message. This step must complete before any other task.

**Checkpoint**: `ydata-profiling` is importable. `matplotlib` is available as a transitive dependency.

---

## Phase 2: User Story 1 — Generate Data Profile Report (Priority: P1) 🎯 MVP

**Goal**: A user uploads a CSV and receives a complete profiling report: HTML statistical profile, inline charts, and a 7-section natural language report verified by the Data Analyst persona.

**Independent Test**: Run eval-001 (T009).

**Covers**: eval-001 (all 12 criteria) | Pipeline steps 2–9 (except PII scan, which is US2)

### Implementation for User Story 1

- [ ] T002 [US1] Implement `validate_input` per `contracts/validate-input.md` — accept a file path, run all 8 validation checks in contract order (file exists → CSV extension → pd.read_csv() → ≥1 column → ≥1 row → cell count ≤500K hard gate → cell count 100K–500K warning → single-row warning). Generate run ID per FR-015 format (`profile-YYYYMMDD-HHMMSS-XXXX`). Return `validation_result` dict matching DM-002 schema. Console output must match the contract's ✅ format. Hard-gate failures halt the pipeline with the contract's actionable error messages.

- [ ] T003 [US1] Implement `detect_quality_issues` per `contracts/detect-quality-issues.md` — accept the DataFrame and `validation_result`, run all 4 checks: duplicate column names (`df.columns.duplicated()`), special characters in column names (regex `r'^[a-zA-Z_][a-zA-Z0-9_]*$'`), all-missing columns (`df.isnull().all()`), mixed types (`col.dropna().map(type).nunique() > 1`). Return `quality_detections` list matching DM-003 schema. Console output must match the contract's ⚠️/✅ format. This step is informational — findings do not halt the pipeline.

- [ ] T004 [US1] Implement `run_profiling` per `contracts/run-profiling.md` — accept the DataFrame and `validation_result`, determine profiling mode (minimal if >50K cells), build the configuration dict with `sensitive=True` and `samples={"head": 0, "tail": 0}`, run `ProfileReport(df, **config)`, export HTML to `{run_id}-profile.html`, extract statistics from `report.get_description()` into DM-006 schema. Return `profiling_statistics` dict and `profiling_mode` string. Console output must match the contract's 📊/✅ format. If profiling fails, halt with the contract's error message.

- [ ] T005 [US1] Implement `generate_charts` per `contracts/generate-charts.md` — accept the DataFrame and `validation_result`, generate up to 3 charts: missing values bar (omit if zero missing), data type distribution bar (always), numeric histograms (omit if no numeric columns, cap at top 12 by variance). Apply the contract's style fallback chain (`seaborn-v0_8-whitegrid` → `seaborn-whitegrid` → default). DPI 150, font sizes 10pt/12pt. Save PNGs as `{run_id}-chart-*.png`. Return `chart_metadata` list matching DM-007 schema. Individual chart failures are non-blocking — set `included: false` and continue.

- [ ] T006 [US1] Implement `generate_nl_report` per `contracts/generate-nl-report.md` — the LLM (Large Language Model) generates a draft 7-section natural language report following the DM-008 template. All 8 prompt constraints from the contract must be enforced: template enforcement, data sourcing from `profiling_statistics` only, privacy rule (no raw values from `top_values`), plain language (FR-007), what/why/impact format, chart references based on `chart_metadata`, no fabrication, column-level summary cap at 30. The draft is not shown to the user — it passes to verification. Note: PII scan results will be empty (`[]`) until US2 is implemented; the PII Scan Results section should state "PII scanning not yet enabled" or equivalent.

- [ ] T007 [US1] Implement `verify_report` per `contracts/verify-report.md` — the LLM adopts the Data Analyst persona and reviews the draft report against the raw profiling data. Apply the 7-item validation checklist: statistical accuracy, completeness, PII coverage, no fabrication, plain language, chart references, privacy. Append the Verification Summary section (Corrections Made, Confirmed Accurate, Review Status: PASS or CORRECTIONS APPLIED). If verification fails entirely, deliver the draft with the contract's disclaimer. Console output must match the contract's 🔎/✅/⚠️ format.

- [ ] T008 [US1] Implement `deliver_outputs` per `contracts/deliver-outputs.md` — write `{run_id}-summary.md` (final NL report) and `{run_id}-profiling-data.json` (DM-010 handoff schema containing `validation_result`, `quality_detections`, `pii_scan`, `profiling_statistics`). Display the NL report inline with charts. Present all three files (`-profile.html`, `-summary.md`, `-profiling-data.json`) for download. Console output must match the contract's 📥 format. File write failure is non-blocking — the user still sees the inline report.

- [ ] T009 [US1] Evaluation test (eval-001) — create `eval-fixture-clean-500x12.csv` (synthetic: 500 rows × 12 columns, 2 columns with >20% missing, 1 column 100% missing, 1 mixed-type column, 2 numeric columns with outliers, no PII, standard column names). Run the full pipeline and verify all 12 pass criteria: HTML report exists and >0 bytes, NL report has all 7 sections, missing values reported with correct percentages (±1% tolerance), all-missing column flagged as Critical, mixed types reported, outliers mentioned, no fabricated issues, plain language, at least 2 charts displayed, Verification Summary present, downloads available, run ID present.

**Checkpoint**: User Story 1 is fully functional. A user can upload any CSV and get a profiling report with charts, verification, and downloads. PII scanning is stubbed (returns empty results).

---

## Phase 3: User Story 2 — Detect and Flag PII (Priority: P2)

**Goal**: The pipeline detects potential PII (Personally Identifiable Information) in the dataset using a two-layer approach: heuristic column-name matching (Layer 1) plus LLM value inspection on unflagged columns (Layer 2). PII warnings appear in the NL report without exposing raw data values.

**Independent Test**: Run eval-002 (T013).

**Covers**: eval-002 (all 8 criteria) | Pipeline step: `scan_pii`

### Implementation for User Story 2

- [ ] T010 [US2] Implement `scan_pii` Layer 1 (heuristic pre-scan) per `contracts/scan-pii.md` — normalize column names to lowercase, split on delimiters (`_`, `-`, ` `, `.`), match against the contract's 5 PII type token lists (direct_name, direct_contact, direct_identifier, indirect, financial). Matches produce `confidence: "high"`, `detection_source: "column_name_pattern"`. Return results matching DM-004 schema.

- [ ] T011 [US2] Implement `scan_pii` Layer 2 (LLM value inspection) per `contracts/scan-pii.md` — for columns **not flagged by Layer 1**, extract the first 5 non-null values (`df[col].dropna().head(5).tolist()`), send to the LLM for pattern analysis (email format, phone format, SSN format, etc.). Matches produce `confidence: "medium"`, `detection_source: "value_pattern_llm"`. Privacy constraint: the NL report must include column names and PII categories only — never raw values. Depends on T010.

- [ ] T012 [US2] Integrate `scan_pii` into the pipeline — slot PII scanning between `run_profiling` (T004) and `generate_charts` (T005) in the pipeline execution order. Update `generate_nl_report` (T006) to consume non-empty `pii_scan` results and populate the PII Scan Results section with ⚠️-formatted warnings per the contract. Update `deliver_outputs` (T008) to include `pii_scan` in the JSON handoff. Console output must match the contract's 🔒/⚠️/✅ format.

- [ ] T013 [US2] Evaluation test (eval-002) — create `eval-fixture-pii-200x10.csv` (synthetic: 200 rows × 10 columns with `customer_name`, `email`, `zip_code`, `account_number`, `field_7` containing phone-formatted strings, plus 5 numeric columns). Run the full pipeline and verify all 8 pass criteria: `customer_name` and `email` flagged as Direct PII, `zip_code` as Indirect, `account_number` as Financial, `field_7` flagged via Layer 2 (expected but may vary), all 5 PII columns flagged, 5 numeric columns not flagged, warnings follow ⚠️ format, no raw values in warnings.

**Checkpoint**: PII detection is live. The pipeline now warns users about potential PII without exposing actual values. User Story 1 still works — PII scan adds findings without breaking existing functionality.

---

## Phase 4: User Story 3 — Handle Edge Cases (Priority: P2)

**Goal**: The pipeline gracefully handles non-standard inputs: empty CSVs, single-row CSVs, duplicate column names, special characters in column names, and non-CSV files. Hard errors produce actionable messages. Soft edge cases proceed with appropriate warnings in the report.

**Independent Test**: Run eval-003 (T018).

**Covers**: eval-003 (all 6 criteria) | Enhancements to: `validate_input`, `detect_quality_issues`, `generate_nl_report`

### Implementation for User Story 3

- [ ] T014 [US3] Verify `validate_input` edge-case handling — create `edge-empty.csv` (headers only, no rows), `edge-single-row.csv` (1 header + 1 data row, 5 columns), and `edge-not-csv.txt` (prose text, not tabular). Test each: empty CSV should produce hard error "This CSV contains headers but no data rows.", non-CSV should produce hard error "This file is not a valid CSV.", single-row should proceed with a warning. These cases should already be handled by T002's validation rules. If any case fails, fix `validate_input`.

- [ ] T015 [US3] Verify `detect_quality_issues` edge-case handling — create `edge-duplicate-cols.csv` (8 columns, 2 pairs with duplicate names, 10 rows) and `edge-special-chars.csv` (columns named `Sales $`, `Name (Full)`, `📧 Email`, `Normal_Col`, `% Change`, 10 rows). Test each: duplicates should be flagged via FR-009, special characters via FR-010. These should already be handled by T003's detection rules. If any case fails, fix `detect_quality_issues`.

- [ ] T016 [US3] Verify NL report edge-case coverage — run the full pipeline on `edge-single-row.csv` and confirm the NL report includes a Statistical Limitations section. Run on `edge-duplicate-cols.csv` and confirm the report identifies which column names are duplicated. Run on `edge-special-chars.csv` and confirm the report identifies non-standard column names. If `generate_nl_report` does not surface these findings, update its prompt constraints.

- [ ] T017 [US3] Verify error message quality — confirm all hard-error messages (empty CSV, non-CSV) tell the user what to do to fix the issue. Confirm messages match the exact text from the `validate_input` contract. If messages are vague or missing actionable guidance, update the error handling.

- [ ] T018 [US3] Evaluation test (eval-003) — run eval-003 pass criteria against all 5 edge-case fixtures (created in T014–T015): empty CSV rejected with error, single-row processed with Statistical Limitations section, duplicate columns flagged in report, special characters flagged in report, non-CSV rejected with error, all error messages are actionable. Document results for each fixture independently.

**Checkpoint**: The pipeline handles all specified edge cases. Hard errors are clear and actionable. Soft edge cases produce appropriate warnings in the NL report. No silent failures or pipeline crashes.

---

## Phase 5: User Story 4 — Download Profiling Outputs (Priority: P2)

**Goal**: All three output files (HTML profile, markdown summary, JSON handoff data) are available for download with correct naming, valid content, and no raw data leakage.

**Independent Test**: Run eval-004 (T023).

**Covers**: eval-004 (all 6 criteria) | Refinements to: `deliver_outputs`

### Implementation for User Story 4

- [ ] T019 [US4] Verify download file integrity — after a full pipeline run with `eval-fixture-clean-500x12.csv` (from T009), confirm: `{run_id}-profile.html` exists, is >0 bytes, and opens in a browser; `{run_id}-summary.md` exists and contains the full 7-section report with Verification Summary; `{run_id}-profiling-data.json` exists and is valid JSON (parseable by `json.loads()`).

- [ ] T020 [US4] Verify filename consistency — confirm all three filenames use the same run ID from the report header. The run ID format is `profile-YYYYMMDD-HHMMSS-XXXX` (FR-015).

- [ ] T021 [US4] Verify HTML privacy compliance — open `{run_id}-profile.html` and confirm no raw data rows are displayed. The ydata-profiling config sets `samples={"head": 0, "tail": 0}` and `sensitive=True` — this should suppress sample data in the HTML report.

- [ ] T022 [US4] Verify JSON schema compliance — confirm `{run_id}-profiling-data.json` contains all 4 required top-level keys: `validation_result`, `quality_detections`, `pii_scan`, and `profiling_statistics`. Validate that each key's value matches its respective data model schema (DM-002, DM-003, DM-004, DM-006).

- [ ] T023 [US4] Evaluation test (eval-004) — run the full eval-004 pass criteria checklist: HTML downloadable and opens in browser, markdown downloadable with full report, JSON downloadable and valid, filenames match run ID, HTML has no raw data, JSON schema valid. Document results.

**Checkpoint**: All output files are complete, correctly named, and downloadable. The JSON handoff artifact is schema-valid and ready for Feature 2 (Data Cleaning) to consume.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and preparation for Feature 2 handoff.

- [ ] T024 [P] Run full pipeline on `eval-fixture-clean-500x12.csv` and `eval-fixture-pii-200x10.csv` back-to-back — confirm both produce complete outputs and no state leaks between runs.

- [ ] T025 [P] Review all console output messages across the full pipeline — confirm emoji prefixes (📦, 🔍, 📊, 🔒, 📈, 📝, 🔎, 📥), formatting, and message text match their respective contracts exactly.

- [ ] T026 Run `quickstart.md` validation — follow the end-to-end walkthrough in `quickstart.md` step by step with a fresh CSV. Confirm each step matches the documented behavior. Note any discrepancies for correction.

- [ ] T027 Verify Feature 2 handoff — confirm `{run_id}-profiling-data.json` (DM-010 schema) contains all data that Feature 2 (Data Cleaning) needs to consume: validation result, quality detections, PII scan results, and profiling statistics. Confirm the JSON is self-contained (no references to session-ephemeral files that won't exist in a new session).

**Checkpoint**: Feature 1 is complete. All 4 evaluations pass. The pipeline is ready for Feature 2 integration.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — must complete first. Installs ydata-profiling which all later phases need.
- **US1 (Phase 2)**: Depends on Phase 1. Implements the core pipeline end-to-end. **Blocks US2, US3, US4** — later stories build on this pipeline.
- **US2 (Phase 3)**: Depends on Phase 2. Adds PII scanning to the existing pipeline.
- **US3 (Phase 4)**: Depends on Phase 2. Can run in parallel with US2 — tests and refines existing pipeline steps without adding new ones.
- **US4 (Phase 5)**: Depends on Phase 2. Can run in parallel with US2 and US3 — verifies and refines output delivery.
- **Polish (Phase 6)**: Depends on Phases 3, 4, and 5 all being complete.

### Pipeline Step Sequencing (within a single run)

The pipeline executes in this fixed order during every run. This is the runtime sequence, not the task implementation order:

```
install_dependencies → validate_input → detect_quality_issues → run_profiling → scan_pii → generate_charts → generate_nl_report → verify_report → deliver_outputs
```

### Parallel Opportunities

- **Phases 3, 4, 5**: US2, US3, and US4 can proceed in parallel after US1 is complete, since:
  - US2 adds a new pipeline step (scan_pii) — no overlap with US3 or US4 tasks
  - US3 verifies existing steps (validate_input, detect_quality_issues) — no overlap with US2
  - US4 verifies output delivery — no overlap with US2 or US3
- **Phase 6**: T024 and T025 can run in parallel.

### Within User Story 1 (Critical Path)

Tasks T002–T008 must execute in this order — each step's output is the next step's input:

```
T002 (validate_input) → T003 (detect_quality_issues) → T004 (run_profiling) → T005 (generate_charts) → T006 (generate_nl_report) → T007 (verify_report) → T008 (deliver_outputs) → T009 (eval-001 test)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Install ydata-profiling
2. Complete Phase 2: Implement full pipeline (T002–T008)
3. **STOP and VALIDATE**: Run eval-001 (T009) — confirm full profiling report works end-to-end
4. At this point, a user can upload any CSV and get a profiling report with charts, verification, and downloads

### Incremental Delivery

1. Setup → Dependency installed
2. Add US1 → Full pipeline works → Run eval-001 (MVP!)
3. Add US2 → PII detection live → Run eval-002
4. Add US3 → Edge cases handled → Run eval-003
5. Add US4 → Downloads verified → Run eval-004
6. Polish → All evals pass, quickstart validated, Feature 2 handoff ready

### Gate 3 (Constitution Acceptance Tests)

After all 4 evaluations pass, the plan requires end-to-end acceptance tests with 3 real-world datasets:
1. NYC TLC Trip Records
2. Kaggle Instacart / Dunnhumby "The Complete Journey"
3. UCI dataset (mixed numeric and categorical)

These are **not included as tasks** in this file — they are a separate Phase 3 gate documented in the plan. They require real dataset downloads and are run manually after the pipeline is fully implemented and all evaluations pass.

---

## Notes

- All pipeline scripts execute inline in the Claude.ai sandbox — there is no persistent `src/` directory or version control
- All output files are session-ephemeral — they exist only for the duration of the Claude.ai session
- The pipeline uses a hybrid approach: deterministic Python scripts for validation/detection/profiling/charts, LLM (Claude) for PII value inspection, NL report generation, and persona-based verification
- `sensitive=True` and `samples={"head": 0, "tail": 0}` are enforced in ydata-profiling config as belt-and-suspenders privacy protection (FR-016)
- The NL report never includes raw data values from `top_values` or any other field — this is non-negotiable
- LLM variability in Layer 2 PII detection (T011) and NL report generation (T006) is expected — consistent failures indicate prompt engineering issues, not code bugs
- The JSON handoff file (`{run_id}-profiling-data.json`, DM-010 schema) is the contract between Feature 1 and Feature 2
- Evaluation fixture CSVs are created at test time within each evaluation task — they are synthetic, anonymized, and purpose-built for their respective eval criteria
