# AI-Assisted Data Prep Pipeline — Project Overview

**Version**: 1.0 | **Date**: 2026-03-30 | **Status**: Under Review

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

- **Goal:** Enable teams to produce consistent, auditable, and decision-ready datasets with reduced manual effort and controlled risk. The pipeline must document every transformation decision in plain language with justification, and all LLM-suggested actions must be approved by a human before execution.

- **Hallucination Tolerance:** **ZERO — Catastrophic.** The LLM (Claude 4.5 Sonnet) may suggest plausible but incorrect transformation strategies. All suggestions must be reviewed and approved by a human before execution. The Verification Ritual (Read → Run → Test → Commit) applies to every transformation.

- **LLM:** Claude 4.5 Sonnet (Anthropic). The LLM is a core runtime component — it analyzes data, recommends transformation approaches, interacts with users in natural language, and generates documentation.

- **Platform Decision:**

| Phase | Platform | LLM | Python Execution |
|-------|----------|-----|-----------------|
| **MVP** | Claude.ai | Claude 4.5 Sonnet | Claude.ai's built-in Python tools (sandboxed) |
| **V2** | Claude Code | Claude 4.5 Sonnet | Full local Python environment + Agent Skills |

## 2. User Scenarios & Testing

### Scenario 1: End-to-End Data Preparation Pipeline

- **Priority:** P1

- **Given:** A user has a raw, messy CSV dataset

- **When:** The user uploads the CSV to Claude.ai and requests the full preprocessing pipeline (Module A → Module B)

- **Then:** Claude 4.5 Sonnet reads the full dataset via Python tools, analyzes it, identifies issues, and suggests cleaning and feature engineering transformations with justification — presenting each action for human approval in natural language before execution — and returns a cleaned, feature-engineered CSV along with a plain-language transformation report (markdown) following the mandatory justification template (What was done? Why? Alternatives considered and why rejected? Impact?)

- **Test:** Upload a sample raw CSV to Claude.ai, run the pipeline, and verify that (1) data is cleaned and transformed correctly, (2) every transformation was approved by the user before execution, and (3) a complete transformation report is generated as a downloadable markdown file following the justification template

### Scenario 2: Run Data Cleaning Only (Module A)

- **Priority:** P2

- **Given:** A user has a raw CSV dataset with missing values, duplicates, type inconsistencies, and/or messy column names

- **When:** The user uploads the CSV to Claude.ai and requests only Module A for data cleaning

- **Then:** Claude 4.5 Sonnet detects issues, suggests cleaning actions with justification in natural language, waits for human approval, executes approved actions via Python tools, and returns cleaned data along with a markdown report explaining the steps taken and the rationale behind them

- **Test:** Upload a CSV with missing values, duplicates, and mixed types. Run only Module A. Verify that (1) the output dataset reflects the expected cleaning logic, (2) every action was presented for approval before execution, (3) rejected actions triggered the next best alternative, and (4) the documentation follows the mandatory justification template

### Scenario 3: Handle Conflicting Duplicates

- **Priority:** P2

- **Given:** A user has a dataset containing duplicate or near-duplicate records with conflicting values

- **When:** The user uploads the CSV to Claude.ai and runs the preprocessing pipeline

- **Then:** Claude 4.5 Sonnet detects the conflicting duplicates, presents the suggested handling logic for human approval in natural language or flags them for review, and documents the actions taken with justification

- **Test:** Upload a dataset containing duplicate or near-duplicate records with conflicting fields, run the pipeline, and verify that conflicts are either resolved according to approved rules or clearly flagged, with documentation included in the output

### Scenario 4: Run Feature Engineering Only (Module B)

- **Priority:** P2

- **Given:** A user has a cleaned dataset (output of Module A or pre-cleaned data)

- **When:** The user uploads the CSV to Claude.ai and requests only Module B for feature engineering

- **Then:** Claude 4.5 Sonnet suggests relevant features with justification in natural language, waits for human approval, generates approved features via Python tools, and produces a markdown report with before/after comparisons and benchmark references

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
- System MUST accept raw CSV files uploaded by the user to Claude.ai (MVP scope — single file only).
- System MUST reject empty input files with a clear error message.
- System MUST require input data to have a valid tabular structure with headers/column names.

