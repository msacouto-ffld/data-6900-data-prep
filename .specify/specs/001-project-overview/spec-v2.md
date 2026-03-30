# AI-Assisted Data Prep Pipeline — Project Overview (Version B: Python Tools MVP, Claude Code deferred to V2)

**Version**: 1.0 | **Date**: 2026-03-25 | **Status**: Under Review

---

## 1. Project Overview

- **Project Name:** AI-Assisted Data Prep Pipeline

- **Team:**

| Role | Person | Ownership |
|------|--------|-----------|
| PM | Margarida Sacouto | Constitution, project overview, coordination |
| Module A Owner | Xiao Pan | Data Cleaning (missing values, duplicates, type consistency, outliers, column names) |
| Module B Owner | Valerie Bien-Aime | Feature Engineering (feature generation, transformation documentation) |

- **Primary Users:**

| User Group | Module | Technical Level |
|------------|--------|-----------------|
| Non-technical business stakeholders | Module A (primary) | Level B — understands data concepts (e.g., "null," "duplicate"), cannot code |
| Data scientists | Module B (primary), Module A (secondary) | Technical — comfortable with code and statistical concepts |
| Data analysts | Module A (secondary), Module B (secondary) | Intermediate — works with data tools but may not code extensively |

- **Problem Statement:** Data scientists, data analysts, and non-technical business stakeholders spend significant time preparing large, messy datasets for analysis and modeling. Common repetitive tasks include format transformations (such as floats and dates), identifying and removing duplicates or near-duplicates, handling missing values through strategies such as dropping or imputing records, and extracting features. All of these tasks require careful documentation to maintain auditability and trust — yet documentation is often incomplete or inconsistent.

- **Goal:** Enable teams to produce consistent, auditable, and decision-ready datasets with reduced manual effort and controlled risk. The pipeline must document every transformation decision in plain language with justification, and all suggested actions must be approved by a human before execution.

- **Hallucination Tolerance:** **ZERO — Catastrophic.** The MVP is a deterministic pipeline (no AI generation). All transformation logic is rule-based and human-approved. V2 introduces AI-assisted suggestions via Claude Code, which will require the Verification Ritual (Read → Run → Test → Commit).

- **Platform Decision:**

| Phase | Platform | Rationale |
|-------|----------|-----------|
| **MVP** | Standard Python scripts, executed locally via CLI | Deterministic, no AI dependency, simpler to test and validate |
| **V2** | Claude Code with Claude Agent Skills | Adds AI-assisted interaction, natural-language approval, and inline explanations |

## 2. User Scenarios & Testing

### Scenario 1: End-to-End Data Preparation Pipeline

- **Priority:** P1

- **Given:** A user has a raw, messy CSV dataset

- **When:** The user runs the full preprocessing pipeline (Module A → Module B) via CLI

- **Then:** The system applies cleaning, imputation, and feature engineering rules — presenting each action for human approval via CLI prompts before execution — and returns a cleaned, feature-engineered dataset along with a plain-language transformation report (markdown file) following the mandatory justification template (What was done? Why? Alternatives considered and why rejected? Impact?)

- **Test:** Upload a sample raw CSV, run the pipeline via CLI, and verify that (1) data is cleaned and transformed correctly, (2) every transformation was approved by the user before execution, and (3) a complete transformation report is generated as a markdown file following the justification template

### Scenario 2: Run Data Cleaning Only (Module A)

- **Priority:** P2

- **Given:** A user has a raw CSV dataset with missing values, duplicates, type inconsistencies, and/or messy column names

- **When:** The user chooses to run only Module A for data cleaning via CLI

- **Then:** The system detects issues, suggests cleaning actions with justification via CLI prompts, waits for human approval (y/n or detailed options), executes approved actions, and returns cleaned data along with a markdown report explaining the steps taken and the rationale behind them

- **Test:** Upload a CSV with missing values, duplicates, and mixed types. Run only Module A. Verify that (1) the output dataset reflects the expected cleaning logic, (2) every action was presented for approval before execution, (3) rejected actions triggered the next best alternative, and (4) the documentation follows the mandatory justification template

### Scenario 3: Handle Conflicting Duplicates

- **Priority:** P2

