# AI-Assisted Data Prep Pipeline Constitution

## Version B: Python Tools MVP (Claude Code deferred to V2)

---

## Core Principles

### I. Purpose & Scope

This project transforms raw, messy CSV files into clean, decision-ready datasets through a two-module pipeline built as standard Python scripts, executed locally via CLI. Claude Code with Claude Agent Skills is planned for V2. The pipeline serves two primary user groups: non-technical business users (Level B) who interact with Module A (Data Cleaning), and data scientists who interact with Module B (Feature Engineering).

- **Problem:** Raw CSV data requires significant manual effort to clean, validate, and prepare for analysis or modeling.
- **Primary users:** Non-technical business stakeholders (Module A) and data scientists (Module B).
- **Outcome that matters most:** Trustworthy, well-documented, decision-ready data — with zero tolerance for hallucinated or fabricated transformations.
- **MVP scope:** Tabular CSV data only. Single file in, single output out. Consumer credit banking data is deferred to post-MVP.
- **MVP platform:** Standard Python scripts executed locally via CLI. No AI dependency — the pipeline is fully deterministic.
- **V2 platform:** Claude Code with Claude Agent Skills, adding AI-assisted interaction, natural-language approval, and inline explanations.

### II. AI as Overconfident Intern

In V2, when Claude Code is introduced, AI will be treated as a capable but unreliable assistant. All AI-generated outputs must pass through the Verification Ritual before acceptance. Humans remain responsible for all final decisions.

**MVP (Python Tools):** The pipeline is deterministic — no AI generation. The "overconfident intern" principle applies to the transformation logic itself: all suggested transformations must be presented to the user for approval before execution, even though they are rule-based.

**V2 (Claude Code):** The full Verification Ritual applies:
  1. **Read:** Review the transformation report (plain-language summary with justification).
  2. **Run:** Execute the associated scripts and tools.
  3. **Test:** Run unit tests (Pandera for schema validation) and property-based tests (Hypothesis for edge cases). Tests use a hybrid approach — pre-defined templates for common cases, dynamically generated for edge cases.
  4. **Commit:** Accept only verified, human-approved output.

**Applies to both MVP and V2:**
- **Module/Skill Handoff Contract:** Module A produces a standardized output format that Module B expects. If Module B detects issues with Module A's output, Module B stops and flags the issue for human review.
- **Mistake Logging:** Each module maintains its own mistake log. The PM aggregates logs into a summary report and uses recurring patterns to trigger Constitution updates.
- **Approval Model (MVP):** Modules pause and present a plain-language approval step via CLI prompts. Users can approve (y/n) or request more detail. On rejection, the module presents the next best alternative.
- **Approval Model (V2):** Skills pause and present an interactive, plain-language approval step directly in Claude Code. Users can APPROVE, REJECT, or request EXPLAIN MORE.
- **Batch Mode (MVP):** A `--auto-approve` flag allows experienced users to skip confirmations for transformations below a configurable risk threshold. Transformations above the threshold always require explicit approval.

### III. Plain-Language Commitment

All specs, plans, documentation, and transformation reports must be understandable to a non-developer stakeholder. A single documentation voice is used across both modules — non-technical language that data scientists will also understand.

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
  - New features must include benchmark comparisons.
  - Jargon scan: no undefined acronyms, no unexplained terminology.
- **Output format (MVP):** Transformation reports are generated as markdown files alongside the output CSV.
- **Output format (V2):** Transformation reports are generated and presented inline in Claude Code with AI explanation.

### IV. Guardrails Over Features

Guardrails are first-class citizens in this project. Decisions about security, data handling, and constraints are not optional. If a feature conflicts with a guardrail, the guardrail wins.

- **Non-Negotiable Guardrails** (cannot be overridden without a Major version change):
  - Security and PII rules
  - Zero hallucination tolerance (MVP: deterministic pipeline; V2: Verification Ritual)
  - Human-in-the-loop approval for all transformations
- **Discussable Guardrails** (can be relaxed with full team consensus):
  - All other rules and constraints
