# AI-Assisted Data Prep Pipeline Constitution

---

## Core Principles

### I. Purpose & Scope

This project transforms raw, messy CSV files into clean, decision-ready datasets through an LLM-powered two-module pipeline. The pipeline uses Claude 4.5 Sonnet as its core runtime engine to analyze data, judge the best transformation approaches, interact with users in plain language, and generate documentation.

The pipeline serves two primary user groups: non-technical business users (Level B) who interact with Skill A (Data Cleaning), and data scientists who interact with Skill B (Feature Engineering).

- **Problem:** Raw CSV data requires significant manual effort to clean, validate, and prepare for analysis or modeling.
- **Primary users:** Non-technical business stakeholders (Skill A) and data scientists (Skill B).
- **Outcome that matters most:** Trustworthy, well-documented, decision-ready data.
- **MVP scope:** Tabular CSV data only. Single file in, single output out. Consumer credit banking data is deferred to post-MVP.
- **MVP platform:** Claude.ai with built-in Python tools. Users upload CSVs and receive cleaned data plus documentation.
- **V2 platform:** Claude Code with Claude Agent Skills, adding richer interaction, local Python environment, and advanced testing capabilities.
- **LLM:** Claude 4.5 Sonnet (Anthropic). The LLM is a core runtime component — it analyzes data, makes transformation recommendations, and generates documentation.

### II. AI as Overconfident Intern

The LLM (Claude 4.5 Sonnet) is treated as a capable but unreliable assistant. It may suggest plausible-sounding but incorrect transformation strategies. All LLM-generated suggestions must have an internal validation loop with different personas challenging the initial LLM decision, to achieve a final robust decision. The report produced by the LLM will include a 'confidence score' in the decision.  

**Verification Ritual:**
  1. **Read:** Generate LLM personas to review the initisl suggested transformation and challenge the assumptions. Decide on the best approach.
  2. **Run:** Execute the approved transformation via Python tools.
  3. **Test:** Verify the output (MVP: have an LLM Data Analyst persona to review transformations and compare before/after).
  4. **Commit:** Accept only verified, Data Analyst LLM persona output.

**Applies to both MVP and V2:**
- **Skill Handoff Contract:** Skill A produces a standardized output format that Skill B expects. If Skill B detects issues with Skill A's output, Skill B stops and flags the issue for human review.
- **Mistake Logging:** Each skill maintains its own mistake log. The PM aggregates logs into a summary report and uses recurring patterns to trigger Constitution updates.
- **Approval Model:** The LLM presents transformation suggestions with justification. LLM personas approve, reject, or ask for more detail in natural language. On rejection, the LLM presents the next best alternative with justification. Final report for human includes final decision in MVP. In V2, user can inspect the discussion between LLM personas to get details on the reasoning. 
- **LLM Data Access:** The LLM has access to the full dataset via Python tools. It analyzes the complete data to make informed recommendations.

### III. Plain-Language Commitment

All specs, plans, documentation, and transformation reports must be understandable to a non-developer stakeholder. A single documentation voice is used across both modules — non-technical language that data scientists will also understand.

- Basic statistical terms (e.g., mean, median, mode, outlier) are permitted without explanation.
- Method-specific terms (e.g., z-score, IQR, one-hot encoding) must be explained on first use.
- All acronyms must be defined on first use. No company-specific terminology without explanation.
- **Mandatory Justification Template** — every transformation report must include:
  1. What was done?
  2. Why?
  3. What is the impact?
  4. (V2 - What alternatives were considered (and why were they rejected)?)
- **Plain-Language Tests:**
  - Every metric must be given context (e.g., percentage of rows affected, column name, before/after comparison).
  - New features must include benchmark comparisons.
  - Jargon scan: no undefined acronyms, no unexplained terminology.
- **Output format (MVP):** Transformation reports generated as markdown files by the LLM, downloadable from Claude.ai alongside the output CSV.
- **Output format (V2):** Transformation reports generated and presented inline in Claude Code.

### IV. Guardrails Over Features