- **Given:** A user has a dataset containing duplicate or near-duplicate records with conflicting values

- **When:** The user runs the preprocessing pipeline via CLI

- **Then:** The system detects the conflicting duplicates, presents the suggested handling logic for human approval via CLI prompts or flags them for review, and documents the actions taken with justification

- **Test:** Upload a dataset containing duplicate or near-duplicate records with conflicting fields, run the pipeline, and verify that conflicts are either resolved according to approved rules or clearly flagged, with documentation included in the output

### Scenario 4: Run Feature Engineering Only (Module B)

- **Priority:** P2

- **Given:** A user has a cleaned dataset (output of Module A or pre-cleaned data)

- **When:** The user chooses to run only Module B for feature engineering via CLI

- **Then:** The system suggests relevant features with justification via CLI prompts, waits for human approval, generates approved features, and produces a markdown report with before/after comparisons and benchmark references

- **Test:** Upload a cleaned CSV, run only Module B, and verify that (1) suggested features are relevant and justified, (2) the user approved each feature before generation, and (3) documentation includes benchmark comparisons

### Edge Cases

The pipeline must handle the following edge cases robustly (V1 requirement):

- Empty CSV (headers only, no rows) — fail with clear error message
- Single-row CSV — process with appropriate warnings about statistical limitations
- All values missing in a column — detect, suggest handling strategy, await approval
- Mixed types in a single column (e.g., "123", "abc", "45.6") — detect, suggest type resolution, await approval
- Special characters in column names (spaces, emojis, unicode) — detect and suggest standardization
- Duplicate column names — detect and suggest resolution
- Required columns missing — fail with clear error message indicating impact
- Malformed or inconsistent data types — warn and suggest resolution
- Imputation cannot be applied safely — flag for human review, do not proceed without approval

## 3. Functional Requirements

### Must Have (P1)

**Data Ingestion:**
- System MUST ingest raw datasets from CSV files (MVP scope — single file only).
- System MUST reject empty input files with a clear error message.
- System MUST require input data to have a valid tabular structure with headers/column names.

**Human-in-the-Loop Approval (NON-NEGOTIABLE):**
- System MUST present all suggested transformations for human approval before execution.
- System MUST use a CLI-based approval interaction: clear plain-language prompt → user confirms (y/n) or selects from options.
- System MUST present the next best alternative when a suggestion is rejected.
- System MUST clearly distinguish between automated decisions and user-defined transformations.
- System SHOULD support a `--help` flag with human-readable descriptions for every command.
- System SHOULD support a `--auto-approve` flag for experienced users, skipping confirmations for transformations below a configurable risk threshold. Transformations above the threshold MUST always require explicit approval.

**Data Cleaning (Module A):**
- System MUST detect and assess missing values in the input dataset.
- System MUST suggest imputation strategies to handle missing values, with justification.
- System MUST detect duplicate and near-duplicate records.
- System MUST handle conflicting duplicates according to approved rules or flag them for review.
- System MUST detect and suggest resolution for type inconsistencies.
- System MUST detect and suggest handling for outliers.
- System MUST detect and suggest standardization for messy column names (special characters, duplicates).

**Feature Engineering (Module B):**
- System MUST suggest relevant features with justification.
- System MUST apply feature engineering and format transformations (including data type conversions such as floats and dates) only after human approval.

**Documentation & Auditability:**
- System MUST generate documentation as markdown files following the mandatory justification template for every transformation:
  1. What was done?
  2. Why?
  3. What alternatives were considered (and why were they rejected)?
  4. What is the impact?
- System MUST produce a summary of applied preprocessing changes with before/after comparison context.
- System MUST log all transformations applied to the dataset in a structured format.
- System MUST generate a plain-language data quality report explaining issues found, actions taken, and rationale, including:
  - Key metrics before vs. after preprocessing (e.g., row counts, aggregates)
  - Number of records affected by each transformation
- System MUST assign a unique version or run ID to each pipeline execution.
- System MUST allow users to reproduce previous outputs using the same inputs and configuration.
- System MUST flag transformations that may significantly alter business-critical metrics.

