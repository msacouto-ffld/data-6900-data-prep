# Hooks in AI-Assisted Code Generation — 30-Minute Lesson Plan

**Audience:** Analytics practitioners and teams using AI coding agents
**Format:** 3 presenters, 10 minutes each, with a live A/B demo in Part 2

---

## Part 1: What Are Hooks & Why They Matter (10 min)
**Presenter A**

### Objective
Learners understand what hooks are, how the lifecycle works, and why deterministic control matters for analytics workflows.

### Talking Points (0:00–5:00) — The Core Concept

- **Open with the reliability problem.** AI models are probabilistic — you can ask an agent to "always validate the data before running the pipeline," but it may skip that step. Hooks convert polite suggestions into guaranteed actions. Frame hooks as "if this, then that" rules that run every time, no exceptions.
- **Walk through the 5-step lifecycle.** Use a whiteboard or simple diagram:
  1. An event fires (tool call, session start, task end).
  2. The system finds registered hooks for that event type.
  3. Matchers filter which hooks apply (e.g., only file-write operations).
  4. The hook callback executes with contextual data (tool name, arguments, session info).
  5. The hook returns a decision: allow, block, modify inputs, or inject context.
- **Stress the key distinction:** deterministic vs. probabilistic control. A hook runs *every* time — no exceptions, no "the model forgot." This is the core reason hooks exist.

### Talking Points (5:00–8:00) — The "So What?" — Three Things Hooks Give You

Don't just list capabilities — frame each one around what goes wrong *without* it:

1. **Validation gates** — Block bad data before the LLM ever sees it. Without a gate, the LLM "tries to be helpful" on garbage input and produces plausible-looking nonsense. Imagine Skill A outputs a CSV with duplicate column names. Without a hook, Skill B might silently rename them and proceed — and now your feature-engineered dataset has columns nobody asked for. With a hook, the pipeline stops and tells you exactly what's wrong.

2. **Observability and logging** — Hooks can produce structured logs of every action the agent takes, giving you an audit trail. This matters for compliance, debugging, and trust. Example: a `PostToolUse` hook that writes a JSON log entry every time the agent writes or modifies a file — what file, what tool, what timestamp. If an output looks wrong, you can trace backward through the log instead of re-running the whole pipeline and hoping you catch it. In our pipeline, a logging hook on the Skill A → Skill B handoff could record every validation result — pass or fail — with the run ID and contract checks, building a mistake log over time.

3. **Context injection** — Feed the agent extra information (schemas, contracts, prior results) at exactly the right moment. A `PreToolUse` hook can inject Skill A's profiling report into Skill B's context *before* feature engineering starts, so the LLM doesn't have to be told to look for it — it's already there.

### Talking Points (8:00–10:00) — Hooks in the Wild: OpenClaw

Briefly connect to a current real-world example so this doesn't feel academic:

- **OpenClaw** (formerly Clawdbot, now 100k+ GitHub stars) is an open-source AI agent framework that shipped a native hooks system in early 2026. Their architecture mirrors exactly what we've been describing: hooks fire on agent events (`command:new`, `command:stop`, lifecycle events), they're discovered automatically from a `hooks/` directory, and they can be enabled/disabled via CLI (`openclaw hooks enable session-memory`).
- Two of their built-in hooks are good illustrations: `session-memory` saves session context to a workspace file on every `/new` command (observability), and `command-logger` writes structured JSON logs of every action with timestamps and session IDs (audit trail). These are the same patterns we'll use in our pipeline.
- The key architectural point: OpenClaw hooks run *inside the gateway process*, meaning they can synchronously intercept and block actions — exactly like our `PreToolUse` validation gate. This is different from external webhook services that add network latency and can't hard-block.

Then briefly cover the mechanics:
- In Claude Code, hooks are configured in `.claude/settings.json` (project-level) or `~/.claude/settings.json` (user-level). The actual hook scripts go in `.claude/hooks/` by convention.
- Hooks communicate via exit codes: **0 = proceed**, **2 = block**, **1 = non-blocking error**. They can also return structured JSON via stdout for richer feedback.
- This is separate from skills. Skills live in their own directory. Hooks are *infrastructure* — they enforce rules across skills.

