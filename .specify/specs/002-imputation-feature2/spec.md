# Skill A — Data Cleaning: Feature Specifications

**Skill Owner**: Xiao Pan
**Created**: 2026-04-02
**Status**: Draft
**Governed by**: [constitution.md](./constitution.md) v1.1.0

---

# Feature Specification: Data Transformation with Persona Validation

**Feature Branch**: `002-data-transformation`
**Created**: 2026-04-02
**Status**: Draft
**Input**: Natural language report produced by Feature 1 (Data Profiling)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — LLM Suggests and Validates Cleaning Transformations (Priority: P1)

The LLM reads the natural language report from Feature 1 and proposes a set of data cleaning transformations to address the issues identified during profiling — such as handling missing values, resolving type inconsistencies, removing or reconciling duplicates, treating outliers, and standardizing column names. Each suggestion includes a justification. LLM personas then challenge the suggestions internally: different personas review the proposed approach, question assumptions, and either approve, reject, or request more detail. On rejection, the LLM presents the next best alternative with justification. The process produces a final, robust set of transformation decisions, each with a confidence score.

**Why this priority**: This is the core intelligence of Skill A — where data cleaning decisions are made and validated. Without this, the pipeline has no way to move from "understanding the data" to "cleaning the data."

**Independent Test**: Provide the natural language report from a CSV with known issues (e.g., 15% missing values in a numeric column, 200 duplicate rows, a column with mixed string/numeric types). Verify that (1) the LLM proposes specific transformations for each issue, (2) LLM personas challenge at least one assumption, (3) the final decisions include confidence scores, and (4) rejected suggestions are replaced with justified alternatives.

**Acceptance Scenarios**:

1. **Given** a natural language report identifying missing values in a numeric column, **When** the LLM proposes an imputation strategy, **Then** LLM personas review the suggestion, and the final decision includes a justification and a confidence score.
2. **Given** a natural language report identifying duplicate rows with conflicting values, **When** the LLM proposes a deduplication strategy, **Then** LLM personas challenge the approach (e.g., questioning which record to keep and why), and the final decision documents the reasoning.
3. **Given** an LLM persona rejects a proposed transformation, **When** the rejection is registered, **Then** the LLM presents the next best alternative with justification and the persona loop continues until a decision is approved.
4. **Given** a natural language report identifying mixed types in a column, **When** the LLM proposes a type resolution strategy, **Then** the final decision specifies the target type and handling for values that cannot be converted (e.g., coerce to NaN, flag for review).

---

### User Story 2 — Execute Approved Transformations (Priority: P1)

Once the persona validation loop produces a final set of approved transformation decisions, the LLM executes them via Python tools (pandas, numpy, scikit-learn). The system applies each transformation to the dataset and produces a cleaned CSV.

**Why this priority**: Execution is inseparable from the decision-making — without it, the persona validation loop produces decisions that go nowhere. Together with User Story 1, this completes the core cleaning pipeline.

**Independent Test**: Provide a raw CSV and a set of pre-approved transformation decisions. Execute the transformations and verify that (1) the output CSV reflects the expected changes, (2) no transformation is applied that was not approved, and (3) the output CSV is a valid tabular file.

**Acceptance Scenarios**:

1. **Given** a set of approved transformation decisions, **When** the system executes them, **Then** the output CSV reflects all approved changes and no unapproved changes.
2. **Given** an approved imputation strategy (e.g., fill missing numeric values with the median), **When** the transformation is applied, **Then** the affected column has no remaining missing values and the imputed values match the specified strategy.
3. **Given** an approved deduplication strategy, **When** the transformation is applied, **Then** the output CSV contains no duplicate rows according to the approved definition.
4. **Given** a transformation fails during execution (e.g., type coercion error), **When** the failure occurs, **Then** the system stops, reports the error clearly, and does not produce a partial output.

---

### User Story 3 — Generate Transformation Report with Before/After Comparison (Priority: P1)

After all transformations are executed, the system generates a transformation report (markdown) following the mandatory 3-part justification template for each transformation: (1) What was done? (2) Why? (3) What is the impact? The report includes before/after comparisons for key metrics (row counts, column counts, missing value counts, aggregates) and the confidence score for each decision. The report also includes a summary of any transformations that were rejected during the persona validation loop and why.

**Why this priority**: Documentation and auditability are core to the constitution. The transformation report is the primary artifact that enables trust, traceability, and reproducibility. Without it, the pipeline fails the plain-language commitment.

**Independent Test**: Run the full transformation pipeline on a test CSV. Verify that (1) the transformation report follows the 3-part justification template for every transformation, (2) before/after comparisons are included, (3) confidence scores are present, and (4) the report passes the plain-language compliance check.

**Acceptance Scenarios**:

1. **Given** transformations have been executed, **When** the report is generated, **Then** every transformation has an entry following the 3-part template (What was done? Why? What is the impact?) with a confidence score.
2. **Given** transformations have been executed, **When** the report is generated, **Then** it includes before/after comparisons for row count, column count, missing value counts, and at least one aggregate metric (e.g., mean, sum) for affected columns.
3. **Given** a transformation was rejected during the persona loop, **When** the report is generated, **Then** the rejected approach and the reason for rejection are documented.
4. **Given** the report is generated, **When** a non-technical stakeholder reads it, **Then** they can understand every transformation without needing technical assistance (stranger test).

---

### User Story 4 — Download Cleaned CSV and Transformation Report (Priority: P1)

The user can download the cleaned CSV and the transformation report (markdown) from Claude.ai. These are the final outputs of Skill A and the inputs expected by Skill B (Feature Engineering).

**Why this priority**: Without downloadable outputs, the pipeline delivers no tangible value to the user. The cleaned CSV is also the handoff artifact to Skill B, per the Skill Handoff Contract in the constitution.

**Independent Test**: Run the full pipeline on a test CSV and verify that both the cleaned CSV and the transformation report (markdown) are available for download.

**Acceptance Scenarios**:

1. **Given** the transformation pipeline has completed, **When** the user requests outputs, **Then** both the cleaned CSV and the transformation report (markdown) are available for download.
2. **Given** the cleaned CSV is downloaded, **When** it is opened, **Then** it is a valid tabular CSV with headers and reflects all approved transformations.

---

### User Story 5 — LLM Data Analyst Persona Verifies Output (Priority: P2)

After transformations are executed but before the output is finalized, an LLM Data Analyst persona reviews the cleaned dataset against the original. This persona compares before/after states, checks for unintended side effects (e.g., unexpected row loss, shifted distributions), and either confirms the output or flags issues for re-evaluation. This is the "Test" step of the Verification Ritual.

**Why this priority**: This is the quality gate that catches errors the transformation personas may have missed. It is part of the Verification Ritual (Read → Run → Test → Commit) defined in the constitution, but is prioritized as P2 because the core pipeline (suggest → validate → execute → report) must work first.

**Independent Test**: Provide a cleaned CSV and the original raw CSV. Have the Data Analyst persona compare them and verify that it flags at least one known intentional issue (e.g., a 40% row reduction from deduplication) as something to confirm, and catches at least one introduced error in a test scenario.

**Acceptance Scenarios**:

1. **Given** a cleaned CSV and the original raw CSV, **When** the Data Analyst persona reviews them, **Then** it confirms that the transformations match the approved decisions and flags any unexpected differences.
2. **Given** a transformation introduced an unintended side effect (e.g., removing rows that should have been kept), **When** the Data Analyst persona reviews, **Then** it flags the issue for re-evaluation before the output is finalized.

---

### User Story 6 — Maintain Skill A Mistake Log (Priority: P2)

Each execution of Skill A records any errors, rejected transformations, persona disagreements, and edge-case warnings in a structured mistake log. The PM can aggregate these logs over time to identify recurring patterns and trigger Constitution updates.

**Why this priority**: Required by the constitution (Mistake Logging), but not blocking the core transformation pipeline. Can be implemented after the core flow is stable.

**Independent Test**: Run the pipeline on a CSV that triggers at least one persona rejection and one edge-case warning. Verify that both events appear in the mistake log in a structured format.

**Acceptance Scenarios**:

1. **Given** a persona rejects a transformation during the validation loop, **When** the pipeline completes, **Then** the rejection is recorded in the mistake log with the reason and the alternative that was adopted.
2. **Given** an edge-case warning is issued (e.g., single-row CSV), **When** the pipeline completes, **Then** the warning is recorded in the mistake log.
3. **Given** the mistake log is exported, **When** it is inspected, **Then** it contains no raw data values — all identifiers are masked or hashed.

---

### Edge Cases