**Plain-Language Compliance:**
- All documentation MUST be written in plain language understandable to non-developer stakeholders.
- Basic statistical terms (mean, median, mode, outlier) are permitted without explanation.
- Method-specific terms (z-score, IQR, one-hot encoding) MUST be explained on first use.
- All acronyms MUST be defined on first use.
- System MUST run an automated jargon scan to flag undefined acronyms and unexplained terminology.
- Every metric MUST include comparison context (before/after); new features MUST include benchmark comparisons.

### Should Have (P2)

- System SHOULD generate a data dictionary documenting all variables, including definitions and key attributes.
- System SHOULD allow users to override or refine suggested transformations before execution.
- System SHOULD support versioning of transformation pipelines for reproducibility and comparison.
- System SHOULD provide pre-configured defaults so non-technical users can run the pipeline with minimal flags.

### Could Have (P3)

- System COULD provide automated feature importance suggestions to support downstream modeling.
- System COULD include anomaly detection to identify unusual or outlier patterns in the dataset.

## 4. Technical Constraints

- **Platform (MVP):** Standard Python scripts, executed locally via CLI. No Claude Code dependency.
- **Platform (V2):** Claude Code with Claude Agent Skills, auto-discovered from `.claude/skills/` directory.
- **Language:** Python 3.10+ (team to confirm minimum version)
- **Dependency Philosophy:** Vanilla Python first. Libraries introduced only for tasks that are error-prone or impractical to implement from scratch.
- **MVP Dependencies:** pandas, pandera, hypothesis, numpy
- **Provisional:** scikit-learn (to be confirmed for Module B)
- **Post-MVP:** great_expectations
- **Dependency Management:** Version ranges in `requirements.txt`. New library adoption requires PM + relevant Module Owner approval and compatibility testing.
- **Testing:** pytest + pandera (schema validation) + hypothesis (property-based testing). Hybrid approach: pre-defined templates for common cases, dynamically generated for edge cases.
- **Data Format (MVP):** Single tabular CSV file only. XLSX, database tables, and multi-file joins are out of scope.
- **Output Format:** CSV (cleaned/engineered data) + Markdown (transformation reports)
- **Security:**
  - Data must remain local (no cloud deployment, no external API calls).
  - V1: Open-source, non-sensitive data only. No data leaves the local environment.
  - Post-MVP (V2 with Claude Code): Data processed through Anthropic's API. PII must be anonymized locally before any LLM interaction.
  - Never hardcode secrets. Store in local `.env`, include in `.gitignore`.
  - Logs must never contain data values. All identifiers must be masked or hashed.
  - System MUST ensure auditability of all transformations applied to the data.
- **PII Handling (V1):** Basic warning only (e.g., "Column X may contain PII — proceed with caution"). Hybrid detection: automated scan flags potential PII, human confirms.
- **PII Handling (Post-MVP):** Pipeline stops and alerts user. Cannot proceed until PII is handled externally.

### V2 Migration Path

To minimize rework when transitioning from MVP (Python tools) to V2 (Claude Code):

1. **Module boundaries = Skill boundaries:** Module A and Module B are designed with the same input/output contracts that future Agent Skills will use.
2. **Standardized handoff format:** The intermediate format between Module A and Module B is identical to the future Skill A → Skill B handoff contract.
3. **Report templates:** The same markdown justification template is used in MVP reports and future Claude Code inline reports.
4. **Test suite portability:** All pytest, pandera, and hypothesis tests work identically in both environments.
5. **SKILL.md preparation:** Each module's purpose, inputs, outputs, and constraints are documented in a format that can be directly converted to `SKILL.md` files for Claude Code.

## 5. Success Criteria

- [ ] **Functional:**
  - All P1 scenarios work end-to-end via CLI
  - Pipeline runs without errors on 3 test datasets:
    1. NYC TLC Trip Records (large, messy, time/location fields)
    2. Kaggle — Instacart / Dunnhumby "The Complete Journey" (retail transactions)
    3. UCI dataset (mixed numeric/categorical data)
  - Outputs include cleaned data, engineered features, and transformation report (markdown)
  - All edge cases handled (empty CSV, single-row, all-missing column, mixed types, special characters, duplicate column names)

- [ ] **Human-in-the-Loop:**
  - Every suggested transformation is presented for approval before execution via CLI
  - Rejected suggestions trigger next best alternative
  - No transformation executes without explicit human approval (unless `--auto-approve` is used for low-risk transformations)