- When a feature request or stakeholder demand conflicts with the Constitution, the team must reference the specific section and explain why the guardrail takes precedence.
- **Change Authority:**
  - Process and documentation changes: PM has final approval.
  - Technical changes: PM and relevant Module Owner co-approve.
  - Users may submit change requests; PM and Module Owners decide.

### V. Iterative Refinement

This Constitution is a living document. It is versioned and updated as the team learns. Recurring problems should trigger Constitution updates, not only one-off fixes.

- **Update Triggers:**
  - Recurring mistakes identified in module logs
  - Guardrails found to be overly restrictive but safe
  - Inconsistencies between Constitution and actual practice
  - V2 migration decisions that require Constitution amendments
- **Update Responsibilities:**
  - PM updates the Constitution and project overview.
  - Module Owners update their respective specs.
  - A checklist ensures all documents remain in sync after any change.
- **Review Cadence:**
  - During MVP development: at each project gate.
  - Post-deployment: weekly, transitioning to bi-weekly once stable.
- **Version Control:** Git with structured commit conventions.


## Tech Stack & Platform Rules

### Platform

| Phase | Platform | Details |
|-------|----------|---------|
| **MVP** | Standard Python scripts (local CLI) | Deterministic pipeline, no AI dependency |
| **V2** | Claude Code (local) | Claude Agent Skills, auto-discovered from `.claude/skills/` |

### Approved Languages & Frameworks

- **Primary language:** Python 3.10+ (team to confirm minimum version)
- **Philosophy:** Vanilla Python first. Libraries are introduced only for tasks that are error-prone or impractical to implement from scratch.
- **MVP dependencies:**
  - `pandas` — dataframe manipulation
  - `pandera` — schema validation
  - `hypothesis` — property-based testing
  - `numpy` — numerical operations
  - `pytest` — test runner
- **Provisional:** `scikit-learn` — to be determined based on Module B requirements
- **Post-MVP (V2):** `great_expectations` — advanced data validation
- **Prohibited:** No frameworks or libraries outside the approved list without PM + Module Owner approval and a compatibility test.

### Dependency Management

- Version ranges specified in `requirements.txt`.
- New library adoption requires: PM + relevant Module Owner approval → compatibility test before integration.

### User Interaction (MVP)

- Users interact with modules via CLI commands.
- **Approval UX:** Plain-language CLI prompts → user confirms (y/n) or selects from options.
- On rejection, the module presents the next best alternative option.
- `--help` flag with human-readable descriptions for every command.
- `--auto-approve` flag for experienced users (configurable risk threshold).
- Pre-configured defaults so non-technical users can run with minimal flags.

### User Interaction (V2)

- Users interact with skills directly in Claude Code.
- **Approval UX:** Standardized APPROVE / REJECT / EXPLAIN MORE interaction pattern.
- On rejection, the skill presents the next best alternative automatically.

### Output Format

- **Data output:** CSV (cleaned and/or feature-engineered)
- **Reports:** Markdown files (transformation reports, data quality reports)
- **Logs:** Structured format (JSON or similar), never containing data values

### V2 Migration Design Principles

To minimize rework when transitioning from MVP (Python tools) to V2 (Claude Code):

1. **Module boundaries = Skill boundaries:** Module A and Module B are designed with the same input/output contracts that future Agent Skills will use.
2. **Standardized handoff format:** The intermediate format between Module A and Module B is identical to the future Skill A → Skill B handoff contract.
3. **Report templates:** The same markdown justification template is used in MVP reports and future Claude Code inline reports.
4. **Test suite portability:** All pytest, pandera, and hypothesis tests work identically in both environments.
5. **SKILL.md preparation:** Each module's purpose, inputs, outputs, and constraints are documented in a format that can be directly converted to `SKILL.md` files for Claude Code.


## Security, Privacy & Data Boundaries

### Secrets & Credentials

- **Never** hardcode API keys, tokens, or passwords in code.
- Store secrets in a local `.env` file only.
- `.gitignore` must include `.env` before any version control system is adopted.
- **Never** copy or share session tokens or authentication details.
- If a secret is accidentally committed, it must be **rotated immediately**. Removal from the repository alone is not sufficient.
- **MVP Note:** No API keys are needed in this phase (no external services). These rules activate when API-based access is introduced.
- **V2 Note:** Claude Code introduces Anthropic API interaction. API credentials must follow these rules.