- What happens when the natural language report from Feature 1 identifies no issues? The system should confirm the data is clean, skip transformations, and produce a report stating no cleaning was required.
- What happens when all LLM personas disagree and no consensus is reached? The system should flag the transformation for human review rather than proceeding without a validated decision.
- What happens when imputation cannot be applied safely (e.g., a column with 95% missing values)? The system should flag it for human review and not proceed without explicit approval.
- What happens when a transformation would remove more than 50% of rows? The system should flag this as a high-impact transformation in the report and require explicit validation from the persona loop.
- What happens when the Skill A output does not meet the Skill Handoff Contract expected by Skill B? Skill B should stop and flag the issue for human review (this is Skill B's responsibility, but Skill A must produce output that meets the contract).
- What happens when a transformation causes a column to become entirely empty? The system should flag this in the transformation report and the Data Analyst persona should catch it during verification.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-101**: System MUST read the natural language report produced by Feature 1 as its input. Feature 2 cannot run without Feature 1 output.
- **FR-102**: The LLM MUST propose specific data cleaning transformations for each issue identified in the natural language report, with justification for each.
- **FR-103**: System MUST implement the Verification Ritual: Read (LLM personas challenge assumptions) → Run (execute via Python tools) → Test (Data Analyst persona reviews before/after) → Commit (accept verified output).
- **FR-104**: LLM personas MUST challenge the initial transformation suggestions. The persona loop MUST produce a final decision with a confidence score for each transformation.
- **FR-105**: On rejection by an LLM persona, the system MUST present the next best alternative with justification.
- **FR-106**: System MUST execute approved transformations using pandas, numpy, and scikit-learn via Claude.ai's Python tools.
- **FR-107**: System MUST NOT apply any transformation that was not approved through the persona validation loop.
- **FR-108**: System MUST produce a cleaned CSV as output, conforming to the Skill Handoff Contract expected by Skill B.
- **FR-109**: System MUST generate a transformation report (markdown) following the mandatory 3-part justification template for each transformation: (1) What was done? (2) Why? (3) What is the impact?
- **FR-110**: The transformation report MUST include before/after comparisons for key metrics: row count, column count, missing value counts, and at least one aggregate metric for each affected column.
- **FR-111**: The transformation report MUST include the confidence score for each transformation decision.
- **FR-112**: The transformation report MUST document rejected transformations and the reasons for rejection.
- **FR-113**: System MUST flag transformations that may significantly alter business-critical metrics (e.g., large row reductions, shifted distributions).
- **FR-114**: System MUST make both the cleaned CSV and the transformation report (markdown) available for download.
- **FR-115**: System MUST assign a unique version or run ID to each transformation execution.
- **FR-116**: System MUST allow users to reproduce previous outputs using the same inputs and configuration.
- **FR-117**: System MUST maintain a mistake log recording errors, rejected transformations, persona disagreements, and edge-case warnings in a structured format.
- **FR-118**: Mistake log MUST never contain raw data values. All identifiers MUST be masked or hashed.
- **FR-119**: All documentation MUST be written in plain language. Basic statistical terms are permitted without explanation. Method-specific terms MUST be explained on first use. All acronyms MUST be defined on first use.
- **FR-120**: System MUST run an automated jargon scan on the transformation report to flag undefined acronyms and unexplained terminology.
- **FR-121**: If the natural language report identifies no issues, the system MUST confirm the data is clean, skip transformations, and produce a report stating no cleaning was required.
- **FR-122**: If persona consensus cannot be reached, the system MUST flag the transformation for human review and not proceed without explicit approval.

### Key Entities

- **Natural Language Report**: The exploratory profiling summary produced by Feature 1. This is the sole input to Feature 2. It contains the LLM's assessment of data quality issues and their impact.
- **Transformation Decision**: A specific cleaning action proposed by the LLM, validated through the persona loop, and assigned a confidence score. Each decision maps to one or more data quality issues from the natural language report.
- **LLM Persona**: A role assumed by the LLM during the validation loop (e.g., data quality skeptic, domain expert, statistical reviewer, Data Analyst). Personas challenge assumptions and validate decisions.
- **Cleaned CSV**: The output dataset after all approved transformations have been applied. Must conform to the Skill Handoff Contract for Skill B.
- **Transformation Report**: A markdown document following the 3-part justification template for every transformation, with before/after comparisons and confidence scores.
- **Mistake Log**: A structured log of errors, rejections, and warnings. Used by the PM to identify recurring patterns and trigger Constitution updates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-101**: Every transformation decision has a documented justification following the 3-part template and a confidence score.
- **SC-102**: The persona validation loop challenges at least one assumption per profiling run — no transformation set passes through unchallenged.
- **SC-103**: The cleaned CSV reflects all approved transformations and no unapproved transformations.
- **SC-104**: Before/after comparisons are present in the transformation report for every transformation, covering row count, column count, missing values, and at least one aggregate metric per affected column.
- **SC-105**: The transformation report passes the plain-language compliance check: no undefined acronyms, no unexplained method-specific terms, every metric includes context.
- **SC-106**: A non-technical stakeholder (Level B user) can read the transformation report and understand every decision without technical assistance (stranger test).
- **SC-107**: The cleaned CSV conforms to the Skill Handoff Contract and is accepted by Skill B without errors.
- **SC-108**: The pipeline handles all required edge cases: no-issue datasets, persona disagreements, unsafe imputations, high-impact row reductions, and post-transformation empty columns.
- **SC-109**: Outputs for the same input CSV and configuration are deterministic and reproducible.
- **SC-110**: The mistake log captures all persona rejections, edge-case warnings, and execution errors in a structured format with no raw data values.

---

**Governed by**: [constitution.md](./constitution.md) v1.1.0