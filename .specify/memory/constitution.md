# AI-Assisted Data Prep Pipeline Constitution

## Core Principles

### I. Purpose & Scope

This project transforms raw, messy CSV files into clean, decision-ready datasets through a two-skill pipeline built on Claude Code. It serves two primary user groups: non-technical business users (Level B) who interact with Skill A (Data Cleaning), and data scientists who interact with Skill B (Feature Engineering).

- **Problem:** Raw CSV data requires significant manual effort to clean, validate, and prepare for analysis or modeling.
- **Primary users:** Non-technical business stakeholders (Skill A) and data scientists (Skill B).
- **Outcome that matters most:** Trustworthy, well-documented, decision-ready data — with zero tolerance for hallucinated or fabricated transformations.
- **MVP scope:** Tabular CSV data only. Single file in, single output out. Consumer credit banking data is deferred to post-MVP.

### II. AI as Overconfident Intern

AI is treated as a capable but unreliable assistant. All AI-generated outputs must pass through the Verification Ritual before acceptance. Humans remain responsible for all final decisions.

- **Verification Ritual:**
  1. **Read:** Review the transformation report (plain-language summary with justification).
  2. **Run:** Execute the associated scripts and tools.
  3. **Test:** Run unit tests (Pandera for schema validation) and property-based tests (Hypothesis for edge cases). Tests use a hybrid approach — pre-defined templates for common cases, dynamically generated for edge cases.
  4. **Commit:** Accept only verified, human-approved output.
- **Skill Handoff Contract:** Skill A produces a standardized output format that Skill B expects. If Skill B detects issues with Skill A's output, Skill B stops and flags the issue for human review.
- **Mistake Logging:** Each skill maintains its own mistake log. The PM aggregates logs into a summary report and uses recurring patterns to trigger Constitution updates.
- **Approval Model:** Skills pause and present an interactive, plain-language approval step directly in Claude Code. Users can approve, reject, or request further explanation.

### III. Plain-Language Commitment

All specs, plans, documentation, and transformation reports must be understandable to a non-developer stakeholder. A single documentation voice is used across both skills — non-technical language that data scientists will also understand.

- Basic statistical terms (e.g., mean, median, mode, outlier) are permitted without explanation.
- Method-specific terms (e.g., z-score, IQR, one-hot encoding) must be explained on first use.
- All acronyms must be defined on first use. No company-specific terminology without explanation.
- **Mandatory Justification Template** — every transformation report must include:
  1. What was done?
  2. Why?
  3. What alternatives were considered (and why were they rejected)?
  4. What is the impact?
- For trivial transformations, a lightweight version of the template is acceptable at the team's discretion.
- **Plain-Language Tests:**
  - Every metric must be given context (e.g., percentage of rows affected, column name, before/after comparison).
  - Jargon scan: no undefined acronyms, no unexplained terminology.

### IV. Guardrails Over Features

Guardrails are first-class citizens in this project. Decisions about security, data handling, and constraints are not optional. If a feature conflicts with a guardrail, the guardrail wins.

- **Non-Negotiable Guardrails** (cannot be overridden without a Major version change):
  - Security and PII rules
  - Zero hallucination tolerance
  - Human-in-the-loop approval
- **Discussable Guardrails** (can be relaxed with full team consensus):
  - All other rules and constraints
- When a feature request or stakeholder demand conflicts with the Constitution, the team must reference the specific section and explain why the guardrail takes precedence.
- **Change Authority:**
  - Process and documentation changes: PM has final approval.
  - Technical changes: PM and relevant Skill Owner co-approve.
  - Users may submit change requests; PM and Skill Owners decide.

### V. Iterative Refinement

This Constitution is a living document. It is versioned and updated as the team learns. Recurring problems in AI output should trigger Constitution updates, not only one-off fixes.

- **Update Triggers:**
  - Recurring mistakes identified in skill logs
  - Guardrails found to be overly restrictive but safe
  - Inconsistencies between Constitution and actual practice
