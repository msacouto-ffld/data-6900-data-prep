# Skill B — Feature Engineering: Feature Specification

**Skill Owner**: Valerie Bien-Aime
**Created**: 2026-04-02
**Status**: Draft
**Governed by**: [constitution.md](./constitution.md) v1.1.0

---

# Feature Specification: Feature Engineering with Persona Validation

**Feature Branch**: `003-feature-engineering`
**Created**: 2026-04-02
**Status**: Draft
**Input**: Cleaned CSV produced by Skill A (Data Cleaning)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Validate Skill A Output Against Handoff Contract (Priority: P1)

Before any feature engineering begins, Skill B validates the cleaned CSV received from Skill A against the Skill Handoff Contract. The system checks that the input meets the expected format, structure, and quality standards. If issues are detected, Skill B stops immediately and flags the problem for human review — it does not attempt to fix Skill A's output.

**Why this priority**: The constitution mandates that Skill B stops and flags issues with Skill A's output rather than proceeding on bad data. This is the first thing that must happen. If the input is invalid, nothing else in Skill B should run.

**Independent Test**: Provide a CSV that violates the handoff contract (e.g., contains remaining duplicates, has missing column headers, or includes unflagged mixed types). Verify that Skill B stops, identifies the specific contract violation, and flags it for human review without proceeding.

**Acceptance Scenarios**:

1. **Given** a cleaned CSV from Skill A that conforms to the Skill Handoff Contract, **When** Skill B validates the input, **Then** validation passes and the feature engineering pipeline proceeds.
2. **Given** a cleaned CSV that violates the Skill Handoff Contract (e.g., remaining missing values in columns that should have been cleaned), **When** Skill B validates the input, **Then** the system stops, identifies the specific violation, and flags it for human review. No feature engineering is performed.
3. **Given** a CSV that was not produced by Skill A (e.g., uploaded directly by a user), **When** Skill B attempts to validate it, **Then** the system rejects the input with a clear message explaining that Skill B requires Skill A's output.

---

### User Story 2 — LLM Suggests and Validates Feature Engineering Transformations (Priority: P1)

The LLM analyzes the cleaned dataset and proposes feature engineering transformations — new derived columns (ratios, aggregations), encoding of categorical variables (one-hot, label encoding), date/time feature extraction (day of week, hour, month), and normalization or scaling of numeric columns. Each suggestion includes a justification and a benchmark comparison explaining why the proposed feature is expected to add analytical value. LLM personas then challenge the suggestions internally: different personas review the proposed features, question assumptions about their relevance and correctness, and either approve, reject, or request more detail. On rejection, the LLM presents the next best alternative with justification. The process produces a final, robust set of feature engineering decisions, each with a confidence score.

**Why this priority**: This is the core intelligence of Skill B — where feature engineering decisions are made and validated. Without this, the skill has no way to determine what features to create.

**Independent Test**: Provide a cleaned CSV with date columns, categorical columns, and numeric columns. Verify that (1) the LLM proposes specific feature engineering transformations for each relevant column type, (2) each suggestion includes a benchmark comparison, (3) LLM personas challenge at least one assumption, (4) the final decisions include confidence scores, and (5) rejected suggestions are replaced with justified alternatives.

**Acceptance Scenarios**:

1. **Given** a cleaned CSV containing date/time columns, **When** the LLM proposes feature extraction, **Then** it suggests relevant time-based features (e.g., day of week, hour, month) with justification and a benchmark comparison explaining the expected analytical value.
2. **Given** a cleaned CSV containing categorical columns, **When** the LLM proposes encoding strategies, **Then** it suggests appropriate encoding methods (e.g., one-hot for low-cardinality, label encoding for ordinal categories) with justification for the chosen method over alternatives.
3. **Given** a cleaned CSV containing numeric columns, **When** the LLM proposes normalization or scaling, **Then** it specifies the method (e.g., min-max scaling, z-score standardization) with justification based on the data distribution and intended downstream use.
4. **Given** an LLM persona rejects a proposed feature (e.g., questioning the relevance of a derived ratio), **When** the rejection is registered, **Then** the LLM presents the next best alternative with justification and the persona loop continues until a decision is approved.
5. **Given** the LLM identifies an opportunity for a derived column (e.g., a ratio between two numeric columns), **When** it proposes the feature, **Then** the suggestion includes a justification of why the derived feature adds value beyond the original columns and a benchmark comparison.