**Transition:** "Now Presenter B will show you what this looks like in practice — with a real hook built for a real skill pipeline, and an A/B test so you can see the difference."

---
# Part 2: Live A/B Demo — Contract Enforcement in Agent Systems (10 min)
**Presenter B**

---

## Objective

Learners see — side by side — what happens when a skill-to-skill handoff runs:

* **Without system-level enforcement (Skill only)**
* **With deterministic enforcement (Skill + validation layer)**

---

# Setup Context (10:00–11:00) — Explain the Pipeline (1 min)

"We’re building a two-skill analytics pipeline:

* **Skill A (Data Cleaning)**: takes a raw CSV, validates and cleans it, and outputs a structured dataset
* **Skill B (Feature Engineering)**: takes that dataset and creates new features — encoding categories, extracting dates, building ratios, normalizing values

Between them is a **handoff contract** — a set of rules the data must satisfy before Skill B runs.

Things like:

* No duplicate column names
* Consistent data types
* Valid column formats
* Reasonable dataset size

For this demo, we’re skipping Skill A and using two files:

* One that **violates the contract**
* One that **passes it**

The question is: *what actually enforces the contract?*"

---

# Demo Part A — Skill Only (11:00–14:30) — "The Silent Failure"

### Step 1 — Show the Bad CSV (`bad-handoff.csv`)

```
customer_id,revenue,revenue,signup_date,category
101,500,,2024-01-15,Premium
102,,"",2024/02/20,basic
103,300,300,,PREMIUM
```

Point out:

* Duplicate column name (`revenue`)
* Mixed date formats
* Missing values
* Inconsistent category casing

Say:

"This file clearly violates the contract. In a production pipeline, this should never reach feature engineering."

---

### Step 2 — Run Skill B in Copilot Chat (Loose Version)

Open Copilot Chat and paste:

* Loose Skill B prompt
* `bad-handoff.csv`

Say:

"Right now, we’re running the skill directly. There is **no system enforcing the contract** — only instructions inside the prompt."

---

### Step 3 — Observe Behavior

The model may:

* Rename duplicate columns
* Attempt to fix inconsistencies
* Proceed with feature engineering anyway

Result:

* Features are generated
* Errors are not surfaced clearly
* Data issues propagate silently

---

### Key Line

"The model didn’t refuse. It didn’t block. It tried to be helpful — and that’s the problem.

When validation lives inside the prompt, it becomes **probabilistic**. Sometimes it works. Sometimes it doesn’t. You don’t get guarantees."

---

# Demo Part B — Skill + Validation Layer (14:30–18:30) — "The Hard Gate"

### Step 1 — Introduce the Validation Layer

"Now we introduce a deterministic validation layer that runs **before Skill B executes**.

In an agent system, this would be a guardrail or a PreToolUse hook.
Here, we simulate it with a Python validation step."

---

### Step 2 — Run Validator on Bad CSV

In VS Code terminal:

```bash
python3 scripts/validate_handoff.py data/bad-handoff.csv
```

Show output:

```json
{
  "decision": "block",
  "reason": "Handoff contract violations: Duplicate column names: ['revenue']; Column 'revenue' has mixed types (numeric + string)"
}
```

Say:

"The pipeline stops here. Skill B never runs.

We get a precise explanation of what’s wrong — and we know exactly where to fix it."

---

### Step 3 — Run Validator on Good CSV

```bash
python3 scripts/validate_handoff.py data/good-handoff.csv
```

Show output:

```json
{
  "decision": "allow",
  "reason": "All handoff contract checks passed."
}
```

Say:

"Only now does the system allow the skill to run."

---

### Step 4 — Run Skill B in Copilot (Same Prompt as Part A)

Paste:

* Same loose Skill B prompt
* `good-handoff.csv`

Say:

"Same skill. Same prompt. No changes."

---

### Step 5 — Observe Behavior

Now:

* Clean input
* Consistent types
* No structural issues

Result:

* Feature engineering behaves as expected
* Outputs are coherent and reliable

---

### Key Line

"Same model. Same prompt.

The only difference is the validation layer.

We’ve turned a suggestion into a guarantee."

---

# Closing Insight (18:30–20:00)

"So should everything be enforced this way? No.