- **Update Responsibilities:**
  - PM updates the Constitution and project overview.
  - Skill Owners update their respective specs.
  - A checklist ensures all documents remain in sync after any change.
- **Review Cadence:**
  - During MVP development: at each project gate.
  - Post-deployment: weekly, transitioning to bi-weekly once stable.
- **Version Control:** Git with structured commit conventions.


## Tech Stack & Platform Rules

### Platform

- **Development Environment:** Claude Code (local)
- **Skill Architecture:** Claude Agent Skills, auto-discovered from `.claude/skills/` directory
  - Skill A (Data Cleaning): Owned by Xiao Pan
  - Skill B (Feature Engineering): Owned by Valerie Bien-Aime

### Approved Languages & Frameworks

- **Primary language:** Python (runtime version per Claude Code environment)
- **Philosophy:** Vanilla Python first. Libraries are introduced only for tasks that are error-prone or impractical to implement from scratch.
- **MVP dependencies:**
  - `pandas` — dataframe manipulation
  - `pandera` — schema validation
  - `hypothesis` — property-based testing
  - `numpy` — numerical operations
- **Provisional:** `scikit-learn` — to be determined based on Skill B requirements
- **Post-MVP:** `great_expectations` — advanced data validation
- **Prohibited:** No frameworks or libraries outside the approved list without PM + Skill Owner approval and a compatibility test.

### Dependency Management

- Version ranges specified in `requirements.txt`.
- New library adoption requires: PM + relevant Skill Owner approval → compatibility test before integration.

### User Interaction

- Non-technical users interact with skills directly through Claude Code.
- **Approval UX:** Standardized APPROVE / REJECT / EXPLAIN MORE interaction pattern.
- On rejection, the skill presents the next best alternative option.


## Security, Privacy & Data Boundaries

### Secrets & Credentials

- **Never** hardcode API keys, tokens, or passwords in code.
- Store secrets in a local `.env` file only.
- `.gitignore` must include `.env` before any version control system is adopted.
- **Never** copy or share Claude Code session tokens or authentication details.
- If a secret is accidentally committed, it must be **rotated immediately**. Removal from the repository alone is not sufficient.
- **V1 Note:** No API keys are needed in this phase. These rules activate when API-based access is introduced.

### PII & Sensitive Data

- **PII Categories:**
  - Direct: names, emails, phone numbers, SSNs, addresses
  - Indirect: date of birth, zip code, job title
  - Financial: account numbers, credit card numbers, transaction details
- **Detection:** Hybrid approach — automated scan flags potential PII, human confirms.
- **V1 Behavior:** Basic warning only (e.g., "Column X may contain PII — proceed with caution").
- **Post-MVP Behavior:** Pipeline stops and alerts the user. Cannot proceed until PII is handled. User must mask or anonymize data externally and re-upload.
- **Logging:** Data values must **never** appear in logs. All identifiers must be masked or hashed.

### External Services & Data Sharing

- **External APIs:** None — the pipeline is fully local.
- **Data Residency:** All data (input, processing, output, logs) remains on the local file system.
- **V1 LLM Exposure:** Data may be processed through Anthropic's API via Claude Code. Only open-source, non-sensitive data is permitted.
- **Post-MVP LLM Exposure:** Data containing PII must be anonymized locally before any LLM interaction. The skill only ever sees clean data.
- **Team Sharing:** Via Git repository. No PII and no secrets in the repo.
- **Large Files:** Only sample data (small subsets) committed to the repo. Full datasets are stored locally.


## Out of Scope

### Functional Exclusions

The following features are intentionally **not** being built in V1:

- Web UI or dashboard — interaction is through Claude Code only
- Automated model training on cleaned data — the pipeline ends at clean, feature-engineered data plus documentation
- Multi-file joins or merging multiple CSVs — single CSV in, single output out
- Consumer credit banking data processing — deferred to post-MVP
- Full PII enforcement (stop and alert) — deferred to post-MVP; V1 has basic warning only

