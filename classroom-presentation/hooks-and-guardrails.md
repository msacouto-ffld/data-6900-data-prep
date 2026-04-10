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

## Part 2: Live A/B Demo — Contract Validation Hook (10 min)
**Presenter B**

### Objective
Learners see — side by side — what happens when a skill-to-skill handoff runs *without* a hook versus *with* a hook enforcing the contract.

### Setup Context (10:00–11:00) — Explain the Pipeline (1 min)

"We're building a two-skill analytics pipeline:

- **Skill A** (Data Cleaning) takes a raw CSV, validates it, profiles it with ydata-profiling, and outputs a *cleaned CSV*.
- **Skill B** (Feature Engineering) takes that cleaned CSV and engineers new features — one-hot encoding, date extraction, derived ratios, normalization.

Skill B has a *handoff contract* — a set of hard gates the cleaned CSV must pass before feature engineering starts. The contract checks things like: no duplicate column names, no special characters in headers, consistent types per column, no empty files, and a cell count under 500,000.

For this demo, we don't need Skill A fully built. We have two scaffold CSVs: one that passes the contract, and one that violates it. The question is: **what catches the violation?**"

### Demo Part A — Without the Hook (11:00–14:30) — "The Silent Failure" (3.5 min)

**Narrate as you go:**

"Right now, Skill B's contract validation lives inside its prompt instructions. The SKILL.md tells the LLM to validate the input before proceeding. Let's see what happens when we hand it a bad CSV."

**Step 1 — Show the bad CSV** (`bad-handoff.csv`):

```
customer_id,revenue,revenue,signup_date,category
101,500,,2024-01-15,Premium
102,,"",2024/02/20,basic
103,300,300,,PREMIUM
```

Point out the violations:
- `revenue` column name is duplicated (violates validation step 7)
- Mixed date formats and missing values (violates step 9 — inconsistent types)
- Inconsistent casing in `category` (`Premium` vs `basic` vs `PREMIUM`) — Skill A should have standardized this

**Step 2 — Run Skill B without the hook:**

Show the LLM receiving the bad CSV. Because the validation is only in the prompt, the LLM may:
- Skip validation entirely and jump to feature engineering
- Notice *some* issues but proceed anyway ("I see duplicates but I'll rename them")
- Miss the inconsistent types entirely

**Step 3 — Show the damage:**

The LLM produces a feature-engineered CSV with nonsense: one-hot encoding on the duplicated `revenue` column, date extraction that fails silently on the inconsistent formats, and no error report.

**Key line:** "The LLM didn't refuse. It didn't flag. It *tried to be helpful* — and that's the problem. Probabilistic validation means sometimes it catches issues, sometimes it doesn't. You'll never know which run was safe."

### Demo Part B — With the Hook (14:30–18:30) — "The Hard Gate" (4 min)

**Step 1 — Show the hook script** (`.claude/hooks/validate-handoff.sh`):

```bash
#!/bin/bash
# PreToolUse hook — validates Skill A → Skill B handoff contract
# Runs BEFORE any tool call matching the feature engineering pipeline

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  echo '{"decision":"block","reason":"No file path provided or file not found."}'
  exit 2
fi

# Run the contract validation checks
python3 -c "
import pandas as pd, sys, json

path = '$FILE_PATH'
errors = []

# Step 2: Parse check
try:
    df = pd.read_csv(path)
except Exception as e:
    print(json.dumps({'decision':'block','reason':f'Not a valid CSV: {e}'}))
    sys.exit(0)

# Step 3: At least 1 column
if len(df.columns) == 0:
    errors.append('CSV has no columns.')

# Step 4: At least 1 data row
if len(df) == 0:
    errors.append('CSV has headers but no data rows.')

# Step 5: Cell count limit
cells = df.shape[0] * df.shape[1]
if cells > 500_000:
    errors.append(f'Dataset exceeds 500k cell limit ({cells} cells).')

# Step 7: Duplicate column names
dupes = df.columns[df.columns.duplicated()].tolist()
if dupes:
    errors.append(f'Duplicate column names: {dupes}')

# Step 8: Special characters in column names
import re
bad_cols = [c for c in df.columns if not re.match(r'^[a-zA-Z0-9_ ]+$', c)]
if bad_cols:
    errors.append(f'Special characters in column names: {bad_cols}')

# Step 9: Consistent types per column
for col in df.columns:
    types = df[col].dropna().apply(type).unique()
    if len(types) > 1:
        errors.append(f\"Column '{col}' has mixed types: {[t.__name__ for t in types]}\")

if errors:
    print(json.dumps({'decision':'block','reason':'Handoff contract violations: ' + '; '.join(errors)}))
else:
    print(json.dumps({'decision':'allow','reason':'All handoff contract checks passed.'}))
"

RESULT=$?
if echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('decision')=='allow' else 2)" 2>/dev/null; then
  exit 0
else
  exit 2
fi
```

Walk through the key points:
- This is a **PreToolUse** hook — it fires *before* the LLM's tool call executes
- It reads the file path from the tool input JSON via stdin
- It runs the same checks from the handoff contract (steps 2–9 from the validation rules table)
- Exit code 2 = hard block. The LLM never proceeds.

**Step 2 — Register the hook** in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Read|Execute",
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/validate-handoff.sh"
      }]
    }]
  }
}
```

**Step 3 — Run the same bad CSV through Skill B again:**

This time the hook fires, catches the duplicate column names and type inconsistencies, and **blocks the pipeline with a structured error message**:

```json
{
  "decision": "block",
  "reason": "Handoff contract violations: Duplicate column names: ['revenue']; Column 'signup_date' has mixed types"
}
```

The LLM never gets to attempt feature engineering. The user sees exactly what's wrong and knows to go back to Skill A.

**Step 4 — Show the good CSV** (`good-handoff.csv`) passing through cleanly:

```
customer_id,revenue,signup_date,category
101,500,2024-01-15,premium
102,350,2024-02-20,basic
103,300,2024-03-10,premium
```

Hook returns `{"decision": "allow"}`, exit code 0, pipeline proceeds.

**Key line:** "Same pipeline, same LLM, same prompt. The only difference is one line in `settings.json`. The hook turned a *suggestion* into a *guarantee*."

### Closing the Demo (18:30–20:00) — Hook vs. Skill Boundary (1.5 min)

"So should everything be a hook? No. Here's the distinction:

- The **contract validation** (duplicate columns, cell limits, type consistency) is a **hook** — it's pattern matching, it must happen every time, and failure should hard-block.
- The **feature engineering decisions** inside Skill B (should we one-hot encode this column? is this ratio meaningful?) — those stay in the **skill/prompt**. They require LLM judgment, domain reasoning, and the persona validation loop.

The rule of thumb: if a human would say 'this must *never* get through,' it's a hook. If a human would say 'use your judgment,' it's a skill."

**Transition:** "Presenter C will now give you the framework for making that decision systematically."

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