* The **contract validation** — duplicate columns, type consistency, file structure — must be deterministic. That’s a hard gate.
* The **feature engineering decisions** — what to create, how to transform — require judgment. That stays in the skill.

The rule of thumb:

If a human would say *'this must never get through'* → enforce it deterministically.
If a human would say *'use your judgment'* → leave it to the model."

---

### Transition

"Next, we’ll give you a framework for deciding what belongs in guardrails versus what belongs in the skill itself."


---

## Part 3: Applying Hooks to Our Projects (10 min)
**Presenter C**

### Objective
Learners can distinguish hooks from skills/sub-agents and see exactly where hooks apply in their own Synchrony project work.

### Talking Points (20:00–23:00) — The Decision Framework (3 min)

Present this as a quick decision tree:

| Ask yourself… | If YES → | If NO → |
|---|---|---|
| Must this happen every single time, with zero exceptions? | Hook | Skill/prompt |
| Is it pattern matching (not reasoning)? | Hook | Skill/prompt |
| Should failure hard-block the pipeline? | Hook | Skill/prompt (or soft warning) |
| Does it require domain judgment or contextual reasoning? | Skill/prompt | Hook |

Walk through two examples from the demo pipeline:

1. **"Reject CSVs with duplicate column names"** → Must happen every time? Yes. Pattern matching? Yes. Hard block? Yes. → **Hook.**
2. **"Decide whether to one-hot encode a categorical column with 500 unique values"** → Requires judgment? Yes. Context-dependent? Yes. → **Skill** (specifically, the persona validation loop in Skill B).

### Talking Points (23:00–25:00) — Hooks in Our Pipeline (2 min)

Walk through the specific hook opportunities in our Data Cleaning → Feature Engineering pipeline:

