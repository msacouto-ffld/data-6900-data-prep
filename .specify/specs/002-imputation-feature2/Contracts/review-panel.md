# Contract: review_panel

**FR(s)**: FR-103 (Read), FR-104, FR-105, FR-111, FR-122 | **Owner**: LLM | **Freedom**: High | **Runtime**: LLM-executed

---

## Purpose

The review panel evaluates the proposed transformation plan from multiple perspectives (Conservative, Business, Technical), producing verdicts, confidence scores, and alternatives for rejected transformations. This is the validation step of the Verification Ritual.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| transformation_plan | dict | DM-104 — from propose_transformations | Yes |
| profiling_data | dict | DM-101 JSON (parsed) | Yes |

## Outputs

Returns `review_output` (DM-105 schema).

Console output (condensed — all-approved steps as single line, expanded for medium/low confidence or rejections):

```
🔎 Review panel evaluating proposed transformations...

{Per-step results}

All transformations approved. Proceeding to execution.
```

## LLM System Prompt

The full multi-perspective prompt from RQ-003, including:

- Three perspectives: Conservative View, Business View, Technical View
- Fixed confidence score table:
  - Unanimous approval, catalog strategy: 95
  - Unanimous approval, custom strategy: 82
  - Majority approval with minor dissent: 67
  - Significant dissent but consensus reached: 50
  - No consensus: 35
- Structured output format (DM-105)

## Rejection Loop

1. If any transformation has `verdict: REJECT`:
   a. Collect rejected transformations
   b. Send back to propose_transformations with rejection reasoning as `rejection_context`
   c. LLM proposes alternatives (guided by the review panel's suggested alternative)
   d. Re-run review panel on revised proposals only
   e. Maximum 2 rejection loops per step
   f. After 2 loops, if still rejected → score set to 35 → human review escalation

## Human Review Escalation (FR-122)

If `confidence_score == 35`:

1. Build escalation object (DM-113) with column context
2. Present options to user inline (see quickstart Step 4)
3. Wait for user response
4. User types number → adopt that strategy
5. User types "skip" → record as skipped; check dependency warnings
6. User types guidance → re-run propose + review with guidance as context; if still no consensus, adopt highest-scoring option with note: "Adopted based on user guidance; review panel dissent noted."
7. Record decision in DM-106 `human_review_decisions` and mistake log

## Error Conditions

| Condition | Message |
|-----------|---------|
| LLM fails to produce valid JSON | Retry once; if still invalid, halt: "Review panel failed. Please try again." |
| Max rejection loops exceeded | Score set to 35; human review escalation triggered |

## Dependencies

- LLM (Claude 4.5 Sonnet)
