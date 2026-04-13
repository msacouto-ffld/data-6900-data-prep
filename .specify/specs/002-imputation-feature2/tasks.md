# Tasks: Data Transformation with Persona Validation

**Input**: Design documents from `specs/002-data-transformation/`
**Prerequisites**: plan.md, spec_002_02.md, research.md, data-model.md, quickstart.md, contracts/
**Platform**: Claude Agent Skill (claude.ai custom Skill)
**Feature 1 dependency**: Feature 1 (Data Profiling) must be implemented and tested before Feature 2 can run end-to-end. Feature 2 consumes Feature 1's output files.

---

## Skill Structure (Target)

The plan's `src/` directory structure is remapped to a Claude Agent Skill directory:

```text
data-cleaning/
├── SKILL.md                         # Main instructions + pipeline workflow
├── CATALOG.md                       # DM-103 transformation catalog reference
├── REPORT-TEMPLATE.md               # DM-109 report template reference
├── PROMPTS.md                       # LLM persona prompts (propose, review, verify, report, light-verify)
├── scripts/
│   ├── load_inputs.py               # load_feature1_outputs (contract: load-feature1-outputs.md)
│   ├── schemas.py                   # DM-101 through DM-113 as dicts/dataclasses
│   ├── catalog.py                   # DM-103 transformation catalog (Python dict)
│   ├── thresholds.py                # DM-108 high-impact thresholds (Python dict)
│   ├── metrics.py                   # capture_metrics() function
│   ├── high_impact.py               # check_high_impact() function
│   ├── run_id.py                    # Run ID generation
│   ├── execute_transformations.py   # Orchestrator (contract: execute-transformations.md)
│   ├── step_1_column_names.py       # Step 1: column name standardization
│   ├── step_2_drop_missing.py       # Step 2: drop all-missing columns
│   ├── step_3_type_coercion.py      # Step 3: type coercion + sub-dispatchers
│   ├── step_4_invalid_categories.py # Step 4: invalid category cleanup
│   ├── step_5_imputation.py         # Step 5: missing value imputation
│   ├── step_6_deduplication.py      # Step 6: deduplication
│   ├── step_7_outliers.py           # Step 7: outlier treatment
│   ├── jargon_scan.py               # scan_jargon (contract: scan-jargon.md)
│   ├── deliver_outputs.py           # deliver_outputs (contract: deliver-outputs.md)
│   └── mistake_log.py               # collect_mistake_log (contract: collect-mistake-log.md)
└── tests/
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

**Mapping rationale**: Agent Skills use a SKILL.md file as the entry point, bundled markdown files for reference content Claude reads on-demand, and a `scripts/` subdirectory for Python code Claude executes via bash. LLM-owned contracts (propose, review, verify, generate report, light verification) become instructions in SKILL.md and PROMPTS.md. Script-owned contracts become Python files in `scripts/`.

---

## Phase 1: Setup (Skill Scaffolding)

Purpose: Create the Agent Skill directory structure and the SKILL.md entry point.

- [ ] **T001** Create the `data-profiling-and-cleaning/` Skill directory with the full subdirectory structure shown above: `scripts/`, `tests/`, `tests/fixtures/`. Create empty placeholder files for all Python scripts, markdown reference files, and test files. Do not write implementation content yet — this task establishes the file tree only.

- [ ] **T002** Write the SKILL.md YAML frontmatter and top-level instructions. The frontmatter must include `name: data-cleaning` and a `description` (max 1024 characters) that tells Claude when to trigger this Skill — specifically when a user requests data cleaning after Feature 1 profiling has completed. The body should contain: (1) a Purpose section summarizing the 7-step pipeline, (2) a Prerequisites section stating Feature 1 must have run, (3) a Workflow Overview section listing the pipeline stages (load → propose → review → execute → verify → report → jargon scan → deliver) with references to the appropriate script or markdown file for each stage, and (4) an Error Reference table matching the quickstart error table. Keep the body under 500 lines per Agent Skill best practices. Reference CATALOG.md, REPORT-TEMPLATE.md, and PROMPTS.md using relative links — do not inline their content.

**Checkpoint**: Skill directory exists with SKILL.md. Claude can discover and trigger the Skill, though no pipeline logic works yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

Purpose: Schemas, configuration, utility functions, and reference files that all pipeline stages depend on. No pipeline stage can be implemented until this phase is complete.

⚠️ CRITICAL: No user story work can begin until this phase is complete.

- [ ] **T003** [P] Write `scripts/schemas.py` implementing all data model schemas from DM-101 through DM-113 as Python dicts or dataclasses. Each schema must include all fields, types, and required/optional designations exactly as defined in data-model.md. Include a validation function for each schema that checks required keys and types — returning a list of violations rather than raising immediately. This file is imported by every other script. Covers: DM-101 (Feature 1 inputs), DM-102 (run metadata), DM-103 (catalog reference), DM-104 (transformation plan), DM-105 (review panel output), DM-106 (approved plan), DM-107 (step execution result), DM-108 (thresholds reference), DM-109 (report template reference), DM-110 (metadata JSON output), DM-111 (cleaned CSV guarantees), DM-112 (mistake log), DM-113 (human review escalation).

- [ ] **T004** [P] Write `scripts/catalog.py` implementing the `TRANSFORMATION_CATALOG` dict from DM-103, and the required-parameters-per-strategy table from DM-104. Include a `validate_parameters(strategy, parameters)` function that checks required parameters are present for a given strategy and returns missing parameter names. This is consumed by the execution engine for parameter validation before each step.

- [ ] **T005** [P] Write `scripts/thresholds.py` implementing the `HIGH_IMPACT_THRESHOLDS` dict from DM-108. Include the step dependency map from DM-106 as a `STEP_DEPENDENCIES` dict mapping each step number to its list of dependency step numbers.

- [ ] **T006** [P] Write `scripts/metrics.py` implementing the `capture_metrics(df)` function exactly as defined in RQ-004 of research.md. The function accepts a pandas DataFrame and returns a dict with dataset-level metrics (row_count, column_count, total_missing, total_duplicates) and per-column metrics (dtype, plus type-specific stats: mean/min/max for numeric, mode/unique_count for categorical/object, min/max for datetime, true_count/false_count for boolean). Handle all-null columns gracefully (return None for stats).

- [ ] **T007** [P] Write `scripts/high_impact.py` implementing the `check_high_impact(metrics_before, metrics_after, thresholds, affected_columns)` function from RQ-005. The function compares before/after metrics against the thresholds dict and returns a list of high-impact flag dicts following the DM-107 `high_impact_flags` schema. Each flag must include the actual value, the threshold that triggered it, and a human-readable message with both values for report context.

- [ ] **T008** [P] Write `scripts/run_id.py` implementing the `generate_run_id()` function that produces IDs in the format `transform-YYYYMMDD-HHMMSS-XXXX` where XXXX is a 4-character random hex string. Uses `datetime` and `secrets` standard library modules only.

- [ ] **T009** [P] Write `scripts/mistake_log.py` implementing the collection API and write function from the collect-mistake-log contract. Must include: (1) `init_mistake_log(transform_run_id)` returning a DM-112 dict with empty entries list, (2) `log_entry(mistake_log, entry_type, step, transformation_type, description, resolution, affected_columns, confidence_score)` appending to the entries list, (3) `write_mistake_log(mistake_log, transform_run_id)` writing to `{transform_run_id}-mistake-log.json`. The `affected_columns` field must contain column names only — never raw data values. The `description` and `resolution` fields must use generic descriptions, not data samples.

- [ ] **T010** [P] Write `CATALOG.md` — a markdown reference file containing the full transformation catalog from DM-103 formatted as a readable table (step number, step name, available strategies, required/optional parameters per strategy). Claude reads this file when constructing the LLM proposal prompt. Keep it factual and concise — this is reference data, not instructions.

- [ ] **T011** [P] Write `REPORT-TEMPLATE.md` — a markdown reference file containing the DM-109 report template with all 10 sections in order (Header, Executive Summary, Dataset Comparison, Transformations Applied, Rejected Transformations, Skipped Transformations, High-Impact Summary, Next Steps, Verification Summary, Pipeline Log Summary). Include the 3-part justification template (What was done? Why? What is the impact?) and the rules for omitting empty sections. Claude reads this file when generating the transformation report.

- [ ] **T012** Write `PROMPTS.md` — a markdown reference file containing the LLM persona prompts for all five LLM-owned pipeline stages. Each prompt must be a self-contained section Claude can read and use directly. Sections: (1) **Propose Transformations** — system prompt embedding the catalog, 7-step order, DM-104 output format, no-issues detection logic, and re-proposal instructions for rejection rounds (from propose-transformations contract and RQ-002). (2) **Review Panel** — multi-perspective system prompt with Conservative/Business/Technical views, fixed confidence score table (95/82/67/50/35), DM-105 output format, and verdict instructions (from review-panel contract and RQ-003). (3) **Data Analyst Verification** — verification checklist (8 checks from verify-output contract and RQ-007), verification result output format, and failure handling instructions. (4) **Report Generation** — 10 prompt constraints from generate-report contract, referencing REPORT-TEMPLATE.md for the template. (5) **Light Verification** — prompt for the no-issues path from light-verification contract, including fallback behavior if concerns are found. This file depends on T010 (CATALOG.md) and T011 (REPORT-TEMPLATE.md) being complete, since it references both.

**Checkpoint**: Foundation ready — all schemas, configuration, utilities, and reference content are in place. User story implementation can begin.

---

## Phase 3: User Story 1 — LLM Suggests and Validates Cleaning Transformations (Priority: P1) 🎯 MVP

**Goal**: Given Feature 1 profiling outputs, the LLM proposes cleaning transformations from the guided catalog, and the review panel challenges and validates them — producing approved decisions with confidence scores.

**Independent Test**: Provide a synthetic profiling JSON with known issues. Verify the LLM proposes transformations for each issue, the review panel challenges at least one assumption, confidence scores are assigned, and rejected suggestions are replaced with justified alternatives.

### Implementation for User Story 1

- [ ] **T013** [US1] Write `scripts/load_inputs.py` implementing the load_feature1_outputs contract (FR-101). The script must: (1) glob for `profile-*-profiling-data.json` in the sandbox, (2) handle missing/multiple/ambiguous files per the contract's error conditions, (3) validate required top-level JSON keys (run_id, validation_result, quality_detections, pii_scan, profiling_statistics), (4) load the NL report markdown (`{profiling_run_id}-summary.md`), (5) load the original raw CSV from `validation_result.file_path`, (6) generate the transform run ID using `run_id.py`, (7) build and return `run_metadata` (DM-102), `profiling_data`, `nl_report`, and `raw_df`. Print the console output specified in the contract. All error messages must match the contract exactly.

- [ ] **T014** [US1] Add the proposal workflow instructions to SKILL.md. After loading inputs, SKILL.md must instruct Claude to: (1) read PROMPTS.md § Propose Transformations, (2) read CATALOG.md for the catalog reference, (3) construct the proposal prompt with profiling_data, nl_report, and run_metadata as context, (4) parse the LLM output as DM-104, (5) validate the plan using `schemas.py` validation functions, (6) if `no_issues_detected` is true, branch to the light verification workflow, (7) print the console output showing all 7 steps (issues found and skipped steps) as shown in the quickstart. This task modifies SKILL.md only — the LLM prompt content lives in PROMPTS.md (T012).

- [ ] **T015** [US1] Add the review panel workflow instructions to SKILL.md. After the proposal, SKILL.md must instruct Claude to: (1) read PROMPTS.md § Review Panel, (2) construct the review prompt with the transformation plan (DM-104) and profiling_data as context, (3) parse the LLM output as DM-105, (4) validate the review output using `schemas.py`, (5) for REJECTED verdicts: collect rejection context, re-invoke propose_transformations with rejection_context (max 2 rounds per step per RQ-003), re-run review on revised proposals only, (6) for confidence score 35: build escalation object (DM-113), present options to user inline per quickstart Step 4, handle user response (number, "skip", or natural language guidance), (7) after all reviews are final: build the approved plan (DM-106) by merging DM-104 and DM-105, including rejected_transformations, skipped_transformations, human_review_decisions, and dependency_warnings, (8) log persona rejections and consensus failures to the mistake log via `mistake_log.py`. Print condensed console output per quickstart Step 4.

**Checkpoint**: User Story 1 complete. Given profiling outputs, the Skill can load them, propose transformations, run the review panel with rejection loops and human escalation, and produce an approved plan (DM-106). No transformations are executed yet.

---

## Phase 4: User Story 2 — Execute Approved Transformations (Priority: P1) 🎯 MVP

**Goal**: Execute the approved transformation plan from User Story 1 in the fixed 7-step order, producing a cleaned CSV with before/after metrics and high-impact flags for each step.

**Independent Test**: Provide a raw CSV and a pre-approved DM-106 plan with known transformations. Execute and verify: correct row/column counts, no unapproved changes, deterministic output, valid metrics.

### Implementation for User Story 2

- [ ] **T016** [P] [US2] Write `scripts/step_1_column_names.py` implementing the step 1 function with signature `step_1_column_names(df, transformations, rng) -> pd.DataFrame`. Must handle strategies: `standardize_to_snake_case` (lowercase, replace spaces/special chars with underscores, strip leading/trailing underscores, collapse consecutive underscores), `remove_special_characters` (remove non-ASCII characters from column names), `rename_duplicates_with_suffix` (append `_2`, `_3`, etc. to duplicate column names). Must not modify any data values — only column names. Must validate required parameters before executing.

- [ ] **T017** [P] [US2] Write `scripts/step_2_drop_missing.py` implementing the step 2 function with signature `step_2_drop_missing(df, transformations, rng) -> pd.DataFrame`. Must handle strategy: `drop_column` (drop columns where 100% of values are missing). Must validate that targeted columns actually have 100% missing values before dropping — if not, raise an exception rather than silently dropping a column with data.

- [ ] **T018** [P] [US2] Write `scripts/step_3_type_coercion.py` implementing the step 3 function with signature `step_3_type_coercion(df, transformations, rng) -> pd.DataFrame`. Must dispatch internally based on strategy: `coerce_to_target_type` (pandas `astype()` with errors='coerce' — values that cannot be converted become NaN), `parse_dates_infer_format` (`pd.to_datetime()` with `format='mixed'`, fallback to NaT — note: `infer_datetime_format` is deprecated in recent pandas, use `format='mixed'` instead), `parse_currency_strip_symbols` (regex strip currency symbols + commas, convert to float), `parse_percent_to_float` (regex strip '%', divide by 100). Each sub-strategy is a separate internal function. Must validate required parameters (e.g., `target_type` for `coerce_to_target_type`).

- [ ] **T019** [P] [US2] Write `scripts/step_4_invalid_categories.py` implementing the step 4 function with signature `step_4_invalid_categories(df, transformations, rng) -> pd.DataFrame`. Must handle strategies: `map_to_canonical_value` (apply `canonical_mapping` dict to replace values), `group_rare_into_other` (replace categories below `threshold_pct` frequency with "Other"), `flag_for_human_review` (no data modification — log the flag only). Must validate required parameters (`canonical_mapping` for map strategy, `threshold_pct` for group strategy).

- [ ] **T020** [P] [US2] Write `scripts/step_5_imputation.py` implementing the step 5 function with signature `step_5_imputation(df, transformations, rng) -> pd.DataFrame`. Must handle strategies: `drop_rows` (drop rows where targeted columns have missing values), `drop_column` (drop the column entirely), `impute_mean`, `impute_median`, `impute_mode` (compute statistic from non-null values, fill NaN), `impute_constant` (fill with `fill_value` parameter), `impute_most_frequent` (same as mode), `impute_unknown` (fill with "Unknown" or custom `fill_value`). scikit-learn SimpleImputer receives `random_state=42` where applicable. Must validate required parameters (`fill_value` for `impute_constant`).

- [ ] **T021** [P] [US2] Write `scripts/step_6_deduplication.py` implementing the step 6 function with signature `step_6_deduplication(df, transformations, rng) -> pd.DataFrame`. Must handle strategies: `drop_exact_keep_first` (`df.drop_duplicates(keep='first')`), `drop_exact_keep_last` (`df.drop_duplicates(keep='last')`), `keep_most_recent` (requires a date column to sort by — validate parameter), `keep_most_complete` (keep the row with fewest NaN values among duplicates), `flag_for_human_review` (no removal — add a flag column or log only). All sort operations use `kind='mergesort'` for deterministic stable sort.

- [ ] **T022** [P] [US2] Write `scripts/step_7_outliers.py` implementing the step 7 function with signature `step_7_outliers(df, transformations, rng) -> pd.DataFrame`. Must handle strategies: `cap_at_percentile` (clip values at `percentile_lower` and `percentile_upper`), `remove_rows` (remove rows where targeted column values exceed percentile thresholds), `flag_only` (no data modification — add an outlier flag to the report), `winsorize` (replace values beyond percentile thresholds with the threshold values). Must validate required parameters (`percentile_lower`, `percentile_upper` for cap/winsorize).

- [ ] **T023** [US2] Write `scripts/execute_transformations.py` implementing the orchestrator from the execute-transformations contract. Must: (1) initialize RNG with `numpy.random.default_rng(42)`, (2) iterate through `STEP_ORDER` (7 steps in fixed order), (3) for each step: get approved transformations from DM-106, skip if none (recording `skipped: true` in step result), validate parameters using `catalog.py`'s `validate_parameters()`, call `capture_metrics()` before, execute the step function, call `capture_metrics()` after, run `check_high_impact()`, build DM-107 step result, (4) check for dependency warnings on skipped steps using `STEP_DEPENDENCIES` from `thresholds.py`, (5) write cleaned CSV as `{transform_run_id}-cleaned.csv` with `df.to_csv(index=False)`, (6) handle errors per contract: missing parameters → halt with exact message, step exception → halt with exact message, empty DataFrame → halt with exact message. Wrap execution in try/finally to ensure mistake log is written. Print console output per quickstart Step 5. Depends on: T003 (schemas), T004 (catalog), T005 (thresholds), T006 (metrics), T007 (high_impact), T009 (mistake_log), T016–T022 (step functions).

- [ ] **T024** [US2] Add the execution workflow instructions to SKILL.md. After the review panel produces an approved plan (DM-106), SKILL.md must instruct Claude to run the execution orchestrator, passing the raw DataFrame, approved plan, and run metadata, then proceed to verification. This task modifies SKILL.md only.

**Checkpoint**: User Stories 1 and 2 complete. The Skill can load profiling outputs, propose and validate transformations, and execute them to produce a cleaned CSV with full metrics. Report and downloads not yet available.

---

## Phase 5: User Story 3 — Generate Transformation Report with Before/After Comparison (Priority: P1) 🎯 MVP

**Goal**: Generate a plain-language transformation report (markdown) with 3-part justifications, before/after comparisons, confidence scores, rejected transformations, and high-impact flags. Run jargon scan to ensure plain-language compliance.

**Independent Test**: Provide step results from a completed execution. Verify the report follows the DM-109 template exactly, every transformation has what/why/impact, confidence scores are present, jargon scan passes.

### Implementation for User Story 3

- [ ] **T025** [US3] Write `scripts/jargon_scan.py` implementing the scan-jargon contract (FR-120). Must include: (1) `ACRONYM_WHITELIST` set (CSV, HTML, JSON, NaN, PII, ID, LLM, NL, ASCII, UTC, ISO, PDF, API), (2) `scan_jargon(report_text)` function that finds all uppercase sequences (2+ chars) via `\b[A-Z]{2,}\b`, removes whitelisted terms, checks remaining terms for first-use definitions using the pattern from RQ-008, returns list of truly undefined terms. The script portion is deterministic. The LLM fix (if undefined terms are found) is handled by SKILL.md instructions, not by this script.

- [ ] **T026** [US3] Add the report generation and jargon scan workflow instructions to SKILL.md. After execution and verification, SKILL.md must instruct Claude to: (1) read PROMPTS.md § Report Generation, (2) read REPORT-TEMPLATE.md for the template, (3) construct the report generation prompt with step_results, approved_plan, review_outputs, verification_result, run_metadata, profiling_data, and high_impact_flags, (4) generate the report following the 10 prompt constraints from the generate-report contract, (5) run `scripts/jargon_scan.py` on the report text, (6) if undefined terms are found: make one targeted LLM call to define or replace them, apply corrections — no second scan, (7) print console output per quickstart Step 7. This task modifies SKILL.md only.

**Checkpoint**: User Stories 1, 2, and 3 complete. The Skill produces a cleaned CSV, a validated transformation report, and all pipeline metadata.

---

## Phase 6: User Story 4 — Download Cleaned CSV and Transformation Report (Priority: P1) 🎯 MVP

**Goal**: Write all output files to the sandbox and present them to the user for download — cleaned CSV, transformation report, metadata JSON (DM-110 — the Skill B handoff artifact), and mistake log.

**Independent Test**: After a full pipeline run, verify all 4 files exist, filenames use the same run ID, metadata JSON contains `produced_by: "skill_a"`, and row/column counts match the actual CSV.

### Implementation for User Story 4

- [ ] **T027** [US4] Write `scripts/deliver_outputs.py` implementing the deliver-outputs contract (FR-108, FR-114, FR-115). Must: (1) write the transformation report to `{transform_run_id}-transform-report.md`, (2) build and write the metadata JSON (DM-110) from run_metadata, approved_plan, profiling_data PII warnings, and skipped transformations (both `user_skipped` and `skill_boundary` sources per contract), (3) write the mistake log via `write_mistake_log()`, (4) the cleaned CSV is already written by execute_transformations — verify it exists. Handle file write failures as non-blocking for inline delivery per contract error conditions. Return the list of filenames for presentation.

- [ ] **T028** [US4] Add the delivery workflow instructions to SKILL.md. After jargon scan, SKILL.md must instruct Claude to: (1) run `scripts/deliver_outputs.py`, (2) display the report inline in the conversation, (3) present the download links using the exact format from quickstart Step 9 (4 files: cleaned CSV, report, metadata JSON, mistake log), (4) include the "What to Do Next" guidance from quickstart. This task modifies SKILL.md only.

**Checkpoint**: User Stories 1–4 complete. The full standard pipeline works end-to-end: load → propose → review → execute → verify → report → jargon scan → deliver. The user receives all output files.

---

## Phase 7: User Story 5 — LLM Data Analyst Persona Verifies Output (Priority: P2)

**Goal**: After execution, the Data Analyst persona reviews the cleaned dataset against the original, checking for unintended side effects, metric consistency, and unapproved changes. This is the "Test" step of the Verification Ritual (Read → Run → Test → Commit).

**Independent Test**: Provide a cleaned CSV with an intentional row count error (447 vs. expected 450). Verify the persona catches the discrepancy. On a correct output, verify it reports PASS with no false positives.

### Implementation for User Story 5

- [ ] **T029** [US5] Add the verification workflow instructions to SKILL.md. After execution but before report generation, SKILL.md must instruct Claude to: (1) call `capture_metrics()` on the final cleaned DataFrame to get `final_metrics`, (2) collect all `high_impact_flags` from step results, (3) read PROMPTS.md § Data Analyst Verification, (4) construct the verification prompt with profiling_data (original CSV stats), step_results, approved_plan, final_metrics, and high_impact_flags, (5) parse the verification result (status: PASS | CORRECTIONS_APPLIED | DISCREPANCY_FOUND, with corrections, confirmed, and discrepancies lists), (6) if DISCREPANCY_FOUND: flag to the user inline per quickstart Step 6 — do not halt the pipeline, (7) if verification LLM call fails entirely: deliver report with disclaimer per verify-output contract, (8) pass verification_result to the report generation stage. Print console output per quickstart Step 6. This task also updates SKILL.md's workflow order to insert verification between execution (Phase 4) and report generation (Phase 5).

**Checkpoint**: User Stories 1–5 complete. The Verification Ritual is fully implemented: Read (propose + review) → Run (execute) → Test (Data Analyst verify) → Commit (deliver verified output).

---

## Phase 8: User Story 6 — Maintain Skill A Mistake Log (Priority: P2)

**Goal**: Ensure all pipeline events (persona rejections, execution errors, edge-case warnings, consensus failures, high-impact flags, human review decisions) are captured in the mistake log throughout execution.

**Independent Test**: Run the pipeline on a CSV that triggers at least one persona rejection and one edge-case warning. Verify both events appear in the mistake log with correct types, and the log contains no raw data values.

### Implementation for User Story 6

- [ ] **T030** [US6] Audit all pipeline stages in SKILL.md and all scripts for complete mistake log coverage. Verify that `log_entry()` calls are present for every event type defined in the collect-mistake-log contract: `persona_rejection` (during review panel — T015), `execution_error` (during execute_transformations — T023), `edge_case_warning` (no-issues path, high-impact triggers — T023, T031), `consensus_failure` (score = 35 escalation — T015), `high_impact_flag` (after each step — T023), `human_review_decision` (user response to escalation — T015). Add any missing `log_entry()` calls. Verify that no `log_entry()` call includes raw data values in `description`, `resolution`, or `affected_columns`. This task touches multiple files but is a single audit-and-fix pass.

**Checkpoint**: User Stories 1–6 complete. All pipeline events are captured in the mistake log.

---

## Phase 9: Light Verification and No-Issues Path (Cross-Cutting)

Purpose: Implement the alternative workflow for datasets with no quality issues (FR-121).

- [ ] **T031** [US1] Add the light verification workflow to SKILL.md. When `no_issues_detected` is true in the transformation plan (DM-104): (1) read PROMPTS.md § Light Verification, (2) construct the light verification prompt with profiling_data, nl_report, raw_df, and run_metadata, (3) if the persona confirms no issues: generate a simplified report (Executive Summary: "No data quality issues identified"; Dataset Comparison: before and after identical; Transformations Applied: "None"; Next Steps: normalization/encoding for Skill B; Verification Summary: PASS), deliver the original CSV unchanged as the cleaned output, and write all 4 output files as usual, (4) if the persona flags a concern: display the concern to the user per quickstart No-Issues Workflow, then enter the standard propose → review → execute pipeline, (5) if the LLM call fails: fall back to the standard workflow silently. Log the no-issues path as an `edge_case_warning` in the mistake log. This task depends on T013 (load_inputs), T012 (PROMPTS.md), T027 (deliver_outputs), and T009 (mistake_log).

**Checkpoint**: Both the standard pipeline and the no-issues path work end-to-end.

---

## Phase 10: Evaluation Fixtures and Evaluation Scripts

Purpose: Create synthetic test data and evaluation scripts per evaluation-suite.md.

### Evaluation Fixtures

- [ ] **T032** [P] Create `tests/fixtures/eval-profiling-standard.json` — a synthetic profiling JSON (DM-101 format) for a 500-row × 12-column dataset with the issues specified in eval-101: 2 columns with special characters in names, 1 column 100% missing, 1 column with mixed types (int + string), 1 column with 15% missing (numeric), 1 column with 8% missing (categorical), 50 exact duplicate rows. Must include all required top-level keys and follow Feature 1's DM-010 schema. No real PII — all synthetic data.

- [ ] **T033** [P] Create `tests/fixtures/eval-raw-500x12.csv` — a synthetic 500-row × 12-column CSV that matches the profiling data in `eval-profiling-standard.json`. Column names must include the 2 with special characters. Column values must include the mixed types, missing values, and duplicates described in the fixture. All data is synthetic and anonymized.

- [ ] **T034** [P] Create `tests/fixtures/eval-approved-plan.json` — a pre-approved DM-106 plan with known transformations matching the issues in `eval-profiling-standard.json`. Used by eval-102 to isolate execution testing from proposal logic. All strategies should be catalog strategies with correct parameters.

- [ ] **T035** [P] Create `tests/fixtures/eval-profiling-clean.json` — a synthetic profiling JSON where all `quality_detections` have `status: "clean"`. Used by eval-106 (no-issues scenario).

- [ ] **T036** [P] Create `tests/fixtures/eval-profiling-no-consensus.json` — a synthetic profiling JSON crafted to produce a step 5 imputation that triggers no consensus (confidence score 35). Must include a column with high enough missing percentage to cause panel disagreement (e.g., 34% missing in a numeric measure column). Used by eval-106 (human review escalation scenario).

- [ ] **T037** [P] Create `tests/fixtures/eval-profiling-high-dedup.json` — a synthetic profiling JSON where duplicate rows exceed 10% of total rows. Used by eval-106 (high-impact row reduction scenario).

- [ ] **T038** [P] Create `tests/fixtures/eval-cleaned-with-bug.csv` — a cleaned CSV based on `eval-raw-500x12.csv` after applying the `eval-approved-plan.json` transformations, but with an intentional row count error: 447 rows instead of the expected 450. Used by eval-105 (Data Analyst verification discrepancy detection).

### Evaluation Scripts

- [ ] **T039** [US1] Write `tests/eval_101_proposal.py` implementing the 10 pass criteria from eval-101 in evaluation-suite.md. The script loads `eval-profiling-standard.json`, runs the proposal and review panel stages, and checks: all issues addressed, 7-step structure, catalog strategies preferred, parameters present, review panel runs, at least one challenge, confidence scores valid, rejection loop works, issue prefix format, no fabricated issues. Output: PASS/FAIL per criterion with details.

- [ ] **T040** [US2] Write `tests/eval_102_execution.py` implementing the 10 pass criteria from eval-102. The script loads `eval-raw-500x12.csv` and `eval-approved-plan.json`, executes the pre-approved plan, and checks: output CSV exists, row count correct (450), column count correct (11), column names standardized, no missing in imputed columns, type consistency, no duplicates, no unapproved changes, determinism (run twice, compare with `numpy.allclose()` for numeric, exact match for non-numeric), before/after metrics present. Output: PASS/FAIL per criterion.

- [ ] **T041** [US3] Write `tests/eval_103_report.py` implementing the 11 pass criteria from eval-103. Checks: all required sections present, 3-part template, confidence scores, dataset comparison table, before/after per transformation, high-impact flags, plain language, no raw data values, Next Steps present, Verification Summary present, jargon scan passes. Output: PASS/FAIL per criterion.

- [ ] **T042** [US4] Write `tests/eval_104_downloads.py` implementing the 10 pass criteria from eval-104. Checks: all 4 files downloadable, filenames match run ID, metadata provenance (`produced_by: "skill_a"`), metadata counts match CSV, PII warnings carried, skipped transformations listed with `source: "skill_boundary"`, mistake log no raw data. Output: PASS/FAIL per criterion.

- [ ] **T043** [US5] Write `tests/eval_105_verification.py` implementing the 5 pass criteria from eval-105. Uses `eval-cleaned-with-bug.csv` for discrepancy detection and the clean eval-102 output for no-false-positives check. Output: PASS/FAIL per criterion.

- [ ] **T044** Write `tests/eval_106_edge_cases.py` implementing the 6 pass criteria from eval-106 across 5 scenarios: no-issues dataset, human review escalation, high-impact row reduction, dependency-aware skip, all-transformations-rejected-twice. Uses the scenario-specific fixture files. Output: PASS/FAIL per criterion.

**Checkpoint**: All evaluations can run against the implemented Skill. Results are binary PASS/FAIL per criterion.

---

## Phase 11: Polish and Cross-Cutting Concerns

Purpose: Final quality checks across the entire Skill.

- [ ] **T045** Review SKILL.md for Agent Skill best practices compliance: body under 500 lines, no deeply nested references (all references one level deep from SKILL.md), consistent terminology throughout, no time-sensitive information, workflow steps are clear and sequential, error reference table is complete. Trim or reorganize if over 500 lines.

- [ ] **T046** [P] Review all scripts for constitution compliance: no hardcoded secrets, no raw data values in logs, no libraries outside the approved list (pandas, numpy, scikit-learn, standard library), all identifiers masked or hashed in exported logs, determinism guarantees in place (seed 42, stable sort, explicit parameters).

- [ ] **T047** [P] Review all LLM prompts in PROMPTS.md for plain-language compliance (FR-119): basic statistical terms (mean, median, mode, outlier) permitted without explanation, method-specific terms (z-score, IQR (Interquartile Range), one-hot encoding, winsorize) explained on first use, all acronyms defined on first use.

- [ ] **T048** Run the quickstart walkthrough end-to-end against the implemented Skill. Verify that every user-facing message, console output, error message, and download presentation matches the quickstart document. Document any deviations and fix them.

---

## Dependencies and Execution Order

### Phase Dependencies

| Phase | Depends On | Blocks |
|-------|-----------|--------|
| Phase 1 (Setup) | Nothing | All other phases |
| Phase 2 (Foundational) | Phase 1 | All user stories (Phases 3–9) |
| Phase 3 (US1: Propose + Review) | Phase 2 | Phase 4 (execution needs approved plan) |
| Phase 4 (US2: Execute) | Phase 2, Phase 3 | Phase 5 (report needs step results) |
| Phase 5 (US3: Report + Jargon) | Phase 2, Phase 4 | Phase 6 (delivery needs report) |
| Phase 6 (US4: Deliver) | Phase 5 | Phase 7, 8, 9 (delivery is the final standard pipeline step) |
| Phase 7 (US5: Verify) | Phase 4 | None (inserts between execution and report) |
| Phase 8 (US6: Mistake Log Audit) | Phase 6 | None |
| Phase 9 (No-Issues Path) | Phase 2, T012, T013, T027 | None |
| Phase 10 (Evaluations) | Phase 6 (standard pipeline complete) | Phase 11 |
| Phase 11 (Polish) | All prior phases | None |

### Within-Phase Parallel Opportunities

- **Phase 2**: T003–T011 can all run in parallel (different files, no dependencies). T012 depends on T010 and T011.
- **Phase 4**: T016–T022 (step functions) can all run in parallel. T023 (orchestrator) depends on all step functions. T024 depends on T023.
- **Phase 10**: T032–T038 (fixtures) can all run in parallel. T039–T044 (eval scripts) depend on their respective fixtures and on the pipeline phases they test.

### Recommended Execution Sequence

1. Phase 1 → Phase 2 → Phase 3 → Phase 4 → **STOP AND VALIDATE** (eval-101, eval-102)
2. Phase 7 (insert verification into pipeline) → Phase 5 → Phase 6 → **STOP AND VALIDATE** (eval-103, eval-104, eval-105)
3. Phase 8 → Phase 9 → **STOP AND VALIDATE** (eval-106)
4. Phase 10 → Phase 11 → **FINAL VALIDATION** (all evals pass)

### Key Sequencing Note

Phase 7 (Data Analyst Verification) is listed as P2 in the spec but must be implemented before Phase 5 (Report Generation) in the recommended sequence. The verification result is an input to the report — the Verification Summary section depends on it. The recommended sequence above accounts for this dependency by placing Phase 7 before Phase 5 in the second validation cycle.

---

## Implementation Strategy

### MVP First (Standard Pipeline)

Complete Phases 1–4 in order. At that point, the core pipeline works: load → propose → review → execute. Validate with eval-101 and eval-102.

### Add Verification and Reporting

Complete Phase 7 (verification), then Phase 5 (report), then Phase 6 (delivery). This completes the full standard pipeline. Validate with eval-103, eval-104, and eval-105.

### Add Edge Cases and Audit

Complete Phases 8 and 9. This adds complete mistake log coverage and the no-issues path. Validate with eval-106.

### Polish and Ship

Complete Phases 10 and 11. All evaluations pass. Quickstart walkthrough matches implementation.

---

## Notes

- All file paths are relative to the `data-cleaning/` Skill root directory.
- `[P]` = can run in parallel with other `[P]` tasks in the same phase (different files, no dependencies).
- `[USn]` = maps to User Story n from spec_002_02.md for traceability.
- Feature 1 (Data Profiling) must be fully implemented before Feature 2 can be tested end-to-end. Feature 2's load_inputs script depends on Feature 1's output file format (DM-008, DM-010).
- The constitution's three CSV acceptance tests (NYC TLC, Instacart/Dunnhumby, UCI) run after both Skill A features and Skill B are complete. They are not part of this task list.
- Agent Skill constraints: SKILL.md body under 500 lines, `name` field lowercase letters/numbers/hyphens only, `description` max 1024 characters, all file references one level deep from SKILL.md.
