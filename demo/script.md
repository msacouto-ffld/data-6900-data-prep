# Demo Skeleton — 10 Minutes

**Dataset:** UCI Default of Credit Card Clients — first 300 rows, lightly messed up
**Comparison:** Logistic regression, with vs. without the skill
**Theme:** Speed-to-ready + democratization — anyone can be a better analyst with better data

---

## [0:00 – 0:25] PM — Hook

*Walk to front. Pause. Eye contact: left, center, right. Don't look at the laptop.*

The *NYT* reported in 2014: data scientists spend 50–80% of their time cleaning data, not analyzing it. Four days out of every five, your most expensive hire is fixing date formats and chasing down what a question mark in column twelve is supposed to mean.

That's the problem we solved. Two skills that take the four-day part — and do it in minutes.

---

## [0:25 – 1:00] PM — Why this room cares + the bigger idea

The obvious value: speed. Cleaning happens in minutes instead of days, with every decision on the record.

**The less obvious value — and the one we want you to leave with:** when the cleaning bottleneck disappears, *who* can do data analysis changes. A junior analyst with our skill produces work that used to require a senior data scientist. A business analyst who's never written cleaning code can ship a model. **Anyone can become a better data analyst — they just need access to better data.**

We'll show the same dataset processed two ways: rushed manual cleaning vs. our skill. Then logistic regression on both, and you decide whether speed costs quality.

Pairs with **[Team X]** upstream and **[Team Y]** downstream — **[PLACEHOLDER]**.

→ Hand to A-Owner by name.

---

## [1:00 – 4:30] Skill A — Profiling & Cleaning (A-Owner)

### Show the input (1:00 – 1:25)

- 300 clients from a Taiwanese bank, predicting next-month default
- Three problems to call out: column names stripped to X1–X23, question marks as masked nulls, sensitive demographics (sex, education, marriage, age)
- "This is what real data looks like on day one."

### Without the skill — pre-run (1:25 – 2:10)

- Show the rushed notebook: read CSV, describe, drop missing, move on
- What's missing: no record of the question marks, no demographic flags, no documentation of why rows were dropped
- **Closing beat:** "Even this rushed version takes most analysts the better part of a day. A day of an expensive person's time, with no documentation to show for it."

### With the skill — pre-run (2:10 – 3:30)

Walk through the four artifacts:

1. **Profile HTML** — every column, every distribution, every quality issue auto-detected (mention the question-mark-as-null catch)
2. **Transform report** — pick one transformation in advance, narrate the three personas (conservative, business, technical), confidence score visible
3. **Transform metadata JSON** — machine-readable handoff to Skill B, carries PII flags forward
4. **Mistake log** — what the pipeline couldn't auto-resolve, surfaced for human review

### Ground truth (3:30 – 4:20)

- Compared against original Yeh & Lien 2009 dataset
- Side-by-side table: row count, null counts, dtypes — all match
- **Closing beat:** "Identical structural cleaning to what a domain expert would do by hand. [X] minutes. Full audit trail. That's the core of what this skill delivers."

### Handoff to B-Owner (4:20 – 4:30)

"Cleaned CSV is structurally identical to the published version, with a documented reason for every change. Now the question is whether that cleaning matters when you train a model. [B-Owner] will show you."

---

## [4:30 – 8:30] Skill B — Feature Engineering (B-Owner)

### Pick up cleanly (4:30 – 4:45)

"Same dataset, picking up from the cleaned output. The job now is feature engineering — turning columns into signals a model can actually learn from."

### Without the skill — pre-run (4:45 – 5:15)

- Same junior analyst, same hurry. One-hot the categoricals, scale the numerics, done.
- No interactions, no ratios, no reasoning about what predicts default
- "Ready to train. Move on."

### With the skill — pre-run (5:15 – 6:30)

- Six batches: date, text, aggregate, derived, encoding, scaling
- Three personas challenge every proposal before execution
- **Walk through one feature in detail:** `feat_bill_to_limit_ratio` (utilization)
  - Skeptic: redundant with raw bill amount?
  - Statistical reviewer: division by zero?
  - Domain expert: utilization beats either component alone in credit risk
  - Both concerns resolved, confidence 67, medium band — transparent in the report
- **Data dictionary:** every feature self-documenting — name, source, method, range, missing-value handling

### Model comparison — PM takes over (6:30 – 8:00)

Show the pre-built table:

| Logistic Regression | Accuracy | F1 | AUC |
|:--------------------|:--------:|:--:|:---:|
| Without skill | [X] | [X] | [X] |
| With skill | [X] | [X] | [X] |
| Yeh & Lien benchmark (full 30K) | [X] | [X] | [X] |

Read it out loud. Don't assume they can see it.

- Same model, same split, same seed. Only the features changed.
- Lift from [X] to [Y] — features had to do all the work because logistic can only learn linear relationships
- **Honest scope caveat:** 300 rows is small, benchmark used 30K. Not claiming to match the benchmark — showing the lift the skill provides on a fixed dataset. Same data in, better features out, better model.
- **Time bookend:** "And we got there in minutes, not days. The speed isn't a trade-off against quality — it's the result of removing the human bottleneck."

### B-Owner closing (8:00 – 8:30)

**The democratization beat — say this clearly:**

"Here's what we want you to take from this. The skill doesn't beat a senior data scientist. What it does is change *who* can produce senior-quality data work.

A junior analyst with this skill ships a model that holds up to scrutiny. A business analyst who's never written cleaning code can hand off something a data science team will actually trust. The bottleneck isn't talent — it's access to clean, documented data. Remove that bottleneck, and your whole organization gets better at this."

---

## [8:30 – 9:00] PM — Wrap and Q&A

*Step back to center.*

Two skills, one chained pipeline. Raw CSV in, model-ready features out, every decision on the record. Faster. Auditable. **And accessible to anyone who needs to work with data, not just the specialists.**

If you've ever wished more of your team could do this kind of work — that's what we built.

*[pause — eye contact]*

We'd love to explore how this could work in your organization. Happy to take your questions.

*Stop talking. Wait.*

---

## What Each Person Memorizes

| Person | Must memorize |
|:-------|:--------------|
| **PM** | The hook (first 25 sec), the "anyone can be a better analyst" beat (in framing AND in close), the model comparison narration with time bookend |
| **A-Owner** | The three input issues, the one transformation you'll narrate, the "day of an expensive person's time" line, the handoff |
| **B-Owner** | The one feature you'll narrate, the democratization closing beat (8:00–8:30) — this is one of the two moments people will remember |

---

## Pre-Demo Setup Checklist

- [ ] Build messy CSV (300 rows, X1–X23 names, ~5% question-mark nulls, light categorical inconsistency)
- [ ] Pre-run Skill A, save all four artifacts, bookmark the one transformation
- [ ] Pre-run Skill B, confirm `feat_bill_to_limit_ratio` (or chosen feature) was approved
- [ ] Train both logistic regressions: same 80/20 split, seed 42, record acc/F1/AUC
- [ ] Look up Yeh & Lien benchmark numbers
- [ ] Build the comparison table as a static PNG slide
- [ ] Time the actual Skill A run — replace "[X] minutes" in the script with the real number
- [ ] Screenshot every artifact for backup
- [ ] Fill in [Team X] and [Team Y] placeholders
- [ ] Three full timed rehearsals minimum

---
