# AI-Assisted Data Prep Pipeline — Project Overview

**Version**: 2.0 | **Date**: 2026-04-02 | **Status**: Under Review

---

## 1. Project Overview

- **Project Name:** AI-Assisted Data Prep Pipeline

- **Team:**

| Role | Person | Ownership |
|------|--------|-----------|
| PM | Margarida Sacouto | Constitution, project overview, coordination |
| Skill A Owner | Xiao Pan | Data Cleaning (missing values, duplicates, type consistency, outliers, column names) |
| Skill B Owner | Valerie Bien-Aime | Feature Engineering (feature generation, transformation documentation) |

- **Primary Users:**

| User Group | Skill | Technical Level |
|------------|-------|-----------------|
| Non-technical business stakeholders | Skill A (primary) | Level B — understands data concepts (e.g., "null," "duplicate"), cannot code |
| Data scientists | Skill B (primary), Skill A (secondary) | Technical — comfortable with code and statistical concepts |
| Data analysts | Skill A (secondary), Skill B (secondary) | Intermediate — works with data tools but may not code extensively |

- **Problem Statement:** Data scientists, data analysts, and non-technical business stakeholders spend significant time preparing large, messy datasets for analysis and modeling. Common repetitive tasks include format transformations (such as floats and dates), identifying and removing duplicates or near-duplicates, handling missing values through strategies such as dropping or imputing records, and extracting features. All of these tasks require careful documentation to maintain auditability and trust — yet documentation is often incomplete or inconsistent.

- **Goal:** Enable teams to produce consistent, auditable, and decision-ready datasets with reduced manual effort and controlled risk. The pipeline must document every transformation decision in plain language with justification. All LLM-suggested actions must pass through an internal validation loop (LLM personas challenging assumptions) before execution.

- **AI as Overconfident Intern:** The LLM (Claude 4.5 Sonnet) is treated as a capable but unreliable assistant. It may suggest plausible-sounding but incorrect transformation strategies. All LLM-generated suggestions must pass through an internal validation loop where different LLM personas challenge the initial suggestion, resulting in a robust final decision with a confidence score. The Verification Ritual (Read → Run → Test → Commit) applies to every transformation.

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

- **When:** The user uploads the CSV to Claude.ai and requests the full preprocessing pipeline (Skill A → Skill B)

- **Then:** Claude 4.5 Sonnet reads the full dataset via Python tools, analyzes it, identifies issues, and suggests cleaning and feature engineering transformations with justification. LLM personas internally challenge the suggestions and arrive at a robust final decision with a confidence score. Claude executes the approved transformations and returns a cleaned, feature-engineered CSV along with a plain-language transformation report (markdown) following the mandatory justification template (What was done? Why? What is the impact?). The final report includes the LLM's confidence score in each decision.

- **Test:** Upload a sample raw CSV to Claude.ai, run the pipeline, and verify that (1) data is cleaned and transformed correctly, (2) every transformation went through the internal LLM persona validation loop, (3) the final report includes confidence scores for each decision, and (4) a complete transformation report is generated as a downloadable markdown file following the 3-part justification template

### Scenario 2: Handle Conflicting Duplicates

- **Priority:** P2

- **Given:** A user has a dataset containing duplicate or near-duplicate records with conflicting values

- **When:** The user uploads the CSV to Claude.ai and runs the preprocessing pipeline

- **Then:** Claude 4.5 Sonnet detects the conflicting duplicates, presents the suggested handling logic with justification (validated through the LLM persona loop), and documents the actions taken with confidence scores

- **Test:** Upload a dataset containing duplicate or near-duplicate records with conflicting fields, run the pipeline, and verify that conflicts are either resolved according to the validated approach or clearly flagged, with documentation included in the output

### Edge Cases

The pipeline must handle the following edge cases robustly (V1 requirement):

- Empty CSV (headers only, no rows) — fail with clear error message
- Single-row CSV — process with appropriate warnings about statistical limitations
- All values missing in a column — detect, suggest handling strategy, validate through persona loop
- Mixed types in a single column (e.g., "123", "abc", "45.6") — detect, suggest type resolution, validate through persona loop
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

**Verification Ritual (NON-NEGOTIABLE):**
- System MUST implement the Verification Ritual for every transformation:
  1. **Read:** Generate LLM personas to review the initial suggested transformation and challenge assumptions. Decide on the best approach.
  2. **Run:** Execute the approved transformation via Python tools.
  3. **Test:** Have an LLM Data Analyst persona review transformations and compare before/after.
  4. **Commit:** Accept only verified, Data Analyst LLM persona-approved output.