**LLM Runtime (Core):**
- System MUST use Claude 4.5 Sonnet as the core runtime engine for data analysis, transformation recommendations, user interaction, and documentation generation.
- The LLM MUST have access to the full dataset via Claude.ai's Python tools.
- The LLM MUST analyze the complete data before making recommendations.

**Human-in-the-Loop Approval (NON-NEGOTIABLE):**
- System MUST present all LLM-suggested transformations for human approval before execution.
- System MUST interact with users in natural language via Claude.ai's conversational interface.
- System MUST present the next best alternative when a suggestion is rejected.
- System MUST clearly distinguish between LLM-recommended decisions and user-directed transformations.

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
- System MUST generate documentation following the mandatory justification template for every transformation:
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

### Could Have (P3)

- System COULD provide automated feature importance suggestions to support downstream modeling.
- System COULD include anomaly detection to identify unusual or outlier patterns in the dataset.

## 4. Technical Constraints

- **Platform (MVP):** Claude.ai with built-in Python tools. Users upload CSVs and interact with the LLM in natural language.
- **Platform (V2):** Claude Code with Claude Agent Skills, auto-discovered from `.claude/skills/` directory.
- **LLM:** Claude 4.5 Sonnet (Anthropic) — core runtime component in both MVP and V2.
- **Language:** Python (version as provided by Claude.ai's Python tools environment)
- **Dependency Philosophy:** Vanilla Python first. Libraries introduced only for tasks that are error-prone or impractical to implement from scratch.
- **MVP Dependencies (pre-installed in Claude.ai):** pandas, numpy, vanilla Python standard library
- **V2 Dependencies (Claude Code — can pip install):** All MVP dependencies, plus: pandera, hypothesis, pytest
- **Provisional (V2):** scikit-learn (to be confirmed for Module B)
- **Post-MVP (V2):** great_expectations
- **Dependency Management (MVP):** Limited to pre-installed libraries in Claude.ai. No pip install capability.
- **Dependency Management (V2):** Version ranges in `requirements.txt`. New library adoption requires PM + relevant Module Owner approval and compatibility testing.
- **Testing (MVP):** Manual verification — user reviews before/after comparisons generated by the LLM.
- **Testing (V2):** Automated — pytest + pandera (schema validation) + hypothesis (property-based testing). Hybrid approach: pre-defined templates for common cases, dynamically generated for edge cases.
- **Data Format (MVP):** Single tabular CSV file only. XLSX, database tables, and multi-file joins are out of scope.
- **Output Format:** CSV (cleaned/engineered data) + Markdown (transformation reports)
- **Security:**
  - MVP: Data is uploaded to Claude.ai and processed through Anthropic's API. This is accepted for non-sensitive, open-source data only. The security guardrail is relaxed for the MVP.
  - V2: Data processed through Anthropic's API via Claude Code. PII must be anonymized locally before any LLM interaction.
  - Never hardcode secrets. V2: Store in local `.env`, include in `.gitignore`.
  - Logs must never contain raw data values. All identifiers must be masked or hashed in exported logs.
  - System MUST ensure auditability of all transformations applied to the data.
- **PII Handling (V1):** Basic warning only (e.g., "Column X may contain PII — proceed with caution"). Hybrid detection: LLM flags potential PII during analysis, human confirms. MVP uses open-source, non-sensitive datasets only.
- **PII Handling (Post-MVP):** Pipeline stops and alerts user. Cannot proceed until PII is handled externally.

### MVP Workflow

1. User uploads a raw CSV to Claude.ai
2. Claude 4.5 Sonnet reads the full dataset via Python tools
3. Claude analyzes the data, identifies issues, and suggests transformations with justification
4. User approves or rejects each suggestion in natural language
5. On rejection, Claude presents the next best alternative with justification
6. Claude executes approved transformations via Python tools
7. Claude generates a transformation report (markdown) following the 4-part justification template
8. User downloads the cleaned/engineered CSV and the transformation report

### V2 Migration Path

To minimize rework when transitioning from MVP (Claude.ai) to V2 (Claude Code):

1. **Module boundaries = Skill boundaries:** Module A and Module B are designed with the same input/output contracts that future Agent Skills will use.
2. **Standardized handoff format:** The intermediate format between Module A and Module B is identical to the future Skill A → Skill B handoff contract.
3. **Report templates:** The same markdown justification template is used in MVP reports and future Claude Code inline reports.
4. **Test suite portability:** Manual verification steps in MVP are documented so they can be converted to automated tests (Pandera, Hypothesis) in V2.
5. **SKILL.md preparation:** Each module's purpose, inputs, outputs, and constraints are documented in a format that can be directly converted to `SKILL.md` files for Claude Code.

## 5. Success Criteria

- [ ] **Functional:**
  - All P1 scenarios work end-to-end in Claude.ai
  - Pipeline runs without errors on 3 test datasets:
    1. NYC TLC Trip Records (large, messy, time/location fields)
    2. Kaggle — Instacart / Dunnhumby "The Complete Journey" (retail transactions)
    3. UCI dataset (mixed numeric/categorical data)
  - Outputs include cleaned data, engineered features, and transformation report (markdown)
  - All edge cases handled (empty CSV, single-row, all-missing column, mixed types, special characters, duplicate column names)

- [ ] **Human-in-the-Loop:**
  - Every LLM-suggested transformation is presented for approval before execution
  - Rejected suggestions trigger next best alternative
  - No transformation executes without explicit human approval

- [ ] **Documentation Quality:**
  - Every transformation report follows the mandatory 4-part justification template
  - All reports pass the automated jargon scan
  - Every metric includes comparison context
  - A new team member can understand all reports without asking questions (stranger test)

- [ ] **Usability:**
  - Outputs for the same input dataset and configuration MUST be deterministic and reproducible
  - System MUST highlight any transformation that could materially impact key metrics (e.g., revenue, counts, averages)
  - Users MUST be able to trace every output field back to its original source and transformation steps

- [ ] **Business:**
  - Reduce manual data preparation time by at least 30%
  - Reduce data-related rework or corrections in downstream analysis
  - Increase stakeholder trust in data outputs (measured via user feedback or adoption)

## 6. Out of Scope

### Excluded Features

- ❌ Claude Code / Agent Skills — Reason: Deferred to V2
- ❌ Web UI / dashboard — Reason: Interaction is through Claude.ai's conversational interface
- ❌ Building full machine learning models / automated model training — Reason: Pipeline ends at clean, feature-engineered data plus documentation
- ❌ Real-time or streaming pipelines — Reason: Scope is limited to batch preprocessing workflows
- ❌ Multi-file joins / merging multiple CSVs — Reason: Single CSV in, single output out
- ❌ XLSX or database table ingestion — Reason: MVP is CSV only
- ❌ Data storage or data warehouse capabilities — Reason: System operates on provided datasets and does not manage storage infrastructure
- ❌ Integrations with external systems — Reason: Data processed via Anthropic's API only
- ❌ Deployment or orchestration tools (e.g., Airflow) — Reason: Pipeline execution is conversational in Claude.ai
- ❌ Cloud deployment — Reason: No independent cloud infrastructure
- ❌ Consumer credit banking data — Reason: Deferred to post-MVP
- ❌ Full PII enforcement (stop and alert) — Reason: V1 has basic warning only; full enforcement deferred to post-MVP
- ❌ Automated testing (pandera, hypothesis, pytest) — Reason: Not available in Claude.ai; deferred to V2

The system is responsible for data preprocessing and transformation transparency. The user remains responsible for validating final outputs before use in business-critical decisions.

### Deferred to Future Versions

- 🔜 Claude Code with Claude Agent Skills (richer interaction, local Python, Agent Skills) — Target: V2
- 🔜 Automated testing with pandera, hypothesis, pytest — Target: V2
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

**Governed by:** [constitution.md](./constitution.md) v1.0.0
