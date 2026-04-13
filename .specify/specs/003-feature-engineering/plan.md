# Implementation Plan: Feature Engineering with Persona Validation

**Branch**: `003-feature-engineering` | **Date**: 2026-04-06 | **Spec**: `specs/003-feature-engineering/spec.md`
**Input**: Feature specification from `/specs/003-feature-engineering/spec.md`

## Summary

Skill B takes the cleaned CSV produced by Skill A and engineers new features from it — derived columns (ratios, aggregations), categorical encoding (one-hot, label), date/time extraction (day of week, hour, month), basic text features (string length, word count), aggregate metrics (groupby + transform mapped back to rows), and normalization/scaling of numeric columns. Feature proposals are made by the LLM in 6 batches organized by transformation type, with each batch challenged by three LLM personas (Feature Relevance Skeptic, Statistical Reviewer, Domain Expert) before execution. Every approved feature receives a confidence score (0–100, using fixed values matching Skill A's bands: 95, 82, 67, 50, 35) based on persona loop outcomes. After execution, a Data Analyst persona verifies the output as a quality gate. The skill produces four outputs: a feature-engineered CSV (with `feat_` prefix on all new columns), a transformation report following the 3-part justification template with benchmark comparisons, a data dictionary documenting every engineered feature, and a mistake log recording all events. Skill B validates Skill A's output against a handoff contract before doing anything — if the input doesn't meet the contract, it stops and flags for human review. Skill B reads PII flags from Skill A's transform-metadata.json (which carries them forward from Feature 1), and runs a lightweight column-name heuristic as a fallback if metadata is unavailable.

## Technical Context

**Language/Version**: Python (version determined by the Claude.ai sandboxed execution environment — not user-configurable in MVP)

**LLM Runtime**: Claude 4.5 Sonnet (Anthropic) — core runtime component. Analyzes data, proposes feature engineering transformations in batches, runs the four-persona validation loop, and generates all documentation (transformation report, data dictionary).

**Primary Dependencies**: pandas, numpy, scikit-learn (pre-installed in Claude.ai; pip install permitted for approved libraries per constitution amendment)

**Storage**: N/A — input CSV uploaded by user to Claude.ai, outputs (feature-engineered CSV, transformation report, data dictionary, mistake log) downloaded by user. No persistent storage between sessions.

**Testing**: LLM Data Analyst persona reviews transformations and compares before/after (MVP). Automated testing with pytest, pandera, and hypothesis deferred to V2.

**Target Platform**: Claude.ai with built-in Python tools (MVP). Claude Code with Agent Skills (V2).

**Project Type**: LLM-driven data transformation pipeline executed conversationally in Claude.ai

**Performance Goals**: Complete feature engineering pipeline returned within a single synchronous Claude.ai session. File size limits: input CSV hard limit at >500,000 cells (reject), warning at 100,000–500,000 cells. Output column explosion handled by FR-216 and persona challenge, not a hard threshold.

**Constraints**: Claude.ai sandbox limits (file size caps, memory, execution timeouts) not yet fully tested — conservative cell-count thresholds applied. MVP limited to pre-installed libraries plus approved pip installs. Single CSV in, single output out. Skill B designed for separate sessions from Skill A but works in the same session too. 

**Scale/Scope**: MVP demonstrates on 3 datasets (NYC TLC, Instacart/Dunnhumby, UCI). Design must support any arbitrary cleaned CSV, not hardcoded to these three.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Rule | Source | Status |
|------|--------|--------|
| LLM suggestions must pass through persona validation loop with confidence scores | Core Principles §II | ✅ Covered — 4 personas (3 challenge + 1 verification), confidence 0–100 with fixed values matching Skill A bands, batched by type |
| Verification Ritual: Read → Run → Test → Commit | Core Principles §II | ✅ Covered — propose (Read) → execute (Run) → Data Analyst verify (Test) → deliver (Commit) |
| Skill Handoff Contract: Skill B stops and flags if Skill A output has issues | Core Principles §II | ✅ Covered — handoff contract defined in RQ-001, validate-handoff contract |
| Plain-language commitment: 3-part justification template, jargon scan, acronyms defined | Core Principles §III | ✅ Covered — FR-212, FR-223, FR-224, two-layer jargon scan |
| MVP dependencies limited to pandas, numpy, scikit-learn | Tech Stack | ✅ Covered — no additional libraries required |
| pip install permitted for approved libraries | Tech Stack (amended) | ✅ Covered — constitution amendment per Skill A |
| No raw data values in logs | Security §PII | ✅ Covered — FR-222, enforced in mistake log and all outputs |
| Outputs: CSV + Markdown reports, downloadable from Claude.ai | Tech Stack §Output Format | ✅ Covered — FR-211, FR-212, FR-217, FR-218 |
| Unique version/run ID per execution | Project Overview §FR | ✅ Covered — FR-219, format: feature-YYYYMMDD-HHMMSS-XXXX |
| Reproducibility: same input + config = same output | Project Overview §FR | ✅ Covered — FR-220 |
| PII detection: basic warning only in MVP | Security §PII | ✅ Covered — PII re-check added (spec gap resolved): reads PII flags from Skill A's transform-metadata.json (carried forward from Feature 1), heuristic scan if not |
| Mistake Logging: each skill maintains structured log, no raw data | Core Principles §II | ✅ Covered — FR-221, FR-222, append-as-you-go implementation |
| AI as Overconfident Intern: LLM code never executed directly | Core Principles §II | ✅ Covered — execution script uses pre-built code paths, LLM implementation_hint is advisory only |

**Summary**: All rules passing. 1 former blocker resolved (handoff contract now defined). 1 spec gap resolved (PII re-check added). No violations.

## Resolved Technical Decisions

| Decision | Value | Source |
|----------|-------|--------|
| Handoff contract | Three-artifact handoff (CSV + transform-report + transform-metadata.json) expected from Skill A. Validation checks provenance (`produced_by == "skill_a"`), contract version, snake_case ASCII column names, no all-missing columns, no exact duplicates, consistent types, and missing values resolved or justified. Fallback path if metadata absent. | RQ-001, User Interview Q1 |
| Run ID format | `feature-YYYYMMDD-HHMMSS-XXXX` | User Interview Q2 |
| PII re-check (with metadata) | Read PII flags from Skill A's transform-metadata.json `pii_warnings` field | User Interview Q3 |
| PII re-check (without metadata) | Lightweight column-name heuristic only, no LLM value inspection | User Interview Q3 |
| Personas | 4 total: Feature Relevance Skeptic, Statistical Reviewer, Domain Expert (challenge loop, separate LLM calls) + Data Analyst (post-execution verification) | User Interview Q4 |
| Transformation order | Date/time → text features → aggregations → derived columns → encoding → normalization | User Interview Q5 |
| Aggregation grouping | LLM infers from data; personas challenge | User Interview Q6 |
| File size limits | Input only: >500K cells reject, 100K–500K warn, <100K normal | User Interview Q7 |
| Confidence scores | 0–100 with fixed values matching Skill A's bands: 95 (strong consensus), 82 (minor note), 67 (caveats), 50 (unresolved), 35 (contested). Assigned deterministically by script based on persona outcomes. | User Interview Q8 + Skill A reconciliation |
| Jargon scan | Layer 1: script with ~20 term list. Layer 2: verification persona catches the rest. | User Interview Q9 |
| Column naming | `feat_` prefix on all engineered columns, applied by script | User Interview Q10 |
| Benchmark comparison | Plain-language justification per feature type — what it enables + what you'd lose without it | User Interview Q11 |
| Skill B inputs | Three-artifact handoff expected: cleaned CSV + transform-report.md + transform-metadata.json. Fallback if metadata absent: CSV-only with own PII heuristic. | User Interview Q12 + Skill A reconciliation |
| No-opportunity case | Fast-path for ≤2 columns or all identifiers; standard persona loop for everything else | User Interview Q13 |
| Feature batching | 6 batches by transformation type, each through its own persona loop | User Interview Q7 (revised from A7) |
| Session design | Designed for separate sessions from Skill A; works in same session too | Assumption A1 |
| LLM-generated code | Never executed directly; script uses pre-built code paths; implementation_hint is advisory only | Assumption A4, DM-005 |
| Mistake log | Append-as-you-go markdown file; always shown in outputs | Assumption A15, User Interview |
| Batch rejection cap | Max 5 rejected features per batch before remaining are dropped without retry | Contracts revision |
| Out-of-type proposals | Queued for correct batch, not dropped | Contracts revision |
| Aggregate implementation | `groupby().agg()` + merge pattern for efficiency | RQ-006 |
| Text features (new scope) | Basic: string length, word count, regex patterns. No NLP. | Client brief analysis |
| Aggregate features (new scope) | Group-level metrics mapped to rows via groupby + transform. Industry-standard financial/retail KPIs supported. | Client brief analysis |

## Project Structure

### Documentation (this feature)

```text
specs/003-feature-engineering/
├── plan.md                  # This file
├── research.md              # Phase 0 output — 13 research questions resolved
├── data-model.md            # Phase 1 output — 12 schemas (DM-001 to DM-012)
├── quickstart.md            # Phase 1 output — end-to-end walkthrough
├── contracts/               # Phase 1 output
│   ├── validate-handoff.md
│   ├── scan-pii.md
│   ├── generate-dataset-summary.md
│   ├── propose-features.md
│   ├── challenge-features.md
│   ├── execute-transformations.md
│   ├── verify-output.md
│   ├── scan-jargon.md
│   ├── generate-report.md
│   ├── generate-dictionary.md
│   ├── deliver-outputs.md
│   └── evaluation-suite.md
└── tasks.md                 # Phase 2 output (deferred)
```

### Source Code (repository root)

TBD — pending team alignment. The repo contains `agents/`, `prompts/`, and `skills/` folders. The team needs to confirm:

- Does the documentation structure above match what the PM expects?
- What is inside the `agents/`, `prompts/`, and `skills/` folders?
- Is there an existing convention for where skill source code goes?

This section will be updated after team discussion.

**Structure Decision**: Deferred until team confirms repo conventions.

## Phase Breakdown

### Phase 0 — Research

**Goal:** Resolve all open technical questions that block design.

**Entry criteria:** Constitution check passed. Spec reviewed. Scratch pad complete with user stories, FR ownership, entity relationships, guardrails, and open questions cataloged.

**Process:** 13 user interview questions answered one at a time. 15 assumptions documented and approved.

**Output:** `research.md` — 13 research questions resolved with options, recommendations, and rationale.

**Exit criteria:** All research questions have approved recommendations. No unresolved blockers. Assumptions documented.

**Status:** ✅ Complete.

---

### Phase 1 — Design

**Goal:** Define all data schemas, user-facing walkthrough, pipeline step contracts, and evaluation criteria.

**Entry criteria:** Phase 0 complete. All technical decisions resolved.

**Process:** Section execution protocol — draft → plain-language explanation → reviewer simulation (2 personas) → revision → approval.

**Outputs:**
- `data-model.md` — 12 schemas (DM-001 through DM-012): input validation, dataset summary, feature proposals, persona responses, approved feature tracker, verification result, output CSV, transformation report, data dictionary, mistake log
- `quickstart.md` — end-to-end walkthrough from upload to download, covering happy path, persona challenges, rejections, errors, and edge cases
- `contracts/` — 11 pipeline step contracts + 5-case evaluation suite with 15 synthetic fixture files

**Exit criteria:** All schemas concrete (no placeholders). All contracts define inputs, outputs, logic, and error conditions. Evaluation suite covers handoff validation, full pipeline, PII, no-opportunity, and edge cases.

**Status:** ✅ Complete.

---

### Phase 2 — Tasks

**Goal:** Produce sequenced, independently executable implementation tasks.

**Entry criteria:** Phase 1 complete. All schemas and contracts approved.

**Output:** `tasks.md`

**Status:** ⏳ Deferred — produced via next phase of work.

---

### Phase 3 — Implementation

**Goal:** Build and test the full Skill B pipeline.

**Entry criteria:** Phase 2 complete. Tasks sequenced with dependencies.

**Outputs:**
- All pipeline scripts (validation, PII scan, summary generation, execution, jargon scan, output delivery)
- LLM prompt templates (feature proposal, 3 challenge personas, Data Analyst verification, report generation, dictionary generation)
- 15 synthetic evaluation fixtures
- All 5 evaluation cases executed and passing
- Constitution CSV acceptance tests (NYC TLC, Instacart/Dunnhumby, UCI) — separate end-to-end validation

**Status:** ⏳ Deferred.

## Phase 3 Sequencing Constraints

The following dependency order MUST be enforced when tasks.md is produced in Phase 2. These are hard gates — a later task cannot begin until the earlier task is complete.

**Gate 1 — Handoff contract before everything else:**
```
MUST COMPLETE FIRST:
  - validate-handoff script implemented and tested
  - scan-pii script implemented and tested
  - generate-dataset-summary script implemented and tested
THEN AND ONLY THEN:
  - LLM prompt templates authored
  - Feature proposal and challenge loop tested
```

**Gate 2 — Execution before verification:**
```
MUST COMPLETE FIRST:
  - execute-transformations script implemented with all pre-built
    code paths and edge case handling
  - All transformation methods in the contract table working
THEN AND ONLY THEN:
  - Data Analyst verification prompt authored and tested
  - Jargon scan script implemented
```

**Gate 3 — Evaluation fixtures before end-to-end testing:**
```
MUST COMPLETE FIRST:
  - All 15 synthetic fixture files created
  - All 5 evaluation cases documented with pass criteria
THEN AND ONLY THEN:
  - End-to-end evaluation runs
  - Constitution CSV acceptance tests (NYC TLC, Instacart, UCI)
```

**Gate 4 — All pipeline steps before report/dictionary generation:**
```
MUST COMPLETE FIRST:
  - Full pipeline working end-to-end (validate → propose → challenge
    → execute → verify)
THEN AND ONLY THEN:
  - Report generation prompt and truncation logic
  - Dictionary generation prompt
  - Output delivery script
```

## Items to Flag for Team

| Item | Owner | Action Needed |
|------|-------|---------------|
| Handoff contract — Skill A must produce output meeting the contract defined in RQ-001 | Xiao + Margarida | Review and approve contract; update Skill A spec if needed |
| Synthetic data generation for testing | Team / Margarida | Coordinate as team-level deliverable, not Skill B's responsibility |
| AI vs deterministic rules recommendation | Team / Margarida | Cross-cutting deliverable from client brief; both skill owners contribute findings |
| Constitution amendment: pip install permitted | Margarida | Formalize the amendment Xiao's chat established |
| ydata-profiling in approved dependency list | Margarida | Resolve inconsistency: constitution lists it, project overview does not |
| Source code repo structure | Team | Confirm conventions for agents/, prompts/, skills/ folders |

## Complexity Tracking

No constitution violations identified. No justifications required.

One spec gap was identified and resolved:
| Gap | Resolution |
|-----|-----------|
| Skill B spec did not include PII re-check | Added as new scope: reads PII flags from Skill A's transform-metadata.json if available, runs column-name heuristic if not. To be added to spec in next revision. |

Two new scope items added from client brief analysis:
| Addition | Resolution |
|----------|-----------|
| Basic text feature extraction (string length, word count, regex) | Added to Batch 2 in proposal/execution pipeline. Within pandas capabilities. |
| Aggregate metrics as row-level columns (industry-standard financial/retail KPIs) | Added to Batch 3. Uses groupby().agg() + merge. Standard pandas pattern. |

---

## Delivered — Phase 0 + Phase 1

| Artifact | Status |
|----------|--------|
| Scratch pad v1.0 (user stories, FRs, entities, guardrails, open questions) | ✅ Complete |
| User interview — 13 questions resolved | ✅ Complete |
| Assumptions — 15 documented and approved | ✅ Complete |
| research.md — 13 research questions | ✅ Complete |
| data-model.md — 12 schemas (DM-001 to DM-012) | ✅ Complete |
| quickstart.md — end-to-end walkthrough | ✅ Complete |
| contracts/validate-handoff.md | ✅ Complete |
| contracts/scan-pii.md | ✅ Complete |
| contracts/generate-dataset-summary.md | ✅ Complete |
| contracts/propose-features.md | ✅ Complete |
| contracts/challenge-features.md | ✅ Complete |
| contracts/execute-transformations.md | ✅ Complete |
| contracts/verify-output.md | ✅ Complete |
| contracts/scan-jargon.md | ✅ Complete |
| contracts/generate-report.md | ✅ Complete |
| contracts/generate-dictionary.md | ✅ Complete |
| contracts/deliver-outputs.md | ✅ Complete |
| contracts/evaluation-suite.md — 5 evaluations, 15 fixtures | ✅ Complete |

## Deferred — Phase 2 + Phase 3

| Artifact | Phase | Notes |
|----------|-------|-------|
| tasks.md — sequenced implementation tasks | Phase 2 | Next step |
| Pipeline scripts (validation, PII, summary, execution, jargon, delivery) | Phase 3 | Contracts complete; implementation TBD |
| LLM prompt templates (proposal, 3 personas, verification, report, dictionary) | Phase 3 | Persona system prompts drafted in contracts; full templates TBD |
| 15 synthetic evaluation fixtures | Phase 3 | Fixture specs defined; content TBD |
| End-to-end evaluation runs | Phase 3 | Pass criteria defined; execution TBD |
| Constitution CSV acceptance tests (NYC TLC, Instacart, UCI) | Phase 3 | Separate from unit evaluations |
| Skill B spec update — add PII re-check, text features, aggregate scope | Phase 3 | Spec gaps documented; formal update TBD |

---

**Governed by**: [constitution.md](./constitution.md) v1.1.0