Guardrails are first-class citizens in this project. Decisions about security, data handling, and constraints are not optional. If a feature conflicts with a guardrail, the guardrail wins.

- **Non-Negotiable Guardrails** (cannot be overridden without a Major version change):
  - Security and PII rules
  - Validation loop with personas to prevent hallucination
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
  - LLM model updates or behavior changes
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

| Phase | Platform | LLM | Python Execution |
|-------|----------|-----|-----------------|
| **MVP** | Claude.ai | Claude 4.5 Sonnet | Claude.ai's built-in Python tools (sandboxed) |
| **V2** | Claude Code | Claude 4.5 Sonnet | Full local Python environment + Agent Skills |

### LLM Configuration

- **Model:** Claude 4.5 Sonnet (Anthropic)
- **Role:** Core runtime component — analyzes data, recommends transformations, generates documentation
- **Data Access:** Full dataset (uploaded by user to Claude.ai)
- **Intent:** Low temperature / high consistency for maximum reproducibility (to be enforced in V2 where temperature control is available)

### Approved Languages & Frameworks

- **Primary language:** Python (version as provided by Claude.ai's Python tools environment)
- **Philosophy:** Vanilla Python first. Libraries are introduced only for tasks that are error-prone or impractical to implement from scratch.
- **MVP dependencies (pre-installed in Claude.ai):**
  - `pandas` — dataframe manipulation
  - `numpy` — numerical operations
  - `scikit-learn` - encoding, normalization, feature generation
- **V2 dependencies (Claude Code — can pip install):**
  - All MVP dependencies, plus:
  - `pandera` — schema validation
  - `hypothesis` — property-based testing
  - `pytest` — test runner
  - `great_expectations` — advanced data validation (V2)
- **Prohibited:** No frameworks or libraries outside the approved list without PM + Module Owner approval and a compatibility test.

### Dependency Management

- MVP: Limited to pre-installed libraries in Claude.ai. No pip install capability.
- V2: Version ranges specified in `requirements.txt`. New library adoption requires PM + relevant Module Owner approval → compatibility test before integration.

### User Interaction

- **MVP (Claude.ai):** Users interact with the LLM in natural language. The LLM presents transformation suggestions with justification. 
- **V2 (Claude Code):** Users interact with skills directly in Claude Code. Standardized APPROVE / REJECT / EXPLAIN MORE interaction pattern. On rejection, the skill presents the next best alternative automatically.

### MVP Workflow

1. User uploads a raw CSV to Claude.ai
2. Claude 4.5 Sonnet reads/analyzes the full dataset via Python tools
3. Claude summarizes the issues and suggests transformations with justification
4. LLM personas analyze the suggestions and challenge assumptions
5. On rejection, Claude presents the next best alternative with justification
6. Claude executes approved transformations via Python tools
7. Claude generates a transformation report (markdown) following the 3-part justification template
8. User downloads the cleaned/engineered CSV and the transformation report

### Output Format

- **Data output:** CSV (cleaned and/or feature-engineered)
- **Reports:** Markdown files (transformation reports, data quality reports)
- **Logs:** Structured format, never containing raw data values

### V2 Migration Design Principles

To minimize rework when transitioning from MVP (Claude.ai) to V2 (Claude Code):

1. **Module boundaries = Skill boundaries:** Module A and Module B are designed with the same input/output contracts that future Agent Skills will use.
2. **Standardized handoff format:** The intermediate format between Module A and Module B is identical to the future Skill A → Skill B handoff contract.
3. **Report templates:** The same markdown justification template is used in MVP reports and future Claude Code inline reports.
4. **Test suite portability:** Manual verification steps in MVP are documented so they can be converted to automated tests (Pandera, Hypothesis) in V2.
5. **SKILL.md preparation:** Each module's purpose, inputs, outputs, and constraints are documented in a format that can be directly converted to `SKILL.md` files for Claude Code.


## Security, Privacy & Data Boundaries

### Secrets & Credentials

- **Never** hardcode API keys, tokens, or passwords in code.
- **MVP Note:** No API key management needed — Claude.ai handles authentication. Users interact through the Claude.ai interface.
- **V2 Note:** Claude Code introduces direct API interaction. Store secrets in a local `.env` file. `.gitignore` must include `.env` before any version control system is adopted.
- If a secret is accidentally committed, it must be **rotated immediately**. Removal from the repository alone is not sufficient.

### PII & Sensitive Data

- **PII Categories:**
  - Direct: names, emails, phone numbers, SSNs, addresses
  - Indirect: date of birth, zip code, job title
  - Financial: account numbers, credit card numbers, transaction details
- **Detection:** Hybrid approach — LLM flags potential PII during analysis, human confirms.
- **V1 Behavior:** Basic warning only (e.g., "Column X may contain PII — proceed with caution"). MVP uses open-source, non-sensitive datasets only.
- **Post-MVP Behavior:** Pipeline stops and alerts the user. Cannot proceed until PII is handled. User must mask or anonymize data externally and re-upload.
- **Logging:** Raw data values must **never** appear in logs or be persisted outside the active Claude.ai session. All identifiers must be masked or hashed in any exported logs.

### External Services & Data Sharing

- **Data Transit (MVP):** Data is uploaded to Claude.ai and processed through Anthropic's API. This is accepted for non-sensitive, open-source data. The security guardrail is relaxed for the MVP given that only non-sensitive data is used.
- **Data Transit (V2):** Data processed through Anthropic's API via Claude Code. PII must be anonymized locally before any LLM interaction.
- **Data Residency:** Input data resides in Claude.ai during the session. Output data (cleaned CSV, reports) is downloaded by the user to their local system.
- **Team Sharing:** Via Git repository. No PII and no secrets in the repo.
- **Large Files:** Only sample data (small subsets) committed to the repo. Full datasets are stored locally.


## Out of Scope

### Functional Exclusions

The following features are intentionally **not** being built in V1:

- Claude Code / Agent Skills — deferred to V2
- Web UI or dashboard — interaction is through Claude.ai's conversational interface
- Automated model training on cleaned data — the pipeline ends at clean, feature-engineered data plus documentation
- Multi-file joins or merging multiple CSVs — single CSV in, single output out
- Consumer credit banking data processing — deferred to post-MVP
- Full PII enforcement (stop and alert) — deferred to post-MVP; V1 has basic warning only

### Technical Exclusions

- Cloud deployment — data processed via Anthropic's API only
- `pandera`, `hypothesis`, `pytest` — not available in Claude.ai; deferred to V2
- `great_expectations` — deferred to V2
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

**Success criteria:** The pipeline must successfully process 3 CSVs end-to-end in Claude.ai, producing clean data, engineered features, and full documentation for each:

1. **NYC TLC Trip Records** — large, messy, time and location fields
2. **Kaggle — Instacart Online Grocery Shopping / Dunnhumby "The Complete Journey"** — retail transaction data
3. **UCI dataset** — mixed numeric and categorical data


## Governance

### Roles & Ownership

| Role | Person | Responsibilities |
|------|--------|-----------------|
| **PM** | Margarida Sacouto | Owns Constitution and project overview spec; final approval on process and documentation changes; escalation point for unresolved disputes |
| **Skill A Owner** | Xiao Pan | Owns Skill A (Data Cleaning) spec; co-approves technical changes to Skill A; proposes changes based on skill logs |
| **Skill B Owner** | Valerie Bien-Aime | Owns skill B (Feature Engineering) spec; co-approves technical changes to Skill B; proposes changes based on skill logs |

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
| G4 | Skills implemented and tested |
| G5 | 3 CSVs processed successfully |
| G6 (V2) | Claude Code Agent Skills integration |

### Enforcement

- All specs (`spec.md`), plans (`plan.md`), tasks, and skills must comply with this Constitution.
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

**Version**: v1.1.0 | **Ratified**: 2026-03-26 | **Last Amended**: 2026-04-02