---

### User Story 3 — Execute Approved Feature Engineering Transformations (Priority: P1)

Once the persona validation loop produces a final set of approved feature engineering decisions, the LLM executes them via Python tools (pandas, numpy, scikit-learn). The system applies each transformation to the dataset and produces a feature-engineered CSV.

**Why this priority**: Execution is inseparable from decision-making. Together with User Story 2, this completes the core feature engineering pipeline.

**Independent Test**: Provide a cleaned CSV and a set of pre-approved feature engineering decisions. Execute the transformations and verify that (1) the output CSV contains all new features, (2) original cleaned columns are preserved, (3) no unapproved transformation is applied, and (4) the output CSV is a valid tabular file.

**Acceptance Scenarios**:

1. **Given** a set of approved feature engineering decisions, **When** the system executes them, **Then** the output CSV contains all new engineered features and all original cleaned columns are preserved.
2. **Given** an approved one-hot encoding for a categorical column with 5 unique values, **When** the transformation is applied, **Then** the output CSV contains 5 new binary columns and the original categorical column is handled according to the approved decision (kept or dropped).
3. **Given** an approved date/time extraction (e.g., extract day of week from a timestamp column), **When** the transformation is applied, **Then** the output CSV contains a new column with correct day-of-week values for every row.
4. **Given** an approved normalization (e.g., min-max scaling on a numeric column), **When** the transformation is applied, **Then** the new column values fall within the expected range (e.g., 0 to 1) and the original column is handled according to the approved decision.
5. **Given** a transformation fails during execution (e.g., encoding error on unexpected category values), **When** the failure occurs, **Then** the system stops, reports the error clearly, and does not produce a partial output.

---

### User Story 4 — Generate Transformation Report with Benchmark Comparisons (Priority: P1)

After all feature engineering transformations are executed, the system generates a transformation report (markdown) following the mandatory 3-part justification template for each transformation: (1) What was done? (2) Why? (3) What is the impact? Each entry also includes a benchmark comparison for the new feature — explaining its expected analytical value relative to the original columns or to standard practice. The report includes before/after comparisons for key metrics (column count, row count, feature distributions) and the confidence score for each decision.

**Why this priority**: The constitution requires that new features include benchmark comparisons, and documentation is a core deliverable. Without the report, the pipeline fails the plain-language commitment and auditability requirements.

**Independent Test**: Run the full feature engineering pipeline on a test CSV. Verify that (1) every transformation follows the 3-part template, (2) every new feature has a benchmark comparison, (3) before/after comparisons are included, (4) confidence scores are present, and (5) the report passes the plain-language compliance check.

**Acceptance Scenarios**:

1. **Given** feature engineering transformations have been executed, **When** the report is generated, **Then** every transformation has an entry following the 3-part template (What was done? Why? What is the impact?) with a confidence score and a benchmark comparison.
2. **Given** the report is generated, **When** it describes a new derived column, **Then** the benchmark comparison explains why this feature is expected to add analytical value (e.g., "Revenue per unit is a standard retail metric that normalizes for order size, enabling fairer comparison across transactions").
3. **Given** the report is generated, **When** it includes before/after comparisons, **Then** the comparisons cover column count, row count (which should be unchanged), and distribution summaries for new features.
4. **Given** a transformation was rejected during the persona loop, **When** the report is generated, **Then** the rejected approach and the reason for rejection are documented.
5. **Given** the report is generated, **When** a non-technical stakeholder reads it, **Then** they can understand every transformation without needing technical assistance (stranger test).

---

### User Story 5 — Generate Data Dictionary for Engineered Features (Priority: P1)

