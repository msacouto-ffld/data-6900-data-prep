# Feature Engineering with Persona Validation — Phase 1 Contracts

**Date**: 2026-04-06 | **Spec**: Feature 003 — Feature Engineering | **Status**: Draft

---

### Contract: generate_report
**FR(s):** FR-215, FR-216 | **Owner:** LLM | **Freedom:** High | **Runtime:** LLM-executed

### Purpose
Produces the feature engineering transformation report (DM-010) — a self-contained markdown document that a data scientist, stakeholder, or client can read and understand without access to the pipeline code, the cleaned CSV, or Skill A's outputs. Every transformation is documented with the mandatory 3-part justification (What → Why → Impact), persona review outcomes, and confidence score. Rejected features are documented alongside approved ones.

### Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| approved_features | list[dict] | DM-007 (final state after all batches) | Yes |
| rejected_features | list[dict] | DM-007 (running rejection tracker) | Yes |
| verification_result | dict | DM-008 | Yes |
| validation_result | dict | DM-003 | Yes |
| dataset_summary | dict | DM-004 | Yes |
| skipped_batches | list[dict] | Pipeline orchestration | Yes |

### Outputs

Returns a `transformation_report` markdown string (DM-010 schema). Written to `{run_id}-transformation-report.md` in Stage 11.

Console output:
```
📝 Generating transformation report...
✅ Report generated: {n} transformations documented, {r} rejections logged.
   Chat view: {truncated | full}
   Download: full ({chars:,} chars)
```

### Required Report Sections (in order)

Every report must contain these sections:

1. **Header** — Run ID, Source Transform Run ID (from Skill A), Input/Output shape, count of new features
2. **Executive Summary** — 2–4 sentences: what was engineered, how many features, any key caveats
3. **Before / After** — table showing row count, column count, features added, features rejected, batches active
4. **Transformations Applied** — one subsection per batch, with nested feature entries (see template below)
5. **Verification Summary** — 9-row table from DM-008 with pass/fail/warning per check and expanded discussion of any warnings
6. **Persona Rejections — Full Record** — table of all rejected features with the persona that rejected them and reason
7. **Handoff Contract Findings** (optional) — only included when validation_result contains warnings worth surfacing to the Skill A team

### Per-Feature Template (Mandatory)

Every approved feature must be documented using this exact 3-part structure:

```markdown
#### `feat_{feature_name}`
- **What**: {one-sentence description of what the transformation does to the data, no jargon}
- **Why**: {one-sentence justification — what analytical value this adds and what would be lost without it}
- **Impact**: {dtype, range, NaN handling, any edge cases triggered during execution}
- **Method**: {transformation_method name from the execute-transformations table}
- **Source**: {column or columns it was derived from}
- **Benchmark**: {from the original proposal — what comparison case this feature wins against}
- **Persona review**: {0 challenges | N challenge(s) resolved | N challenge(s) with caveats}
- **Confidence**: **{95 | 82 | 67 | 50 | 35} ({High | Medium | Low})**
```

### Per-Batch Structure

Each of the 6 batch types gets its own `### Batch N — {Name}` heading. If a batch was skipped, a one-paragraph `**Skipped**.` entry replaces the feature list, stating why (no applicable columns, all proposals rejected, etc.).

### Rejections Documentation

Rejected features are documented in TWO places:

1. **Inline at the end of the relevant batch** — a short list:
   ```
   **Rejected in Batch {n}**:
   - {feature_name} — {persona that rejected} rejected: {reason}
   ```
2. **Consolidated in the "Persona Rejections — Full Record" section** — a table across all batches.

This duplication is intentional — readers skimming a single batch should see its rejections; readers auditing the pipeline should see all rejections in one place.

### Truncation Rule

If the total number of features (approved + rejected) exceeds **10**:

- **Inline/chat version**: summary table of all features (name, batch, confidence, status) followed by full detail for the top 5 by confidence only.
- **Downloadable version** (the file written to disk): always full detail for every feature.

The LLM receives a `output_mode` parameter set to `"chat"` or `"download"` to control this. Both versions are generated in a single LLM call and differ only in truncation; the full version is always the source of truth.

### LLM Prompt Constraints

**System prompt:**
```
You are generating a feature engineering transformation report that
will be read by a data scientist and may be shared with non-technical
stakeholders. Follow these rules strictly:

1. Use the 3-part justification (What → Why → Impact) for every feature.
   This is non-negotiable — it's the report's core structural promise.

2. Include the benchmark from the original proposal verbatim or near-verbatim.
   Do not invent new justifications.

3. Document persona challenges faithfully:
   - If a persona raised a challenge that was resolved, say so.
   - If a challenge was resolved with a caveat, state the caveat in the
     feature's Impact section.
   - Do not downplay legitimate concerns — caveats are features, not bugs.

4. Privacy: NEVER include raw data values from the dataset. You may
   reference column names, aggregate descriptions ("8 distinct series"),
   and ranges ("values between 0 and 729"), but no row-level content.

5. No jargon without explanation. The Stage 8 jargon scan will catch
   misses, but aim to write in plain language first.

6. Match the section order and structure in the template exactly.
```

### Guardrails

- **No raw data values**: applies to every section. Use column names, counts, ranges, and aggregate descriptions. Sample values from DM-004 are for LLM context only and must not appear in the output.
- **No invented features**: the LLM documents what was actually approved and executed (per DM-007). It does not add features that didn't go through the persona loop.
- **Confidence scores are fixed values**: the LLM does not invent a score. It reads the score from DM-007 and labels the band (High/Medium/Low) based on the DM-007 table.
- **Verification results are authoritative**: the LLM reports the verification checklist faithfully from DM-008. It does not interpret a hard-gate fail as a warning or vice versa.
- **Rejected features must be documented**: a report that omits rejections is a contract violation. The Skill B pipeline explicitly wants rejection transparency — this is the audit trail.

### Error Conditions

| Condition | Message |
|-----------|---------|
| LLM returns a report missing a required section | "Report structure incomplete — {section} missing. Regenerating with explicit section list." Retry once with a stricter prompt listing required sections. |
| LLM includes raw data values | Caught by a post-generation regex check against sample values from DM-004. Redact and log a `verification_correction` event. |
| LLM invents a feature not in approved_features | Caught by post-generation validation against DM-007. Offending content removed; LLM call retried once. |
| Report exceeds 20,000 characters | Warning only — likely indicates verbose LLM output. Delivery still proceeds. |

### Dependencies

- LLM (Claude 4.5 Sonnet)
- re — standard library (post-generation redaction check)
