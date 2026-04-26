# Demo Script — 10 Minutes (with Full Voiceover)

**Dataset:** UCI Default of Credit Card Clients — first 300 rows, with artificial messiness introduced
**Comparison:** Logistic regression, with vs. without the skill
**Theme:** Speed-to-ready + democratization — anyone can be a better analyst with better data

**How to use this document:**
The voiceover is written to be spoken, not read. Memorize the beats, not the words. Stage directions are in *italics*. Pauses are marked `[pause]`. Numbers in `[brackets]` need to be filled in from your dress rehearsal.

---

## [0:00 – 0:25] PM — Hook

*Walk to front. Pause. Eye contact: left, center, right. Don't look at the laptop.*

> "There's a number anyone who's worked with data has heard. The *New York Times* reported it back in 2014: data scientists spend somewhere between fifty and eighty percent of their time cleaning data — not analyzing it.
>
> *[pause]*
>
> Think about what that means. Four days out of every five, your most expensive hire is fixing date formats and chasing down what a question mark in column twelve is supposed to mean.
>
> *[pause]*
>
> That's the problem we solved. Two skills that take the four-day part — and do it in minutes."

---

## [0:25 – 1:00] PM — Why this room cares + the bigger idea

> "The obvious value is speed. Cleaning that used to take days happens in minutes, with every decision on the record.
>
> But here's the less obvious value, and the one we want you to leave the room with. When the cleaning bottleneck disappears, *who* can do data analysis changes. A junior analyst with our skill produces work that used to require a senior data scientist. A business analyst who's never written cleaning code can ship a model.
>
> *[slow down for this line — it's the thesis]*
>
> Anyone can become a better data analyst. They just need access to better data.
>
> Here's how we'll show you. Same dataset, processed two ways: once the way it usually gets done in a hurry, once with our skill. Then we put both into a logistic regression and you decide whether speed costs quality."

> "We're one of three teams presenting a piece of a larger story today. Group A built an evaluation framework that scores AI-generated SQL and Python code across a 200-task benchmark — the kind of framework you'd use to decide which model to trust for analytics work in the first place. Group C built a documentation skillset for Synchrony — turning data artifacts into audit-ready data dictionaries and control narratives that compliance teams sign off on.
>
> Our work sits in the middle. Group A tells you which model to trust. We turn raw, messy data into something that model can actually work with. Group C turns the result into documentation a regulator will accept. Three skills, one pipeline from model selection to audit-ready output."

*Turn slightly toward A-Owner.*

> "[A-Owner's name] is going to start us with profiling and cleaning. [Name]?"

---

## [1:00 – 4:30] Skill A — Profiling & Cleaning (A-Owner)

### Show the input (1:00 – 1:25)

*Open the raw CSV in a viewer with a font size the back of the room can read. Don't open it in tiny terminal text.*

> "This is the UCI Default of Credit Card Clients dataset — three hundred clients from a bank in Taiwan. Twenty-four columns. Demographics, six months of payment history, six months of billing, and a target column: did this person default on next month's payment, yes or no."

*Point at the screen as you call out specific issues.*

> "Notice three things. First — the column names are X1, X2, X3, all the way to X23. Whoever exported this stripped the meaningful names. Second — there are missing values coded as a question mark, not as a null. Pandas won't catch that automatically. Third — there are columns here for sex, education, marital status, and age. Those are sensitive demographics. Any model touching this needs to handle them deliberately.
>
> This is what real data looks like on day one of a project."

### Without the skill — pre-run (1:25 – 2:10)

*Switch to a pre-saved short notebook on screen. The "junior analyst in a hurry" version.*

> "Here's what most people do in the first hour. Read the CSV. Run `describe`. Drop the rows with missing values. Move on."

*Scroll through the script — five or six lines.*

> "It runs. You get a clean dataframe. But watch what's missing."

*Click to the cleaned output.*

> "There's no record that the question marks were ever there. There's no flag on the demographic columns. Nobody documented why we chose to drop rows instead of impute.
>
> *[pause]*
>
> And here's the thing — even this rushed version takes most analysts the better part of a day. A day of an expensive person's time, with no documentation to show for it.
>
> Now watch what our skill does with the same input."

### With the skill — pre-run (2:10 – 3:30)

*Switch to the pre-recorded skill output. The full pipeline runs seventeen stages — too long to run live. Show the artifacts.*

> "The skill runs seventeen stages — nine for profiling, eight for cleaning. I'm going to skip past the mechanics and show you the four things it produces."

*Open the profile HTML report.*

> "First: a profiling report. Every column, every distribution, every quality issue, automatically detected.
>
> *[scroll to the question-mark detection]*
>
> Look at this — the pipeline flagged the question marks as masked nulls. That's the kind of thing a junior analyst misses on a Friday afternoon, and the audit catches six months later."

*Open the transform report markdown. Pre-bookmarked to one specific transformation — pick this in rehearsal. Recommend the canonical mapping on `EDUCATION` or the imputation decision on a payment-history column.*

> "Second: the transformation report. This is the part I want you to look at."

*Pause on the chosen transformation.*

> "For every change the pipeline made, you get three things: what it did, why it did it, and what the impact was. Three personas reviewed the proposal — a conservative reviewer, a business reviewer, and a technical reviewer — and the report shows you their confidence score on a deterministic scale: ninety-five if there were zero objections, eighty-two if everything was resolved, sixty-seven if there were caveats, and so on down to thirty-five if the proposal had to be rejected and an alternative adopted.
>
> This isn't a black box. Every decision is on the record."

*Open the transform metadata JSON briefly.*

> "Third: a machine-readable handoff file. This is what feeds into [B-Owner's name]'s skill in a minute. It carries the PII flags forward — so when the next stage starts engineering features, it already knows which columns are sensitive."

*Open the mistake log.*

> "And fourth: a mistake log. Anything the pipeline flagged but couldn't auto-resolve gets logged here for human review. We're not pretending the system is perfect — we're being honest about its limits."

### Ground truth comparison (3:30 – 4:20)

*Show a side-by-side comparison table — pre-built, on screen.*

> "We compared the skill's cleaned output against the original dataset published by Yeh and Lien in 2009 — the version data scientists have been training on for fifteen years. That's our ground truth."

*Read the table aloud, point at each row.*

> "Row count: matches. Null counts: match. Data types: match.
>
> *[pause]*
>
> Identical structural cleaning to what a domain expert would do by hand. **[X] minutes.** Full audit trail. That's the core of what this skill delivers."

### Handoff to B-Owner (4:20 – 4:30)

*Turn toward B-Owner.*

> "So that's the cleaned CSV — structurally identical to the published version, with a documented reason for every change. Now the question is: does that cleaning actually matter when you train a model on it? [B-Owner's name] will show you."

---

## [4:30 – 8:30] Skill B — Feature Engineering (B-Owner)

### Pick up cleanly (4:30 – 4:45)

> "Thanks, [A-Owner's name]. Same dataset, picking up from the cleaned output you just saw. The job now is feature engineering — turning columns into signals a model can actually learn from."

### Without the skill — pre-run (4:45 – 5:15)

*Show a short notebook again — the baseline approach.*

> "Same junior analyst, same hurry. They one-hot encode the categoricals, scale the numerics, and call it a day. No interaction terms. No ratios. No reasoning about which features actually matter for predicting default."

*Show the resulting feature set briefly.*

> "Ready to train. Move on.
>
> *[pause]*
>
> Now watch the skill."

### With the skill — pre-run (5:15 – 6:30)

*Switch to the pre-recorded skill output.*

> "Our skill works in six batches in order — date-time extraction, text features, aggregates, derived ratios, categorical encoding, and scaling. For every proposed feature in every batch, three personas challenge it before it gets executed: a feature relevance skeptic, a statistical reviewer, and a domain expert."

*Open the transformation report. Pre-bookmarked to one specific feature — recommend `feat_bill_to_limit_ratio` (BILL_AMT1 / LIMIT_BAL).*

> "Here's a feature the skill proposed in batch four — derived columns. Bill amount divided by credit limit. How much of their available credit is this person actually using.
>
> The relevance skeptic challenged it — said it might be redundant with the raw bill amount column. The statistical reviewer challenged it — said division by zero is a real risk if anyone has a zero credit limit. The domain expert approved it — said in credit risk, utilization ratio is a stronger predictor of default than either component alone.
>
> The skill resolved both concerns. The redundancy was logged as acceptable given the predictive lift, and the division-by-zero was handled by mapping to NaN automatically.
>
> *[point at the confidence score]*
>
> Confidence score: sixty-seven. Medium band. Why? Because there were challenges raised, all of them resolved, but with caveats. The report tells you that, transparently. You can see the reasoning."

*Open the data dictionary.*

> "And every engineered feature shows up in the data dictionary — name, description, source columns, method used, value range, what to do with missing values. A new analyst inheriting this project tomorrow can read this dictionary and understand every feature without ever talking to us. Every column the skill creates gets a `feat_` prefix, so you can pull just the engineered features with a one-line filter."

### Model comparison — PM takes over (6:30 – 8:00)

*B-Owner steps slightly aside. PM steps to the screen.*

> "This is the part the room came to see."

*Show a single, large, readable comparison table on screen. Pre-computed.*

| Logistic Regression | Accuracy | F1 | AUC |
|:--------------------|:--------:|:--:|:---:|
| Without skill (baseline features) | [X] | [X] | [X] |
| With skill (engineered features) | [X] | [X] | [X] |
| Yeh & Lien benchmark (full 30K rows) | [X] | [X] | [X] |

*Read the table out loud. Don't assume they can see it.*

> "We trained logistic regression on both feature sets — the rushed baseline, and the skill's engineered version. Same model, same train-test split, same random seed. The only thing that changed was the features going in.
>
> Without the skill: **[X]** accuracy, **[Y]** AUC. With the skill: **[X]** accuracy, **[Y]** AUC. That's a **[Z]**-point lift on a model that, by design, can only learn linear relationships — which means the features had to do all the work."

*Honest scope caveat — say it directly.*

> "I want to be straight with you about scope. Three hundred rows is a small sample, and the published benchmark you see in the third row was trained on thirty thousand. We're not claiming to match the benchmark — we're showing you the lift the skill provides on a fixed dataset. Same data in, better features out, better model."

*Pause. One beat.*

> "And we got there in minutes, not days. The speed isn't a trade-off against quality — it's the result of removing the human bottleneck."

### B-Owner closing — the democratization beat (8:00 – 8:30)

*B-Owner steps back to center.*

> "Here's what we want you to take from this.
>
> *[slow down — this is the second of the two memorable lines]*
>
> The skill doesn't beat a senior data scientist. What it does is change *who* can produce senior-quality data work.
>
> A junior analyst with this skill ships a model that holds up to scrutiny. A business analyst who's never written cleaning code can hand off something a data science team will actually trust. The bottleneck isn't talent — it's access to clean, documented data. Remove that bottleneck, and your whole organization gets better at this."

---

## [8:30 – 9:00] PM — Wrap and transition to Q&A

*PM steps back to center.*

> "That's the demo. Two skills, one chained pipeline. Raw CSV in, model-ready features out, every decision on the record. Faster. Auditable. And accessible to anyone who needs to work with data, not just the specialists.
>
> If you've ever wished more of your team could do this kind of work — that's what we built."

*[pause — eye contact with the room]*

> "We'd love to explore how this could work in your organization. We're happy to take your questions."

*Stop talking. Don't fill the silence. Look up at the room and wait.*

---

## What Each Person Memorizes

| Person | Must memorize |
|:-------|:--------------|
| **PM** | The hook (first 25 sec), the "anyone can be a better analyst" thesis (in framing AND in close), the model comparison narration with the time bookend |
| **A-Owner** | The three input issues, the one transformation you'll narrate, the "day of an expensive person's time" line, the handoff to B-Owner |
| **B-Owner** | The one feature you'll narrate (with all three persona reactions), the democratization closing beat — this is one of the two moments people will remember |

---

## Cuts If You Run Long

If the dress rehearsal shows you're over 10 minutes, cut in this order:

1. **Drop the data dictionary mention** in Skill B (saves ~15 sec) — it's in the HANDOFF anyway.
2. **Shorten the "without skill" segments** to 30 sec each (saves ~30 sec total) — the contrast is the point, not the detail.
3. **Cut the mistake log mention** in Skill A (saves ~15 sec) — keep the other three artifacts.

Do NOT cut the hook, the model comparison table, or the democratization closing beat. Those are the three moments people will remember.

---

## What to Pre-Run vs Live

| Segment | Decision | Why |
|:--------|:---------|:----|
| Skill A — Without | Pre-run, show artifact | Trivial; just show the result |
| Skill A — With (17 stages) | **Pre-run** | Full pipeline > 2 min, ydata-profiling alone is slow |
| Skill A — Ground truth table | Pre-built static comparison | Static artifact |
| Skill B — Without | Pre-run, show artifact | Baseline, not the story |
| Skill B — With (6 batches × 3 personas) | **Pre-run** | Persona validation across 6 batches will exceed 2 min |
| Model comparison | **Pre-computed**, results table only | Never train live |

**Backup plan:** Have screenshots of every artifact and the comparison table ready as PNG slides. If anything fails to load, switch to the screenshot, narrate calmly, no apology.

---

## Pre-Demo Setup Checklist

- [ ] Build messy CSV (300 rows, X1–X23 names, ~5% question-mark nulls, light categorical inconsistency in `EDUCATION`)
- [ ] Pre-run Skill A on the messy CSV; save all four artifacts (profile HTML, transform report, transform metadata JSON, mistake log); bookmark the one transformation A-Owner will narrate
- [ ] Pre-run Skill B on Skill A's output; confirm `feat_bill_to_limit_ratio` (or your chosen feature) was approved with score 67; bookmark it in the report
- [ ] Train both logistic regressions: same 80/20 split, seed 42, record accuracy / F1 / AUC
- [ ] Look up Yeh & Lien (2009) benchmark numbers on the full 30K dataset
- [ ] Build the comparison table as a static PNG slide
- [ ] **Time the actual Skill A run on your laptop** — replace the `[X] minutes` placeholder in the script with the real number. The number must be true.
- [ ] Screenshot every artifact for backup
- [ ] Three full timed rehearsals minimum, ideally one with someone outside the team watching
- [ ] Confirm the framing of Group A and Group C with at least one member of each team — make sure they're comfortable being characterized as "model selection" and "documentation for compliance" respectively

---

## The Two Big Ideas (If They Forget Everything Else)

1. **The four-day part now takes minutes** — and every decision is on the record.
2. **Anyone can be a better analyst with better data** — the bottleneck isn't talent, it's access to clean, documented data.

Everything else in this demo is in service of those two ideas.