After feature engineering is complete, the LLM auto-generates a data dictionary documenting all engineered features. For each new feature, the dictionary includes the feature name, a plain-language description of what it represents, the source column(s) it was derived from, the transformation method used, the data type, and any relevant notes (e.g., value ranges, encoding mappings).

**Why this priority**: The data dictionary is a primary output of Skill B and a key deliverable for data scientists who will use the engineered features downstream. Without it, users cannot reliably interpret or trust the new features.

**Independent Test**: Run the full pipeline on a test CSV that produces at least 5 new features. Verify that the data dictionary contains an entry for each engineered feature with all required fields, and that descriptions are accurate and in plain language.

**Acceptance Scenarios**:

1. **Given** feature engineering has produced new columns, **When** the data dictionary is generated, **Then** every engineered feature has an entry containing: feature name, plain-language description, source column(s), transformation method, and data type.
2. **Given** a one-hot encoded feature, **When** the data dictionary describes it, **Then** the entry explains the encoding mapping (e.g., "Binary column indicating whether the original category was 'Premium'. 1 = Premium, 0 = not Premium").
3. **Given** a derived ratio column, **When** the data dictionary describes it, **Then** the entry identifies both source columns and explains the formula (e.g., "Revenue divided by Units Sold, representing revenue per unit").
4. **Given** the data dictionary is generated, **When** a data scientist reads it, **Then** they can understand every engineered feature without referring back to the transformation report or the original dataset.

---

### User Story 6 — Download Feature-Engineered CSV, Transformation Report, and Data Dictionary (Priority: P1)

The user can download the feature-engineered CSV, the transformation report (markdown), and the data dictionary (markdown) from Claude.ai. These are the final outputs of Skill B and the end of the pipeline.

**Why this priority**: Without downloadable outputs, the pipeline delivers no tangible value. These are the deliverables the constitution defines as the pipeline's end product.

**Independent Test**: Run the full pipeline and verify that all three files are available for download and are valid.

**Acceptance Scenarios**:

1. **Given** the feature engineering pipeline has completed, **When** the user requests outputs, **Then** the feature-engineered CSV, transformation report (markdown), and data dictionary (markdown) are all available for download.
2. **Given** the feature-engineered CSV is downloaded, **When** it is opened, **Then** it is a valid tabular CSV with headers, containing both original cleaned columns and all new engineered features.

---

### User Story 7 — LLM Data Analyst Persona Verifies Output (Priority: P2)

After feature engineering transformations are executed but before outputs are finalized, an LLM Data Analyst persona reviews the feature-engineered dataset against the cleaned input. This persona checks for unintended side effects (e.g., unexpected NaN values in new columns, incorrect encoding mappings, normalization errors), verifies that original columns are intact, and either confirms the output or flags issues for re-evaluation. This is the "Test" step of the Verification Ritual.

**Why this priority**: This is the quality gate from the Verification Ritual. It is prioritized as P2 because the core pipeline (validate → suggest → validate personas → execute → report → dictionary) must work first, then the quality gate is layered on.

**Independent Test**: Provide a feature-engineered CSV and the cleaned input CSV. Have the Data Analyst persona compare them and verify that it catches at least one known introduced error in a test scenario.

**Acceptance Scenarios**:

1. **Given** a feature-engineered CSV and the cleaned input, **When** the Data Analyst persona reviews them, **Then** it confirms that the transformations match the approved decisions and that original columns are unchanged.
2. **Given** a transformation introduced an error (e.g., a one-hot encoding that missed a category value), **When** the Data Analyst persona reviews, **Then** it flags the issue for re-evaluation before the output is finalized.

---

### User Story 8 — Maintain Skill B Mistake Log (Priority: P2)

Each execution of Skill B records any errors, rejected feature suggestions, persona disagreements, handoff contract violations, and edge-case warnings in a structured mistake log. The PM can aggregate these logs over time to identify recurring patterns and trigger Constitution updates.

**Why this priority**: Required by the constitution (Mistake Logging), but not blocking the core feature engineering pipeline. Can be implemented after the core flow is stable.

**Independent Test**: Run the pipeline on a CSV that triggers at least one persona rejection and one handoff contract warning. Verify that both events appear in the mistake log.