- System MUST assign a confidence score to each transformation decision.
- System MUST present the final decision to the human user in the report (MVP). In V2, users can inspect the full discussion between LLM personas.
- On rejection by LLM personas, the system MUST present the next best alternative with justification.
- System MUST clearly distinguish between LLM-recommended decisions and user-directed transformations.

**Approval Model:**
- The LLM presents transformation suggestions with justification.
- LLM personas approve, reject, or ask for more detail in natural language.
- On rejection, the LLM presents the next best alternative with justification.
- Final report for human includes the final decision (MVP).
- In V2, user can inspect the discussion between LLM personas for reasoning details.

**Data Cleaning (Skill A):**
- System MUST detect and assess missing values in the input dataset.
- System MUST suggest imputation strategies to handle missing values, with justification.
- System MUST detect duplicate and near-duplicate records.
- System MUST handle conflicting duplicates according to validated rules or flag them for review.
- System MUST detect and suggest resolution for type inconsistencies.
- System MUST detect and suggest handling for outliers.
- System MUST detect and suggest standardization for messy column names (special characters, duplicates).

**Feature Engineering (Skill B):**
- System MUST suggest relevant features with justification.
- System MUST apply feature engineering and format transformations (including data type conversions such as floats and dates) only after validation through the LLM persona loop.

**Skill Handoff Contract:**
- Skill A MUST produce a standardized output format that Skill B expects.
- If Skill B detects issues with Skill A's output, Skill B MUST stop and flag the issue for human review.

**Mistake Logging:**
- Each skill MUST maintain its own mistake log.
- The PM aggregates logs into a summary report and uses recurring patterns to trigger Constitution updates.

**Documentation & Auditability:**
- System MUST generate documentation following the mandatory 3-part justification template for every transformation (MVP):
  1. What was done?
  2. Why?
  3. What is the impact?
- In V2, the template expands to 4 parts, adding: What alternatives were considered (and why were they rejected)?
- System MUST produce a summary of applied preprocessing changes with before/after comparison context.
- System MUST log all transformations applied to the dataset in a structured format.
- System MUST generate a plain-language data quality report explaining issues found, actions taken, and rationale, including:
  - Key metrics before vs. after preprocessing (e.g., row counts, aggregates)
  - Number of records affected by each transformation
- System MUST assign a unique version or run ID to each pipeline execution.
- System MUST allow users to reproduce previous outputs using the same inputs and configuration.
- System MUST flag transformations that may significantly alter business-critical metrics.
- System MUST include a confidence score for each transformation decision.

