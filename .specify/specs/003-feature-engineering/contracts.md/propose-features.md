# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

### Contract: propose_features
**FR(s):** FR-203, FR-204, FR-225 | **Owner:** LLM | **Freedom:** High | **Runtime:** LLM-executed

### Purpose
For each batch type, the LLM analyzes the dataset summary and proposes feature engineering transformations. Each proposal includes a justification and benchmark comparison. Produces a feature proposal batch (DM-005) consumed by the persona challenge loop. Called once per active batch (up to 6 times).

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_summary | dict | DM-004 | Yes |
| batch_type | string | Pipeline orchestration | Yes |
| approved_features_so_far | list | DM-007 (running tracker) | Yes (may be empty for Batch 1) |
| validation_result | dict | DM-003 | Yes |

### Outputs

Returns `feature_proposal_batch` dict (DM-005 schema).

Console output:
```
📋 Batch {n}: {Batch Type Name}
   Analyzing {relevant column type} columns...

   Proposed features:
   1. {name} — from '{source}' — {brief benchmark}
   2. {name} — from '{source}' — {brief benchmark}
   ...
```

If batch is skipped:
```
📋 Batch {n}: {Batch Type Name}
   ℹ️ Skipped — {reason}.
```

### LLM Prompt Constraints

The LLM system prompt must include:

- **Batch focus:** "You are proposing features of type: {batch_type} only. Do not propose features outside this type."
- **Context awareness:** "These features have already been approved in previous batches: {approved_features_so_far}. You may reference them but do not re-propose them."
- **Benchmark required:** "Every proposed feature must include a benchmark comparison: why it adds analytical value and what you'd lose without it."
- **Implementation hint:** "Include an implementation_hint for each feature. This is advisory only — the execution script will use its own tested code, not your hint."
- **PII awareness:** "These columns are flagged for PII: {pii_flags}. Note PII-flagged columns in your proposals. The Domain Expert persona will challenge features derived from PII columns."
- **Aggregate cap:** "For aggregation batches: propose a maximum of 10 features. If more are possible, propose the top 10 by expected value and note the remainder."
- **No-opportunity handling (FR-225):** "If no features of this type are possible, return an empty proposal with a skipped_reason explaining why."

### Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to produce a structured proposal | Retry once. If second attempt fails: "Feature proposal failed for Batch {n}. Skipping this batch." |
| LLM proposes features outside the batch type | Caught by pipeline script — out-of-type features are queued for the correct batch (e.g., an encoding suggestion in Batch 3 is queued for Batch 5) with a warning logged |

### Dependencies

- LLM (Claude 4.5 Sonnet)

---

## contracts/challenge-features.md

### Contract: challenge_features
**FR(s):** FR-205, FR-206, FR-207 | **Owner:** LLM | **Freedom:** Medium | **Runtime:** LLM-executed

### Purpose
Three separate LLM calls — one per challenge persona — review the proposed feature batch. Each persona has a narrow checklist and returns a structured response (DM-006). The pipeline script aggregates responses, determines approvals/rejections, and assigns confidence scores (DM-007). On rejection, the LLM proposes an alternative (max 2 rejection cycles per feature).

### Inputs (per persona call)

| Input | Type | Source | Required |
|-------|------|--------|----------|
| feature_proposal_batch | dict | DM-005 | Yes |
| dataset_summary | dict | DM-004 | Yes |
| persona_type | string | Pipeline orchestration | Yes |

### Outputs

Each persona returns a `persona_challenge_response` dict (DM-006 schema).

Console output (per persona):
```
🔎 {Persona Name}: {summary of review}
```

Console output (batch summary):
```
✅ Batch {n} complete: {approved} features approved, {rejected} rejected
   (confidence: {scores})
```

### Persona System Prompts

**Feature Relevance Skeptic:**
```
You are a Feature Relevance Skeptic. Your job is to identify redundant
or low-value features. For each proposed feature, ask:
- Is this feature redundant with an existing column? Check if it would
  be >0.95 correlated with any existing or previously approved feature.
- Does it add information beyond what's already available?
- Would removing it meaningfully reduce analytical capability?

Return your review in this exact JSON format:
{DM-006 schema}
```

**Statistical Reviewer:**
```
You are a Statistical Reviewer. Your job is to verify that proposed
methods are valid for the actual data. For each proposed feature, ask:
- Is the transformation method appropriate for this column's dtype
  and distribution?
- Will this produce valid results? (e.g., normalizing a zero-variance
  column, one-hot encoding 500 categories, scaling with extreme outliers)
- Are there edge cases that would produce NaN, infinity, or errors?

Return your review in this exact JSON format:
{DM-006 schema}
```

**Domain Expert:**
```
You are a Domain Expert. Your job is to evaluate whether proposed
features make business sense. For each proposed feature, ask:
- Would a data scientist working with this type of data actually use this?
- Does the grouping key / aggregation / ratio make real-world sense?
- Could the feature be misleading? (e.g., a ratio where the denominator
  is frequently zero)
- Is the benchmark comparison convincing?

Return your review in this exact JSON format:
{DM-006 schema}
```

### Rejection Cycle Logic

```
For each rejected feature:
  Cycle 1: LLM proposes alternative → 3 personas review
    → If approved: record with confidence score
    → If rejected again:
  Cycle 2: LLM proposes second alternative → 3 personas review
    → If approved: record with confidence score
    → If rejected again: feature dropped, logged in mistake log
```

Maximum: 2 rejection cycles per feature. Maximum additional LLM calls per rejected feature: 2 (proposal) + 6 (3 personas × 2 cycles) = 8.

**Batch-level rejection cap:** If more than 5 features in a single batch are rejected, the remaining rejected features are dropped without retry and logged in the mistake log. This prevents runaway LLM calls on batches where the proposals are fundamentally misaligned with the data.

### Confidence Score Assignment (Deterministic)

After all three personas respond, the pipeline script counts challenges and assigns a fixed value matching Skill A's bands:

| Condition | Score | Band |
|-----------|-------|------|
| 0 challenges raised across all 3 personas | 95 | High |
| Challenges raised, all resolved, no caveats | 82 | High |
| Challenges raised, all resolved, with caveats | 67 | Medium |
| Challenges raised, not all resolved | 50 | Medium |
| Original rejected, alternative adopted | 35 | Low |

### Error Conditions

| Condition | Message |
|-----------|---------|
| Persona fails to return structured response | Retry once. If fails again: treat as "approved with no challenges" and log warning. |
| All three personas reject and no alternative found after 2 cycles | Feature dropped. Logged in mistake log. |

### Dependencies

- LLM (Claude 4.5 Sonnet)

---