### PII & Sensitive Data

- **PII Categories:**
  - Direct: names, emails, phone numbers, SSNs, addresses
  - Indirect: date of birth, zip code, job title
  - Financial: account numbers, credit card numbers, transaction details
- **Detection:** Hybrid approach — automated scan flags potential PII, human confirms.
- **V1 Behavior:** Basic warning only (e.g., "Column X may contain PII — proceed with caution").
- **Post-MVP Behavior:** Pipeline stops and alerts the user. Cannot proceed until PII is handled. User must mask or anonymize data externally and re-upload.
- **Logging:** Data values must **never** appear in logs. All identifiers must be masked or hashed.
- **V1 Data Source:** Open-source CSVs (e.g., Kaggle) — no sensitive data.

### External Services & Data Sharing

- **External APIs (MVP):** None — the pipeline is fully local. No data leaves the local environment.
- **External APIs (V2):** Data processed through Anthropic's API via Claude Code. Only non-sensitive, anonymized data is permitted.
- **Data Residency:** All data (input, processing, output, logs) remains on the local file system.
- **Team Sharing:** Via Git repository. No PII and no secrets in the repo.
- **Large Files:** Only sample data (small subsets) committed to the repo. Full datasets are stored locally.


## Out of Scope

### Functional Exclusions

The following features are intentionally **not** being built in V1:

- Claude Code / AI-assisted interaction — deferred to V2
- Web UI or dashboard — interaction is through CLI only
- Automated model training on cleaned data — the pipeline ends at clean, feature-engineered data plus documentation
- Multi-file joins or merging multiple CSVs — single CSV in, single output out
- Consumer credit banking data processing — deferred to post-MVP
- Full PII enforcement (stop and alert) — deferred to post-MVP; V1 has basic warning only

### Technical Exclusions

- Cloud deployment — the pipeline is fully local
- `great_expectations` — deferred to V2
- `scikit-learn` — provisional, to be determined for Module B
- XLSX or database table ingestion — deferred to V2

### V1 Definition of Done

V1 is a **robust tool** that handles edge cases, not a happy-path proof of concept.

**Edge cases that must be handled:**
- Empty CSV (headers only, no rows)
- Single-row CSV
- All values missing in a column
- Mixed types in a single column (e.g., "123", "abc", "45.6")
- Special characters in column names (spaces, emojis, unicode)
- Duplicate column names

**Success criteria:** The pipeline must successfully process 3 CSVs end-to-end via CLI, producing clean data, engineered features, and full documentation for each:

1. **NYC TLC Trip Records** — large, messy, time and location fields
2. **Kaggle — Instacart Online Grocery Shopping / Dunnhumby "The Complete Journey"** — retail transaction data
3. **UCI dataset** — mixed numeric and categorical data


## Governance

### Roles & Ownership

| Role | Person | Responsibilities |
|------|--------|-----------------|
| **PM** | Margarida Sacouto | Owns Constitution and project overview spec; final approval on process and documentation changes; escalation point for unresolved disputes |
| **Module A Owner** | Xiao Pan | Owns Module A (Data Cleaning) spec; co-approves technical changes to Module A; proposes changes based on module logs |
| **Module B Owner** | Valerie Bien-Aime | Owns Module B (Feature Engineering) spec; co-approves technical changes to Module B; proposes changes based on module logs |

Users may submit change requests. PM and Module Owners decide on adoption.

### Change Process

- **Proposal:** Async — propose via message or issue with a short rationale.
- **Objection Window:** 48 hours from proposal.
- **Silence Rule:** If no team member objects within 48 hours, the change is approved.
- **Approval Authority:**
  - Process and documentation changes: PM approves.
  - Technical changes: PM + relevant Module Owner co-approve.

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
| G2 | Module A spec complete |
| G3 | Module B spec complete |
| G4 | Modules implemented and tested |
| G5 | 3 CSVs processed successfully |
| G6 (V2) | Claude Code Agent Skills integration |

### Enforcement

- All specs (`spec.md`), plans (`plan.md`), tasks, and modules must comply with this Constitution.
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