- [ ] **Documentation Quality:**
  - Every transformation report follows the mandatory 4-part justification template
  - All reports pass the automated jargon scan
  - Every metric includes comparison context
  - A new team member can understand all reports without asking questions (stranger test)

- [ ] **Usability:**
  - Outputs for the same input dataset and configuration MUST be deterministic and reproducible
  - System MUST highlight any transformation that could materially impact key metrics (e.g., revenue, counts, averages)
  - Users MUST be able to trace every output field back to its original source and transformation steps
  - Non-technical users can run the pipeline with `--help` and pre-configured defaults

- [ ] **Business:**
  - Reduce manual data preparation time by at least 30%
  - Reduce data-related rework or corrections in downstream analysis
  - Increase stakeholder trust in data outputs (measured via user feedback or adoption)

## 6. Out of Scope

### Excluded Features

- ❌ Web UI / dashboard — Reason: MVP targets CLI-based usage
- ❌ Claude Code / AI-assisted interaction — Reason: Deferred to V2
- ❌ Building full machine learning models / automated model training — Reason: Pipeline ends at clean, feature-engineered data plus documentation
- ❌ Real-time or streaming pipelines — Reason: Scope is limited to batch preprocessing workflows
- ❌ Multi-file joins / merging multiple CSVs — Reason: Single CSV in, single output out
- ❌ XLSX or database table ingestion — Reason: MVP is CSV only
- ❌ Data storage or data warehouse capabilities — Reason: System operates on provided datasets and does not manage storage infrastructure
- ❌ Integrations with external systems — Reason: Data must remain local and external dependencies are restricted
- ❌ Deployment or orchestration tools (e.g., Airflow) — Reason: Pipeline execution is manual in this phase
- ❌ Cloud deployment — Reason: Fully local
- ❌ Consumer credit banking data — Reason: Deferred to post-MVP
- ❌ Full PII enforcement (stop and alert) — Reason: V1 has basic warning only; full enforcement deferred to post-MVP

The system is responsible for data preprocessing and transformation transparency. The user remains responsible for validating final outputs before use in business-critical decisions.

### Deferred to Future Versions

- 🔜 Claude Code with Claude Agent Skills (AI-assisted interaction, natural-language approval, inline explanations) — Target: V2
- 🔜 Web UI / dashboard — Target: V2+
- 🔜 Scheduling / automation of pipeline execution — Target: V2+
- 🔜 Full PII enforcement (stop and alert, user anonymizes externally) — Target: V2
- 🔜 Consumer credit banking data support — Target: V2+
- 🔜 great_expectations integration — Target: V2
- 🔜 XLSX and database table ingestion — Target: V2+

### Edge Case Handling

- System MUST fail (not continue) when:
  - Input file is empty (headers only, no rows)
  - Critical columns are missing that impact key metrics or joins
  - Data integrity cannot be guaranteed (e.g., severe type inconsistencies that cannot be resolved)

- System MUST warn, suggest resolution, and await human approval when:
  - All values are missing in a column
  - Mixed types exist in a single column
  - Special characters or duplicate column names are detected
  - Duplicate or near-duplicate records with conflicting values are found
  - Imputation cannot be applied safely

- Details:
  - **Empty input:** Fail with a clear error message indicating no data was provided
  - **Single-row CSV:** Process with appropriate warnings about statistical limitations
  - **Malformed data:** Warn the user, suggest resolution, await approval before proceeding
  - **Missing fields:** Warn the user, highlight missing columns and potential impact, await approval
  - **Duplicates:** Warn the user, suggest resolution or flag conflicts, await approval
  - **All-missing column:** Suggest drop or imputation strategy with justification, await approval

## 7. Project Gates

| Gate | Milestone |
|------|-----------|
| G1 | Constitution ratified |
| G2 | Module A spec complete |
| G3 | Module B spec complete |
| G4 | Modules implemented and tested |
| G5 | 3 CSVs processed successfully |
| G6 (V2) | Claude Code Agent Skills integration |

---

**Governed by:** [constitution.md](./constitution.md) v1.0.0 (or v2.0.0 if Python tools version is adopted)
