# Tasks: Feature Engineering with Persona Validation

**Input**: Design documents from `/specs/003-feature-engineering/`
**Prerequisites**: plan.md (required), contracts/evaluation-suite.md (required), research.md, data-model.md, contracts/ (all 11 step contracts)

**Tests**: The evaluation suite defines 5 structured evaluations (eval-001 through eval-005) with binary pass criteria. Each evaluation is split into two tasks — one for fixture creation, one for the test run — so fixtures get locked in before tests run. This prevents modifying a fixture mid-test to make a failing test pass: if a test fails, the bug is in the code, not the fixture. Automated unit tests (pytest, pandera) are deferred to V2 — not available in the Claude.ai sandbox.

**Organization**: Tasks are organized into a setup phase, a foundational phase of shared utilities, and 3 user story phases plus a polish phase. Skill B's first 6 user stories (US1–US6 from the spec) are sequential pieces of one pipeline — handoff validation alone is not testable in isolation, and downloads can't exist without features to download. They are grouped into a single P1 phase ("Full Feature Engineering Pipeline") that delivers an end-to-end working MVP. US7 (Data Analyst verification) and US8 (mistake log refinement) are layered on top as P2 enhancements. This grouping is intentional and differs from Skill A's tasks.md, which had 4 independently testable user stories — Skill B's P1 stories are a sequential pipeline where the same principle (one phase per testable unit) yields a single combined phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (USA = User Story Group A combining US1–US6, US7, US8)
- Exact file paths use `{run_id}` prefix per FR-219

## Path Conventions

- **Pipeline scripts**: Executed inline in the Claude.ai sandbox (no persistent `src/` directory)
- **Output files**: Written to the Claude.ai sandbox filesystem (session-ephemeral)
- **Spec documents**: `/specs/003-feature-engineering/` (read-only reference)

---

## Phase 1: Setup

**Purpose**: Verify the pre-installed libraries Skill B needs are available before any pipeline code runs.

- [ ] T001 Verify pre-installed libraries — confirm `pandas`, `numpy`, and `scikit-learn` import successfully in the Claude.ai sandbox. No pip install needed for Skill B (Skill A handles ydata-profiling installation in Feature 1; Skill B does not need it). If any import fails, halt with: "Dependency error: required library {name} is not available. Please try again in a new Claude.ai session."