- **Handoff contract gate** (what we just demoed) — PreToolUse hook that validates Skill A's output against the 12-step contract before Skill B starts. This is the first and most important hook because it sits at the trust boundary between two independently developed skills.
- **Observability / mistake log hook** — PostToolUse hook that appends a structured JSON entry to a run log every time a validation passes or fails (Skill B's FR-221 requires a mistake log). Over time, this builds the data the PM needs to spot recurring patterns and trigger constitution updates. This is the same pattern OpenClaw uses with their `command-logger` hook.
- **Output schema check** — PostToolUse hook that verifies Skill B's three final deliverables (feature-engineered CSV, transformation report, data dictionary) all exist and conform to expected structure before the pipeline reports success. This catches the case where the LLM claims it's done but quietly skipped the data dictionary.

Then clarify what stays *out* of hooks:
- Feature engineering decisions (one-hot vs. label encoding, whether a derived ratio is meaningful) → **Skill B's persona validation loop** — this requires LLM reasoning.
- PII detection in Skill A → **Skill A's prompt instructions** — this requires AI judgment about column content, not pattern matching.
- Plain-language compliance checks (FR-223, FR-224) → **Skill B's jargon scan script** — this is deterministic but runs *within* the skill's execution, not at a boundary.

### Talking Points (25:00–27:00) — How This Applies to Other Projects (2 min)

Connect hooks to the other two group's projects to show the concept isn't pipeline-specific:

- **Team JAS** is building an evaluation framework that benchmarks Claude, Gemini, and ChatGPT across SQL and Python tasks. Their pipeline runs each model on a standardized prompt, then scores the output on correctness, performance, formatting, and AI Critic review. Where could hooks help?
  - **PreToolUse gate on prompt injection**: Before each model receives a task prompt, a hook could verify the prompt matches the canonical task bank — ensuring no accidental modifications or model-specific tweaks slip in. This protects the "one-shot, no revisions" evaluation guarantee.
  - **PostToolUse logging for reproducibility**: After each evaluation run, a hook could log the exact model, prompt, dataset variant, and timestamp to a structured audit file — making it trivial to reproduce any scorecard result. This is the same observability pattern from Part 1.
  - **Output schema validation**: After the evaluation harness produces a scorecard JSON, a hook could validate that every required field (correctness score, performance metrics, Critic review) is present before the scorecard is marked complete — catching partial runs before they contaminate the final report.

- **Group C** s building a skillset that converts raw repository artifacts (JSON schemas, test catalogs, control libraries) into audit-ready compliance documentation. Their spec actually requires all input validation to happen deterministically before any LLM processing — that's a hook written into the spec itself. Where else do hooks fit?
  - **Input format gate (PreToolUse)**: Before any file reaches the LLM, a hook validates it is present, is valid JSON, and contains the required top-level keys for its type. Without this, the LLM might attempt to parse an unsupported file format and produce a plausible-looking but wrong data dictionary. This is a hard block — not a suggestion.
  - **Citation integrity gate (PostToolUse)**: After the LLM drafts an RCSA control narrative, a hook extracts every inline citation and checks each one against the artifact index. If any citation doesn't resolve to a real artifact, the hook blocks the output from being written at all — catching the hallucination case where the LLM invents a reference that sounds credible but doesn't exist.
  - **Output completeness check (PostToolUse)**: Each skill run must produce multiple required files — a data dictionary plus a QA report, or control narratives plus a validation report. A hook verifies all required files exist, are non-empty, and contain expected section headers before the pipeline reports success. Same pattern as our pipeline's output schema check — just different file names.

**Key point:** "The pattern is the same regardless of the project: find the trust boundary, write a deterministic check, make it a hook. Whether you're validating a cleaned CSV or an evaluation prompt, the architecture is identical."

### Talking Points (27:00–29:00) — Action Plan (2 min)

Give the team four concrete steps:

1. **Map your trust boundaries.** In our pipeline, it's the Skill A → Skill B handoff. In Team JAS's framework, it's the prompt → model and model → scorecard boundaries. Every multi-step AI workflow has at least one.
2. **Start with one hook.** Write a shell script that checks 2–3 things at that boundary and exits with code 2 on failure. Keep it under 30 lines. Our `validate-handoff.sh` is a good template.
3. **Add a logging hook second.** Once validation is working, add a PostToolUse hook that writes structured JSON logs. This builds your audit trail and feeds your mistake log over time.
4. **Review against your spec.** Walk through your feature spec's functional requirements and ask: "Which of these *must* happen every time and can be checked without LLM reasoning?" Those are your hook candidates.

### Talking Points (29:00–30:00) — Resources & Close (1 min)

Recommend these learning resources:
- DataCamp: "Claude Code Hooks: A Practical Guide to Workflow Automation"
- Blake Crosley: "Claude Code Hooks Tutorial: 5 Production Hooks From Scratch"
- DEV Community: "Claude Code Hooks Guide 2026"
- OpenClaw Docs: Hooks documentation at docs.openclaw.ai/automation/hooks

### Close
Open the floor for questions. If time is short, remind the group: "The A/B demo showed the whole point — same LLM, same prompt, same data. Without the hook, the bad CSV slipped through and the LLM tried to be helpful on garbage data. With the hook, it was caught and blocked before the LLM ever saw it. That's the difference between a suggestion and a guarantee — and every one of our projects has places where that difference matters."

---

## Preparation Checklist

- [ ] **Presenter A:** Prepare a whiteboard/slide showing the 5-step lifecycle diagram
- [ ] **Presenter A:** Have the OpenClaw hooks docs page open for reference (docs.openclaw.ai/automation/hooks) — you may want to show the `command-logger` JSON output format as a quick visual
- [ ] **Presenter B:** Set up a terminal with Claude Code and `jq` installed
- [ ] **Presenter B:** Prepare `bad-handoff.csv` with the three contract violations (duplicate column name, mixed date formats, inconsistent casing)
- [ ] **Presenter B:** Prepare `good-handoff.csv` that passes all contract checks cleanly
- [ ] **Presenter B:** Have the hook script (`.claude/hooks/validate-handoff.sh`) ready and tested
- [ ] **Presenter B:** Have `.claude/settings.json` ready to register the hook
- [ ] **Presenter B:** Rehearse the A/B flow: run bad CSV without hook → show silent failure → register hook → run bad CSV again → show block → run good CSV → show pass
- [ ] **Presenter C:** Print or display the decision framework table for reference
- [ ] **Presenter C:** Have Team JAS's proposal summary handy (evaluation framework with prompt → model → scorecard pipeline) for the cross-project connection
- [ ] **All:** Test the full A/B demo end-to-end at least once before the session
- [ ] **All:** Share this lesson plan and the Hooks Report with attendees afterward