### Technical Exclusions

- Cloud deployment — the pipeline is fully local
- `great_expectations` — deferred to post-MVP
- `scikit-learn` — provisional, to be determined for Skill B

### V1 Definition of Done

V1 is a **robust tool** that handles edge cases, not a happy-path proof of concept.

**Edge cases that must be handled:**
- Empty CSV (headers only, no rows)
- Single-row CSV
- All values missing in a column
- Mixed types in a single column (e.g., "123", "abc", "45.6")
- Special characters in column names (spaces, emojis, unicode)
- Duplicate column names

**Success criteria:** The pipeline must successfully process 3 CSVs end-to-end, producing clean data, engineered features, and full documentation for each:

1. **NYC TLC Trip Records** — large, messy, time and location fields
2. **Kaggle — Instacart Online Grocery Shopping / Dunnhumby "The Complete Journey"** — retail transaction data
3. **UCI dataset** — mixed numeric and categorical data


## Governance

### Roles & Ownership

| Role | Person | Responsibilities |
|------|--------|-----------------|
| **PM** | Margarida Sacouto | Owns Constitution and project overview spec; final approval on process and documentation changes; escalation point for unresolved disputes |
| **Skill A Owner** | Xiao Pan | Owns Skill A (Data Cleaning) spec; co-approves technical changes to Skill A; proposes changes based on skill logs |
| **Skill B Owner** | Valerie Bien-Aime | Owns Skill B (Feature Engineering) spec; co-approves technical changes to Skill B; proposes changes based on skill logs |

Users may submit change requests. PM and Skill Owners decide on adoption.

### Change Process

- **Proposal:** Async — propose via message or issue with a short rationale.
- **Objection Window:** 48 hours from proposal.
- **Silence Rule:** If no team member objects within 48 hours, the change is approved.
- **Approval Authority:**
  - Process and documentation changes: PM approves.
  - Technical changes: PM + relevant Skill Owner co-approve.

### Versioning

Changes to this Constitution follow semantic versioning:

| Level | Trigger | Example |
|-------|---------|---------|
| **Major** (v2.0.0) | Fundamental change to a core principle or non-negotiable guardrail | v1.0.0 → v2.0.0 |
| **Minor** (v1.1.0) | New rule added, section updated, or scope change | v1.0.0 → v1.1.0 |
| **Patch** (v1.0.1) | Typo fix, clarification, no behavioral change | v1.0.0 → v1.0.1 |

### Review Cadence

| Phase | Cadence |
|-------|---------|
| MVP Development | At each project gate |
| Post-Deployment | Weekly, transitioning to bi-weekly once stable |

### Project Gates

| Gate | Milestone |
|------|-----------|
| G1 | Constitution ratified |
| G2 | Skill A spec complete |
| G3 | Skill B spec complete |
| G4 | Skills implemented |
| G5 | 3 CSVs processed successfully |

### Enforcement

- All specs (`spec.md`), plans (`plan.md`), tasks, and skills must comply with this Constitution.
- AI prompts and skill instructions should reference this Constitution when relevant.
- **Violation Resolution:**
  1. **Step 1:** Raise directly with the team member (peer-to-peer).
  2. **Step 2:** If unresolved, escalate to PM (Margarida) for final decision.
- **Severity-Based Response:**
  - **Non-negotiable guardrail violation:** Work pauses immediately until resolved.
  - **Other violations:** Work may continue while the team discusses.
- All violations are treated as **learning moments** — the team discusses, resolves, and updates the Constitution if a recurring pattern is identified.
- If a conflict arises between a spec/plan and this Constitution, the team must either:
  - Update the Constitution (with explicit agreement and appropriate version bump), OR
  - Adjust the spec/plan to comply.

---

**Version**: v1.0.0 | **Ratified**: 2026-03-25 | **Last Amended**: 2026-03-25