**Plain-Language Compliance:**
- All documentation MUST be written in plain language understandable to non-developer stakeholders.
- Basic statistical terms (mean, median, mode, outlier) are permitted without explanation.
- Method-specific terms (z-score, IQR, one-hot encoding) MUST be explained on first use.
- All acronyms MUST be defined on first use. No company-specific terminology without explanation.
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
- **LLM Configuration Intent:** Low temperature / high consistency for maximum reproducibility (to be enforced in V2 where temperature control is available).
- **Language:** Python (version as provided by Claude.ai's Python tools environment)
- **Dependency Philosophy:** Vanilla Python first. Libraries introduced only for tasks that are error-prone or impractical to implement from scratch.
- **MVP Dependencies (pre-installed in Claude.ai):** pandas, numpy, scikit-learn, vanilla Python standard library
- **V2 Dependencies (Claude Code — can pip install):** All MVP dependencies, plus: pandera, hypothesis, pytest
- **Post-MVP (V2):** great_expectations
- **Prohibited:** No frameworks or libraries outside the approved list without PM + Skill Owner approval and a compatibility test.
- **Dependency Management (MVP):** Limited to pre-installed libraries in Claude.ai. No pip install capability.
- **Dependency Management (V2):** Version ranges in `requirements.txt`. New library adoption requires PM + relevant Skill Owner approval and compatibility testing.
- **Testing (MVP):** LLM Data Analyst persona reviews transformations and compares before/after. Manual verification by user via the transformation report.
- **Testing (V2):** Automated — pytest + pandera (schema validation) + hypothesis (property-based testing). Hybrid approach: pre-defined templates for common cases, dynamically generated for edge cases.
- **Data Format (MVP):** Single tabular CSV file only. XLSX, database tables, and multi-file joins are out of scope.
- **Output Format:** CSV (cleaned/engineered data) + Markdown (transformation reports)
- **Security:**
  - MVP: Data is uploaded to Claude.ai and processed through Anthropic's API. This is accepted for non-sensitive, open-source data only. The security guardrail is relaxed for the MVP.
  - V2: Data processed through Anthropic's API via Claude Code. PII must be anonymized locally before any LLM interaction.
  - Never hardcode secrets. V2: Store in local `.env`, include in `.gitignore`.
  - If a secret is accidentally committed, it must be rotated immediately. Removal from the repository alone is not sufficient.
  - Logs must never contain raw data values. All identifiers must be masked or hashed in exported logs.
  - System MUST ensure auditability of all transformations applied to the data.
- **PII Handling (V1):** Basic warning only (e.g., "Column X may contain PII — proceed with caution"). Hybrid detection: LLM flags potential PII during analysis, human confirms. MVP uses open-source, non-sensitive datasets only.
- **PII Handling (Post-MVP):** Pipeline stops and alerts user. Cannot proceed until PII is handled externally.

### MVP Workflow

1. User uploads a raw CSV to Claude.ai
2. Claude 4.5 Sonnet reads/analyzes the full dataset via Python tools
3. Claude summarizes the issues and suggests transformations with justification
4. LLM personas analyze the suggestions and challenge assumptions
5. On rejection, Claude presents the next best alternative with justification
6. Claude executes approved transformations via Python tools
7. Claude generates a transformation report (markdown) following the 3-part justification template
8. User downloads the cleaned/engineered CSV and the transformation report

### V2 Migration Path

To minimize rework when transitioning from MVP (Claude.ai) to V2 (Claude Code):

1. **Skill boundaries = Module boundaries:** Skill A and Skill B are designed with the same input/output contracts that future Agent Skills will use.
2. **Standardized handoff format:** The intermediate format between Skill A and Skill B is identical to the future Skill A → Skill B handoff contract.
3. **Report templates:** The same markdown justification template is used in MVP reports and future Claude Code inline reports.
4. **Test suite portability:** Manual verification steps in MVP are documented so they can be converted to automated tests (Pandera, Hypothesis) in V2.
5. **SKILL.md preparation:** Each skill's purpose, inputs, outputs, and constraints are documented in a format that can be directly converted to `SKILL.md` files for Claude Code.

## 5. Success Criteria

- [ ] **Functional:**
  - All P1 scenarios work end-to-end in Claude.ai
  - Pipeline runs without errors on 3 test datasets:
    1. NYC TLC Trip Records (large, messy, time/location fields)
    2. Kaggle — Instacart / Dunnhumby "The Complete Journey" (retail transactions)
    3. UCI dataset (mixed numeric/categorical data)
  - Outputs include cleaned data, engineered features, and transformation report (markdown)
  - All edge cases handled (empty CSV, single-row, all-missing column, mixed types, special characters, duplicate column names)

- [ ] **Verification Ritual:**
  - Every LLM-suggested transformation goes through the internal persona validation loop
  - Each transformation decision includes a confidence score
  - Rejected suggestions (by LLM personas) trigger next best alternative
  - Final report presents validated decisions to the human user

- [ ] **Documentation Quality:**
  - Every transformation report follows the mandatory 3-part justification template (MVP) / 4-part template (V2)
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

- System MUST warn, suggest resolution, and validate through the persona loop when:
  - All values are missing in a column
  - Mixed types exist in a single column
  - Special characters or duplicate column names are detected
  - Duplicate or near-duplicate records with conflicting values are found
  - Imputation cannot be applied safely

- Details:
  - **Empty input:** Fail with a clear error message indicating no data was provided
  - **Single-row CSV:** Process with appropriate warnings about statistical limitations
  - **Malformed data:** Warn the user, suggest resolution, validate through persona loop before proceeding
  - **Missing fields:** Warn the user, highlight missing columns and potential impact, validate approach through persona loop
  - **Duplicates:** Warn the user, suggest resolution or flag conflicts, validate through persona loop
  - **All-missing column:** Suggest drop or imputation strategy with justification, validate through persona loop

## 7. Project Gates

| Gate | Milestone |
|------|-----------|
| G1 | Constitution ratified |
| G2 | Skill A spec complete |
| G3 | Skill B spec complete |
| G4 | Skills implemented and tested |
| G5 | 3 CSVs processed successfully |
| G6 (V2) | Claude Code Agent Skills integration |

---

**Governed by:** [constitution.md](./constitution.md) v1.1.0