**Acceptance Scenarios**:

1. **Given** a persona rejects a feature engineering suggestion during the validation loop, **When** the pipeline completes, **Then** the rejection is recorded in the mistake log with the reason and the alternative that was adopted.
2. **Given** a handoff contract violation is detected at input validation, **When** the pipeline stops, **Then** the violation is recorded in the mistake log.
3. **Given** the mistake log is exported, **When** it is inspected, **Then** it contains no raw data values — all identifiers are masked or hashed.

---

### Edge Cases

- What happens when the cleaned CSV from Skill A has no columns suitable for feature engineering (e.g., all columns are identifiers or free text)? The system should report that no feature engineering opportunities were identified and produce no new features — outputting the original cleaned CSV unchanged with a report explaining the finding.
- What happens when one-hot encoding a categorical column with very high cardinality (e.g., 500+ unique values)? The system should flag the high cardinality during the persona loop, and personas should challenge whether one-hot encoding is appropriate or whether an alternative (e.g., frequency encoding, target encoding) should be used.
- What happens when normalization is applied to a column with zero variance (all values identical)? The system should detect this and skip normalization for that column, documenting the reason in the transformation report.
- What happens when date/time extraction is applied to a column with inconsistent date formats? The system should detect the inconsistency, flag it during the persona loop, and propose a parsing strategy before extraction.
- What happens when the feature-engineered CSV has significantly more columns than the cleaned input (e.g., one-hot encoding produces 100+ new columns)? The system should flag the column explosion in the transformation report and the Data Analyst persona should verify that this is intentional and justified.
- What happens when a derived feature produces NaN or infinity values (e.g., division by zero in a ratio column)? The system should detect these values, flag them in the transformation report, and propose a handling strategy (e.g., replace with 0, replace with NaN, drop rows).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-201**: System MUST accept only the cleaned CSV produced by Skill A as input. The system MUST reject any CSV that was not produced by Skill A.
- **FR-202**: System MUST validate the input CSV against the Skill Handoff Contract before proceeding. If any contract violation is detected, the system MUST stop immediately and flag the issue for human review.
- **FR-203**: The LLM MUST analyze the cleaned dataset and propose feature engineering transformations covering: new derived columns (ratios, aggregations), encoding of categorical variables (one-hot, label encoding), date/time feature extraction (day of week, hour, month), and normalization/scaling of numeric columns.
- **FR-204**: Each feature engineering suggestion MUST include a justification and a benchmark comparison explaining the expected analytical value of the proposed feature.
- **FR-205**: System MUST implement the Verification Ritual: Read (LLM personas challenge assumptions) → Run (execute via Python tools) → Test (Data Analyst persona reviews before/after) → Commit (accept verified output).
- **FR-206**: LLM personas MUST challenge the feature engineering suggestions. The persona loop MUST produce a final decision with a confidence score for each transformation.
- **FR-207**: On rejection by an LLM persona, the system MUST present the next best alternative with justification.
- **FR-208**: System MUST execute approved transformations using pandas, numpy, and scikit-learn via Claude.ai's Python tools.
- **FR-209**: System MUST NOT apply any transformation that was not approved through the persona validation loop.
- **FR-210**: System MUST preserve all original cleaned columns in the output CSV unless an approved decision explicitly removes one (e.g., dropping the original categorical column after one-hot encoding).
- **FR-211**: System MUST produce a feature-engineered CSV as output.
- **FR-212**: System MUST generate a transformation report (markdown) following the mandatory 3-part justification template for each transformation: (1) What was done? (2) Why? (3) What is the impact? Each entry MUST also include a benchmark comparison for the new feature.
- **FR-213**: The transformation report MUST include before/after comparisons for column count, row count, and distribution summaries for new features.
- **FR-214**: The transformation report MUST include the confidence score for each transformation decision.
- **FR-215**: The transformation report MUST document rejected transformations and the reasons for rejection.
- **FR-216**: System MUST flag transformations that significantly increase dimensionality (e.g., high-cardinality one-hot encoding) or produce unexpected values (NaN, infinity).
- **FR-217**: System MUST auto-generate a data dictionary (markdown) for all engineered features. Each entry MUST include: feature name, plain-language description, source column(s), transformation method, and data type.
- **FR-218**: System MUST make the feature-engineered CSV, transformation report (markdown), and data dictionary (markdown) available for download.
- **FR-219**: System MUST assign a unique version or run ID to each feature engineering execution.
- **FR-220**: System MUST allow users to reproduce previous outputs using the same inputs and configuration.
- **FR-221**: System MUST maintain a mistake log recording errors, rejected suggestions, persona disagreements, handoff contract violations, and edge-case warnings in a structured format.
- **FR-222**: Mistake log MUST never contain raw data values. All identifiers MUST be masked or hashed.
- **FR-223**: All documentation (transformation report, data dictionary) MUST be written in plain language. Basic statistical terms are permitted without explanation. Method-specific terms (e.g., one-hot encoding, z-score normalization) MUST be explained on first use. All acronyms MUST be defined on first use.
- **FR-224**: System MUST run an automated jargon scan on the transformation report and data dictionary to flag undefined acronyms and unexplained terminology.
- **FR-225**: If no feature engineering opportunities are identified, the system MUST report this finding and output the original cleaned CSV unchanged.