**Checkpoint**: All required libraries are importable. Skill B is ready to begin pipeline construction.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared utilities that must exist before any user story can be implemented — schema definitions, the run ID generator, the mistake log utility, and the jargon term list. Each lives in its own task so individual pieces can be tested in isolation before pipeline code starts referencing them.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Implement schema definitions for DM-001 through DM-012 — define all 12 data schemas from `data-model.md` as Python TypedDicts, dataclasses, or documented dict templates. These are referenced throughout the pipeline: DM-001 (cleaned CSV input rules), DM-002 (three-artifact handoff schema including Skill A's DM-110 metadata), DM-003 (validation result), DM-004 (dataset summary), DM-005 (feature proposal batch), DM-006 (persona challenge response), DM-007 (approved feature set with confidence score 0–100 fixed values), DM-008 (verification result), DM-009 (output CSV column rules), DM-010 (transformation report template), DM-011 (data dictionary template), DM-012 (mistake log entry format). All downstream tasks reference these schemas for input/output structure.

- [ ] T003 [P] Implement run ID generation utility — produce IDs in the format `feature-YYYYMMDD-HHMMSS-XXXX` where XXXX is a 4-character random hex suffix. Use `datetime.datetime.now()` for the timestamp and `secrets.token_hex(2)` for the suffix. Return as a string. Example output: `feature-20260411-091533-b2f1`. Test with at least 3 successive calls to confirm IDs are unique.

- [ ] T004 [P] Implement mistake log utility (`log_event`) per `contracts/deliver-outputs.md` and DM-012 — accept `log_path`, `event_type`, `step`, `details`, `action`, and optional `columns` parameters. Append a markdown-formatted entry to the file with ISO 8601 timestamp. Use a try/finally pattern so log writes don't crash the pipeline. Privacy: never include raw data values, only column names and aggregate descriptions. This utility is called from every pipeline step where loggable events occur. Test by writing 3 sample entries and inspecting the resulting markdown file.

- [ ] T005 [P] Implement jargon term list constant per `contracts/scan-jargon.md` — hardcode the ~20 term list (`one-hot encoding`, `label encoding`, `min-max scaling`, `z-score`, `standard deviation`, `normalization`, `standardization`, `variance`, `cardinality`, `dimensionality`, `dummy variable`, `feature extraction`, `imputation`, `interpolation`, `ordinal`, `nominal`, `categorical`, `continuous`, `discrete`, `skewness`, `kurtosis`, `correlation`, `multicollinearity`, `outlier detection`) as a Python constant `JARGON_TERMS`. Used by T020 (scan_jargon).

**Checkpoint**: Schemas defined, run ID generator works, mistake log utility writes to file successfully, jargon term list is available. Pipeline construction can now begin.

---

## Phase 3: User Story Group A — Full Feature Engineering Pipeline (Priority: P1) 🎯 MVP

**Goal**: An end-to-end working pipeline. A user uploads Skill A's three-artifact handoff (cleaned CSV + transform-report.md + transform-metadata.json), Skill B validates the handoff contract, runs PII checks, proposes features in 6 batches with persona validation, executes approved transformations, generates the transformation report and data dictionary, and delivers all outputs for download. This phase covers User Stories 1 through 6 from the spec because they form one sequential pipeline where individual stories cannot be tested in isolation.

**Independent Test**: Run eval-001 through eval-005 (T027–T035) to confirm handoff validation, full pipeline execution, PII handling, no-opportunity case, and edge case handling all work end-to-end.

**Covers**: US1 (handoff validation), US2 (LLM proposes + persona challenges), US3 (execute), US4 (report), US5 (dictionary), US6 (downloads) | All 11 step contracts except `verify-output` (US7) | Evaluations 1–5

**Task sub-sections within this phase:**

| Group | Tasks | Count | Description |
|-------|-------|-------|-------------|
| Pipeline steps | T006–T008 | 3 | Handoff validation, PII scan, dataset summary |
| Feature proposals | T009 | 1 | LLM proposes features across all 6 batch types |
| Persona prompts | T010–T012 | 3 | One prompt per challenge persona |
| Challenge wiring | T013 | 1 | Rejection cycles, confidence scoring, batch cap |
| Execution batches | T014–T019 | 6 | One per transformation type (different code each) |
| Report and output | T020–T023 | 4 | Jargon scan, report, dictionary, delivery |
| Fast-path + orchestration | T024–T025 | 2 | No-opportunity case, full pipeline wiring |
| Evaluation fixtures | T026, T028, T030, T032, T034 | 5 | Synthetic test data (create early, lock in) |
| Evaluation runs | T027, T029, T031, T033, T035 | 5 | Test execution against locked fixtures |

**Recommended strategy**: Create all evaluation fixtures (T026, T028, T030, T032, T034) early in Phase 3, before pipeline implementation begins. This locks in your test data upfront so it cannot be influenced by implementation choices.

### Pipeline Step Implementation

- [ ] T006 [USA] Implement `validate_handoff` per `contracts/validate-handoff.md` — accept the cleaned CSV path plus optional transform-metadata.json and transform-report.md paths. Run all 16 validation checks in contract order: file exists → parses as CSV → ≥1 column → ≥1 row → cell count ≤500K → cell count warning → provenance check (`produced_by == "skill_a"` when metadata present) → contract version (`handoff_contract_version == "1.0"`) → no duplicate column names → snake_case ASCII column names (regex `r'^[a-z][a-z0-9_]*$'`) → no all-missing columns → no exact duplicate rows → consistent types per column → missing values check → metadata schema validation → report readability. Generate run ID via T003. Return `validation_result` dict matching DM-003 schema. Console output must match the contract's ✅/ℹ️ format. Hard-gate failures halt the pipeline with the contract's actionable error messages. Soft-gate warnings are logged via `log_event` and collected in `validation_result["warnings"]`. If metadata is absent, fall back to CSV-only mode (skip provenance and contract version checks).

- [ ] T007 [USA] Implement `scan_pii` per `contracts/scan-pii.md` — accept the DataFrame and `validation_result`. If `validation_result["has_metadata_json"]` is True, read the `pii_warnings` array from the transform-metadata.json and populate `pii_flags`. If False, run the heuristic Layer 1 scan: normalize column names to lowercase, split on delimiters (`_`, `-`, ` `, `.`), match against the contract's 5 PII type token lists. Heuristic matches produce `confidence: "high"`, `detection_source: "column_name_pattern"`. Return PII flags matching DM-003's `pii_flags` field. Console output must match the contract's 🔒/⚠️/✅ format. Log all PII findings via `log_event`. PII scanning does not halt the pipeline — findings are warnings only (V1 behavior).

- [ ] T008 [USA] Implement `generate_dataset_summary` per `contracts/generate-dataset-summary.md` — accept the DataFrame and `validation_result`. For each column, compute dtype, missing count/percentage, unique count, is_unique flag. For numeric columns, compute mean, std, min, max, median. For each column, extract up to 5 non-null sample values via `df[col].dropna().head(5).tolist()`. For PII-flagged columns, replace `sample_values` with `["[PII — values hidden]"]`. Attach Skill A's transform-report.md content as `skill_a_context` (string) if available. Attach Skill A's transform-metadata.json content as `skill_a_metadata` (dict) if available — provides column transformation history. Return `dataset_summary` dict matching DM-004 schema.

### Feature Proposal Task

- [ ] T009 [USA] Implement `propose_features` for all 6 batch types per `contracts/propose-features.md` — build a single parameterized LLM call that accepts `dataset_summary`, `batch_type`, `approved_features_so_far`, and `validation_result`. The call is invoked once per active batch type in sequence: (1) datetime_extraction, (2) text_features, (3) aggregations, (4) derived_columns, (5) categorical_encoding, (6) normalization_scaling. The surrounding code is the same for all 6 — only the prompt parameter changes. Apply all 7 prompt constraints from the contract: batch focus, context awareness (approved_features_so_far), benchmark required, implementation hint as advisory only, PII awareness, no-opportunity handling. For Batch 3 (aggregations), enforce the aggregate cap: maximum 10 features per batch; any proposals beyond 10 are documented in the transformation report's deferred section so they are not silently lost. Parse the LLM response into `feature_proposal_batch` matching DM-005 schema. If the LLM proposes features outside the batch type, queue them for the correct batch (do not drop). Console output per batch: 📋 with batch number, type, and proposed feature list. If a batch has no applicable columns, return empty proposal with `skipped_reason`. If the LLM fails to produce a structured proposal, retry once. Design and test the 6 prompt variations together — verify each with a small fixture containing the relevant column types.

### Persona Prompts (one per challenge persona)

- [ ] T010 [P] [USA] Implement Feature Relevance Skeptic persona prompt per `contracts/challenge-features.md` — design and test the LLM system prompt for the redundancy check persona. The persona evaluates each proposed feature for redundancy (>0.95 correlation with existing or previously approved features) and information gain. Returns a structured response matching DM-006 schema with `persona: "feature_relevance_skeptic"`. Test against a feature set that includes intentional redundancy (e.g., a derived ratio nearly identical to an existing column) and confirm the persona catches it.

- [ ] T011 [P] [USA] Implement Statistical Reviewer persona prompt per `contracts/challenge-features.md` — design and test the LLM system prompt for the method validity persona. The persona evaluates whether each proposed transformation method is appropriate for the actual data — checks for skewness, cardinality, variance, and edge cases that would produce NaN/infinity. Returns DM-006 with `persona: "statistical_reviewer"`. Test against a feature set that includes intentional method mismatches (e.g., normalizing a zero-variance column, one-hot encoding a 500-category column) and confirm the persona catches them.

- [ ] T012 [P] [USA] Implement Domain Expert persona prompt per `contracts/challenge-features.md` — design and test the LLM system prompt for the business sense persona. The persona evaluates whether each proposed feature would actually be useful to a data scientist, whether grouping keys make real-world sense, whether ratios could be misleading (zero denominators), and whether the benchmark comparison is convincing. Returns DM-006 with `persona: "domain_expert"`. Test against a feature set that includes intentional business-nonsense (e.g., a ratio with frequently-zero denominators) and confirm the persona catches it.

### Challenge Loop Wiring

- [ ] T013 [USA] Wire `challenge_features` loop per `contracts/challenge-features.md` — call all 3 challenge personas (T010, T011, T012) in sequence for each batch. Aggregate the three persona responses, determine approvals/rejections per feature, and assign confidence scores deterministically using the fixed-value table (95, 82, 67, 50, 35) based on challenge counts and resolution status. Implement the rejection cycle (max 2 cycles per feature) and the batch-level rejection cap (max 5 rejected features per batch before remaining are dropped without retry). Console output: 🔎 per persona call, then ✅ batch summary with approved/rejected count and confidence scores. Update the `approved_features_so_far` running tracker (DM-007) after the batch completes.

### Execution Tasks (one per batch type)

- [ ] T014 [P] [USA] Implement `execute_transformations` for Batch 1 (Date/Time Extraction) per `contracts/execute-transformations.md` — implement the pre-built code paths from the contract: `extract_day_of_week`, `extract_hour`, `extract_month`, `extract_quarter` using `pd.to_datetime(df[col]).dt.{accessor}`. Add `feat_` prefix to every new column. Handle NaN from failed datetime parsing — log via `log_event` and continue. Test with a small DataFrame containing a datetime column.

- [ ] T015 [P] [USA] Implement `execute_transformations` for Batch 2 (Text Features) per `contracts/execute-transformations.md` — implement `text_string_length` (`df[col].astype(str).str.len()`) and `text_word_count` (`df[col].astype(str).str.split().str.len()`). Add `feat_` prefix. Test with a small DataFrame containing a text column.

- [ ] T016 [P] [USA] Implement `execute_transformations` for Batch 3 (Aggregate Features) per `contracts/execute-transformations.md` — implement `groupby_agg` using the efficient `df.groupby(key).agg(...).reset_index()` + merge pattern from RQ-006. Add `feat_` prefix. Edge cases: grouping key with all unique values (every row is its own group), grouping key with single value (constant aggregate). Test with a small DataFrame containing an identifier column and a numeric column.

- [ ] T017 [P] [USA] Implement `execute_transformations` for Batch 4 (Derived Columns) per `contracts/execute-transformations.md` — implement `derived_ratio` (`df[col_a] / df[col_b]` with division-by-zero → NaN handling) and `derived_difference` (`df[col_a] - df[col_b]`). Add `feat_` prefix. Edge cases: division by zero replaced with NaN and logged via `log_event`. Test with a small DataFrame containing two numeric columns where one has a zero value.

- [ ] T018 [P] [USA] Implement `execute_transformations` for Batch 5 (Categorical Encoding) per `contracts/execute-transformations.md` — implement `one_hot_encode` (`pd.get_dummies(df, columns=[col], prefix='feat_' + name)` — prefix applied directly by get_dummies, which produces multiple columns like `feat_category_value1`, `feat_category_value2`, etc.) and `label_encode` (`sklearn.preprocessing.LabelEncoder().fit_transform(df[col])`). Note: one-hot expanded columns are sorted alphabetically within the batch per the DM-009 ordering rule. Edge cases: unknown categories during encoding logged and pipeline continues. Test with small DataFrames containing categorical columns of cardinality 4 and 50.

- [ ] T019 [P] [USA] Implement `execute_transformations` for Batch 6 (Normalization/Scaling) per `contracts/execute-transformations.md` — implement `min_max_scale` (`sklearn.preprocessing.MinMaxScaler().fit_transform(df[[col]])`) and `z_score_scale` (`sklearn.preprocessing.StandardScaler().fit_transform(df[[col]])`). Add `feat_` prefix. Edge cases: zero-variance column → skip scaling, log via `log_event`, document reason. Test with small DataFrames containing a normal numeric column and a zero-variance column.

### Report and Output Tasks

- [ ] T020 [USA] Implement `scan_jargon` per `contracts/scan-jargon.md` — accept `report_text` and `dictionary_text`. For each term in JARGON_TERMS (T005), search the text case-insensitively. For each found term, check whether a plain-language explanation appears within ~200 words (look for phrases like "which means", "this means", "in other words", "that is", parenthetical definitions, or sentences starting with the term followed by "is"/"refers to"). For any flagged terms, pass them to the LLM with the instruction: "Rewrite the following sections to include a brief, plain-language explanation of each flagged term. Do not change meaning or structure — only add clarity." Return the updated text. Non-blocking — failures rely on the verification persona (Layer 2, deferred to Phase 4) to catch jargon. Console output: 🔍 with flagged term count.

- [ ] T021 [P] [USA] Implement `generate_report` (initial version, without Verification Summary) per `contracts/generate-report.md` — accept `approved_features`, `rejected_features`, `validation_result`, `original_df`, and `engineered_df`. The LLM generates a markdown transformation report following the DM-010 template with all 9 prompt constraints from the contract: template enforcement, 3-part justification (what/why/impact), benchmark included, confidence scores displayed as N/100 with band, before/after table, rejected features documented, plain language (FR-223), no raw data values, truncation rule (>10 features → inline summary table + top 5 detailed; full report in download). Any aggregate proposals that were capped (beyond the 10-feature limit in Batch 3) must appear in the report's deferred section with their original justification so they are not silently lost. Note: the Verification Summary section will be populated by Phase 4 (T037); for now, leave it as a placeholder noting "Verification not yet implemented." Return the report markdown string. Console output: 📝 generation status.

- [ ] T022 [P] [USA] Implement `generate_dictionary` per `contracts/generate-dictionary.md` — accept `approved_features` and `engineered_df`. The LLM generates a markdown data dictionary following the DM-011 template. Each feature entry must contain: name (with `feat_` prefix), plain-language description, data type, source columns, transformation method, value range, missing value handling, notes. Self-contained entries — a data scientist must understand each entry without referring to the transformation report. No raw data values. Return the dictionary markdown string. Console output: 📝 generation status.

- [ ] T023 [USA] Implement `deliver_outputs` per `contracts/deliver-outputs.md` — accept `engineered_df`, `transformation_report`, `data_dictionary`, `validation_result`, and `mistake_log_path`. Write four files to the sandbox filesystem: `{run_id}-engineered.csv` (already written by T014–T019 batch execution), `{run_id}-transformation-report.md`, `{run_id}-data-dictionary.md`, and confirm `{run_id}-mistake-log.md` exists (already written by T004's append-as-you-go pattern). Display the transformation report inline in chat (truncated if >10 features per the contract). Display the data dictionary inline after the report. Present three primary files for download (CSV, report, dictionary) plus the mistake log (always shown — it is the complete operational record). Console output must match the contract's 📥 format. File write failures are non-blocking for inline delivery.

### Fast-Path and Pipeline Orchestration

- [ ] T024 [USA] Implement no-opportunity fast-path per RQ-013 — accept `dataset_summary` and `validation_result`. Check if the dataset has ≤2 columns OR every column is a unique identifier (all values unique). If so, skip the entire propose → challenge → execute loop and produce a no-opportunity report directly: the transformation report states "no feature engineering opportunities" with a specific reason, the data dictionary states no features were created, and the output CSV is identical to the input. Return a flag indicating whether the fast-path was triggered. This is called by T025 (orchestration) before entering the batch loop.

- [ ] T025 [USA] Wire pipeline orchestration — connect T006 through T023 in execution order: validate_handoff → scan_pii → generate_dataset_summary → check fast-path (T024) → if not fast-path: loop over 6 batch types calling propose_features (T009) and challenge_features (T013) per batch → execute_transformations (T014–T019 in batch order, alphabetical within each batch) → scan_jargon → generate_report → generate_dictionary → deliver_outputs. Manage the running `approved_features_so_far` tracker between batches. Halt the pipeline on any hard-gate failure with the appropriate error message. Log every pipeline event via `log_event`.

### Evaluation Tasks

> **Note**: Fixtures are created and locked in first; tests run against the locked fixtures. Create all fixtures (T026, T028, T030, T032, T034) early in Phase 3 before pipeline implementation begins — this locks in your test data so it cannot be influenced by implementation choices.

- [ ] T026 [P] [USA] Create fixtures for eval-001 (Handoff Contract Validation) — produce 5 synthetic files: `valid-simple.csv` (200 rows × 8 columns, all checks pass, mixed column types), `bad-duplicate-cols.csv` (2 duplicate column names), `bad-special-chars.csv` (column names with spaces and special characters like `$`), `bad-mixed-types.csv` (one column with mixed int/string values), `not-a-csv.txt` (plain text file with prose). Once created, do not modify these fixtures during T027.

- [ ] T027 [USA] Run eval-001 against fixtures from T026 — verify all 6 pass criteria from `contracts/evaluation-suite.md`: valid CSV proceeds past validation, duplicate columns produce specific actionable error message naming the columns, special characters produce specific actionable error message naming the columns, mixed types produce specific actionable error message naming the column, non-CSV rejected with clear error, all error messages are actionable (tell the user what to fix). Document results.

- [ ] T028 [P] [USA] Create fixture for eval-002 (Full Feature Engineering Pipeline) — produce `full-pipeline-test.csv` (500 rows × 12 columns) with: 2 datetime columns (`order_date`, `ship_date`), 3 categorical columns (`category` with 4 unique values, `region` with 8 unique values, `product_type` with 50 unique values), 5 numeric columns (`sale_amount`, `units_sold`, `unit_price`, `discount_pct`, `shipping_cost`), 1 identifier column (`account_id` with repeated values suitable for groupby), 1 text column (`product_description` with varying lengths), no PII. Do not modify during T029.

- [ ] T029 [USA] Run eval-002 against fixture from T028 — verify all 14 pass criteria from `contracts/evaluation-suite.md`: features proposed per non-skipped batch, persona challenges raised, fixed-value confidence scores (95/82/67/50/35) present, output CSV with `feat_` prefix, original 12 columns preserved, row count preserved at 500, transformation report follows DM-010 template, 3-part what/why/impact per feature, benchmarks present, rejected features documented (high-cardinality 50-value column should trigger persona challenge), data dictionary follows DM-011 with entry per feature, downloads available, plain language compliance, no raw data values. The Verification Summary section will show as placeholder until Phase 4.

- [ ] T030 [P] [USA] Create fixtures for eval-003 (PII Detection and Handling) — produce 2 synthetic files: `pii-dataset.csv` (200 rows × 10 columns with `customer_name`, `email`, `zip_code`, `account_number`, plus 6 numeric clean columns) and `pii-transform-metadata.json` (DM-110 schema with `produced_by: "skill_a"`, `handoff_contract_version: "1.0"`, and `pii_warnings` array containing the 4 PII columns). Do not modify during T031.

- [ ] T031 [USA] Run eval-003 against fixtures from T030 — run two scenarios: Run A uploads the CSV + metadata JSON (verify console shows "loaded 4 flags from Skill A transform metadata"), Run B uploads the CSV only (verify console shows "Running PII scan (heuristic)"). Verify all 7 pass criteria: all 4 PII columns flagged in both runs, 6 numeric columns clear, LLM notes PII columns in proposals, Domain Expert persona challenges any PII-derived features, no raw PII values appear in any output (report, dictionary, or mistake log).

- [ ] T032 [P] [USA] Create fixtures for eval-004 (No Feature Engineering Opportunities) — produce 2 synthetic files: `all-identifiers.csv` (100 rows × 3 columns where every value is unique — should trigger fast-path) and `ambiguous-data.csv` (100 rows × 5 columns mostly identifiers but with 1 numeric column — should go through standard persona loop). Do not modify during T033.

- [ ] T033 [USA] Run eval-004 against fixtures from T032 — verify all 6 pass criteria: `all-identifiers.csv` triggers the fast-path (no persona loop calls in console), `ambiguous-data.csv` goes through the standard persona loop, output CSV is identical to input in both cases, transformation report contains "no feature engineering opportunities" entry with specific reason, data dictionary states no engineered features were created, run ID is present in both outputs.

- [ ] T034 [P] [USA] Create fixtures for eval-005 (Edge Cases) — produce 5 synthetic files: `high-cardinality.csv` (a column with 500 unique categorical values), `zero-variance.csv` (a column where all values equal 42), `division-by-zero.csv` (where a ratio source column has zero values for the denominator), `column-explosion.csv` (a column whose one-hot encoding would produce 100+ columns), `bad-dates.csv` (a datetime column with some unparseable values). Do not modify during T035.

- [ ] T035 [USA] Run eval-005 against fixtures from T034 — verify all 7 pass criteria: high-cardinality triggers persona challenge with alternative encoding suggestion, zero-variance column scaling is skipped with documented reason, division by zero produces NaN replacement and log entry, column explosion is flagged in report with persona challenge, NaN from failed date parsing is documented and logged, no pipeline crashes occur, mistake log contains entries for each edge case event triggered.

**Checkpoint**: Full P1 pipeline is functional. A user can upload Skill A's three-artifact handoff and receive a feature-engineered CSV, transformation report, data dictionary, and mistake log. All 5 evaluations pass. The Verification Summary section of the transformation report is a placeholder — to be populated by Phase 4. **This is the MVP delivery point.**

---

## Phase 4: User Story 7 — Data Analyst Verification (Priority: P2)

**Goal**: After execution, an LLM Data Analyst persona reviews the feature-engineered output against the cleaned input. This persona is the "Test" step of the Verification Ritual — it confirms transformations match approved decisions and catches unintended side effects (NaN, infinity, missing columns, encoding errors). The Verification Summary section of the transformation report becomes populated with real review results.

**Independent Test**: Re-run eval-002 (T029) and confirm the Verification Summary section now contains real check results (not a placeholder), and that introduced errors in test scenarios are caught.

**Covers**: US7 (Data Analyst persona verification) | Adds: `verify_output` contract | Updates: `generate_report` to consume verification results

- [ ] T036 [US7] Implement Data Analyst persona prompt for `verify_output` per `contracts/verify-output.md` — design and test the LLM system prompt for the post-execution quality gate. The persona receives `original_df`, `engineered_df`, `approved_features`, and `validation_result`. Apply the 9-item verification checklist from the contract: row_count_preserved, original_columns_intact, feat_prefix_applied, expected_columns_present, no_unexpected_nan, no_infinity_values, encoding_correct, scaling_correct, no_data_leakage. For each check, record pass/fail/warning with details. If correctable issues are found (missing column, incorrect encoding), describe the correction. If uncorrectable issues are found, flag for human review and halt the pipeline. Return `verification_result` matching DM-008 schema. Console output: 🔎 per check, then ✅ summary with correction count.

- [ ] T037 [US7] Update `generate_report` (T021) to consume verification results — accept `verification_result` as a new input and populate the Verification Summary section per DM-010 template. Show the review status (PASS / CORRECTIONS APPLIED / ISSUES FOUND), checks performed, corrections made, and confirmed accurate items. Replace the placeholder text from Phase 3 with real verification content.

- [ ] T038 [US7] Update pipeline orchestration (T025) to call `verify_output` between `execute_transformations` and `scan_jargon`. The new pipeline order is: validate_handoff → scan_pii → generate_dataset_summary → check fast-path → propose+challenge loop (×6 batches) → execute_transformations → **verify_output** → scan_jargon → generate_report → generate_dictionary → deliver_outputs. If verification halts the pipeline, log the issue and surface the error to the user.

- [ ] T039 [US7] Re-run eval-002 with verification — run the full pipeline on `full-pipeline-test.csv` from T028. Confirm the Verification Summary section now contains real check results showing all 9 verification checks. Confirm `verification_status` in the report is "PASS" or "CORRECTIONS APPLIED" (not a placeholder). Add a deliberate test case: manually inject a missing column scenario and confirm the verification persona catches it.

**Checkpoint**: Data Analyst verification is live. Every pipeline run now passes through a quality gate before outputs are delivered. The Verification Summary in the transformation report contains real, structured review results. The Verification Ritual (Read → Run → Test → Commit) is fully implemented.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, end-to-end testing across multiple fixtures, mistake log verification, and preparation for Skill A integration.

- [ ] T040 [P] Run quickstart.md walkthrough — follow the end-to-end walkthrough in `quickstart.md` step by step with a fresh CSV. Confirm each step matches the documented behavior — same console output messages, same emoji prefixes (🔍, 🔒, 📋, 🔎, ⚙️, 📝, 🔍, 📥), same persona challenge format, same download presentation. Note any discrepancies for correction.

- [ ] T041 [P] Review all console output messages across the full pipeline — confirm emoji prefixes, formatting, and message text match their respective contracts exactly (validate-handoff, scan-pii, propose-features, challenge-features, execute-transformations, verify-output, scan-jargon, generate-report, generate-dictionary, deliver-outputs).

- [ ] T042 [P] Verify mistake log completeness — review every pipeline step and confirm each one calls `log_event` for the appropriate event types per DM-012: handoff_contract_violation, handoff_contract_warning, pii_warning, persona_rejection, persona_modification, edge_case_triggered, execution_error, verification_correction, verification_issue, jargon_scan_flag. Add any missing log calls. Re-run eval-005 (T035) and inspect the resulting mistake log — confirm each of the 5 edge case fixtures produces at least one corresponding entry, no entry contains raw data values, and the markdown formatting is consistent. Confirm `deliver_outputs` always presents the mistake log alongside the three primary files.

- [ ] T043 Run full pipeline back-to-back with multiple fixtures — execute the pipeline against `full-pipeline-test.csv` (T028), `pii-dataset.csv` (T030), and `ambiguous-data.csv` (T032) one after the other in the same Claude.ai session. Confirm each run produces complete outputs, no state leaks between runs, and each run gets its own unique run ID.

- [ ] T044 Skill A integration test — when Skill A is fully implemented, run an end-to-end test where Skill A processes a raw CSV and Skill B consumes Skill A's three-artifact output (cleaned CSV + transform-report.md + transform-metadata.json). Verify the handoff contract validation passes with real Skill A output (not synthetic fixtures). Confirm PII flags are correctly read from `transform-metadata.json`. **Note: this task is blocked on Skill A's delivery and may not be completable within Skill B's implementation timeline.** If Skill A is not ready, document the dependency and defer.

- [ ] T045 Full feature value benchmark — run the model comparison across at least 2 datasets. For each: run Skill B end-to-end, run evaluate_features.py for the performance delta, document baseline vs engineered metrics. Produce a summary table comparing deltas across datasets. Write a 1-paragraph recommendation on where AI-assisted feature engineering adds the most value vs where deterministic rules would be sufficient. This is the deliverable the project spec requires under "Benchmark results on at least two datasets."

**Checkpoint**: Skill B is complete. All evaluations pass. The pipeline runs reliably across multiple fixtures without state issues. The mistake log captures all event types. Skill A integration is verified (or deferred with documented dependency). Ready for Phase 3 constitution acceptance tests (NYC TLC, Instacart/Dunnhumby, UCI — see Notes).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — must complete first.
- **Foundational (Phase 2)**: Depends on Phase 1. **Blocks all user stories** — schemas, run ID, mistake log, and jargon list are needed throughout.
- **USA (Phase 3)**: Depends on Phase 2. Implements the core pipeline end-to-end. **Blocks Phase 4 and Phase 5**.
- **US7 (Phase 4)**: Depends on Phase 3. Adds the Data Analyst verification step.
- **Polish (Phase 5)**: Depends on Phase 3. Can run in parallel with Phase 4 — they touch different parts of the pipeline.

### Pipeline Step Sequencing (within a single run, after Phase 4)

The pipeline executes in this fixed order during every run:

```
validate_handoff → scan_pii → generate_dataset_summary
  → check fast-path (skip to report if no opportunities)
  → [Batch 1: propose + challenge] → [Batch 2: propose + challenge]
  → [Batch 3: propose + challenge] → [Batch 4: propose + challenge]
  → [Batch 5: propose + challenge] → [Batch 6: propose + challenge]
  → execute_transformations (in batch order, alphabetical within batch)
  → verify_output
  → evaluate_features (model comparison)
  → scan_jargon → generate_report → generate_dictionary → deliver_outputs
```

### Parallel Opportunities

**Within Phase 2 (Foundational):** T003, T004, T005 are independent utilities — can run in parallel. T002 (schemas) should come first since other tasks may reference schema names.

**Within Phase 3 (Pipeline Implementation):**
- T006 → T007 → T008 (sequential — each depends on the previous)
- **T010–T012** (3 persona prompt tasks) can run in parallel — each is an independent prompt
- T013 (challenge loop wiring) must come after T010–T012
- **T014–T019** (6 execute_transformations batch tasks) can run in parallel — each is an independent code path
- T020 (scan_jargon) is independent
- T021, T022 (generate_report and generate_dictionary) can run in parallel
- T023 (deliver_outputs) needs T021 and T022
- T024 (fast-path) is independent of the batch tasks
- T025 (orchestration) needs everything in T006–T024

**Within Phase 3 (Evaluations):**
- T026, T028, T030, T032, T034 (fixture creation) can all run in parallel — **recommended to do these first**
- T027, T029, T031, T033, T035 (eval runs) can run after T025 (pipeline built) + their respective fixtures

**Phase 4 vs Phase 5:** Can run in parallel — Phase 4 adds verification to the pipeline while Phase 5 validates the mistake log and polishes output.

---

## Implementation Strategy

### MVP First (Phase 3 Only)

1. Complete Phase 1: Verify libraries
2. Complete Phase 2: Build foundational utilities (schemas, run ID, mistake log, jargon list)
3. Complete Phase 3: Implement full pipeline + run all 5 evaluations
4. **STOP and VALIDATE**: All 5 evals pass — pipeline works end-to-end with placeholder verification summary
5. At this point, a user can upload Skill A's three-artifact handoff and get feature engineering working

### Incremental Delivery

1. Setup → Libraries verified
2. Foundational → Utilities ready
3. Phase 3 → Full pipeline works (MVP!) → Run all 5 evals
4. Phase 4 → Data Analyst verification live → Re-run eval-002
5. Phase 5 → Mistake log verified, polish complete → Re-run eval-005
6. Each phase adds value without breaking previous phases

---

## Notes

- All pipeline scripts execute inline in the Claude.ai sandbox — there is no persistent `src/` directory or version control
- All output files are session-ephemeral — they exist only for the duration of the Claude.ai session
- The pipeline uses a hybrid approach: deterministic Python scripts for validation, summary generation, execution, jargon scanning, and orchestration; LLM (Claude) for feature proposals, persona challenges, verification, report and dictionary generation
- The `feat_` prefix is added by the execution script (T014–T019), not by the LLM — the LLM proposes feature names without the prefix
- LLM-generated code is **never** executed directly — the `implementation_hint` field in DM-005 is advisory only. The execution script uses pre-built, tested code paths from the contract's transformation method table
- The mistake log is written append-as-you-go (T004) — it is preserved even if the pipeline crashes mid-run
- Confidence scores use fixed values (95, 82, 67, 50, 35) matching Skill A's DM-105 bands for cross-skill consistency
- LLM variability in feature proposals (T009), persona challenges (T010–T012, T036), and report/dictionary generation (T021, T022) is expected — consistent failures indicate prompt engineering issues, not code bugs
- The handoff contract version is `"1.0"` — Skill B validates this via T006

### Constitution Acceptance Tests (Separate Gate — Not Included as Tasks)

After all 5 evaluations pass and Skill A integration (T044) is verified, the plan requires end-to-end acceptance tests with 3 real-world datasets:

1. NYC TLC Trip Records (large, messy, time/location fields)
2. Kaggle Instacart / Dunnhumby "The Complete Journey" (retail transactions)
3. UCI dataset (mixed numeric/categorical)

These are **not included as tasks** in this file — they are a separate Phase 3 gate documented in the plan. They require real dataset downloads and are run manually after the pipeline is fully implemented and Skill A integration is confirmed working.