### Key Entities

- **Cleaned CSV**: The input dataset produced by Skill A. Must conform to the Skill Handoff Contract. Contains cleaned, validated tabular data with standardized column names and resolved data quality issues.
- **Feature Engineering Decision**: A specific transformation proposed by the LLM, validated through the persona loop, and assigned a confidence score. Each decision maps to one or more columns in the cleaned dataset.
- **LLM Persona**: A role assumed by the LLM during the validation loop (e.g., feature relevance skeptic, statistical reviewer, domain expert, Data Analyst). Personas challenge assumptions and validate decisions.
- **Feature-Engineered CSV**: The output dataset containing both original cleaned columns and all new engineered features. This is the final data output of the pipeline.
- **Transformation Report**: A markdown document following the 3-part justification template plus benchmark comparisons for every transformation, with before/after comparisons and confidence scores.
- **Data Dictionary**: A markdown document auto-generated by the LLM, documenting all engineered features with their names, descriptions, source columns, transformation methods, and data types.
- **Mistake Log**: A structured log of errors, rejections, contract violations, and warnings. Used by the PM to identify recurring patterns and trigger Constitution updates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-201**: Skill B rejects 100% of inputs that violate the Skill Handoff Contract, stopping immediately and flagging the issue for human review.
- **SC-202**: Every feature engineering decision has a documented justification following the 3-part template, a benchmark comparison, and a confidence score.
- **SC-203**: The persona validation loop challenges at least one assumption per execution — no feature set passes through unchallenged.
- **SC-204**: The feature-engineered CSV contains all approved new features and all original cleaned columns (unless an approved decision explicitly removed one).
- **SC-205**: Before/after comparisons are present in the transformation report for every transformation, covering column count, row count, and distribution summaries for new features.
- **SC-206**: Every engineered feature has an entry in the data dictionary with all required fields (name, description, source columns, method, data type).
- **SC-207**: The transformation report and data dictionary pass the plain-language compliance check: no undefined acronyms, no unexplained method-specific terms, every metric includes context, every new feature includes a benchmark comparison.
- **SC-208**: A non-technical stakeholder (Level B user) can read the transformation report and understand every decision without technical assistance (stranger test).
- **SC-209**: A data scientist can read the data dictionary and understand every engineered feature without referring back to the transformation report or the original dataset.
- **SC-210**: The pipeline handles all required edge cases: no-opportunity datasets, high-cardinality encoding, zero-variance columns, inconsistent date formats, column explosion, and NaN/infinity in derived features.
- **SC-211**: Outputs for the same input CSV and configuration are deterministic and reproducible.
- **SC-212**: The mistake log captures all persona rejections, contract violations, edge-case warnings, and execution errors in a structured format with no raw data values.

---

**Governed by**: [constitution.md](./constitution.md) v1.1.0