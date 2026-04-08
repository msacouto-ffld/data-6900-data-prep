# Hooks in AI-Assisted Code Generation — 30-Minute Lesson Plan

**Audience:** Analytics practitioners and teams using AI coding agents
**Format:** 3 presenters, 10 minutes each, with a live demo in Part 2

---

## Part 1: What Are Hooks & Why They Matter (10 min)
**Presenter A**

### Objective
Learners understand what hooks are, how the lifecycle works, and why deterministic control matters for analytics workflows.

### Talking Points (0:00–5:00) — The Core Concept

- **Open with the reliability problem.** AI models are probabilistic — you can ask an agent to "always run tests after editing code," but it may skip that step. Hooks convert polite suggestions into guaranteed actions. Frame hooks as "if this, then that" rules that run every time, no exceptions.
- **Walk through the 5-step lifecycle.** Use a whiteboard or simple diagram:
  1. An event fires (tool call, session start, task end).
  2. The system finds registered hooks for that event type.
  3. Matchers filter which hooks apply (e.g., only file-write operations).
  4. The hook callback executes with contextual data (tool name, arguments, session info).
  5. The hook returns a decision: allow, block, modify inputs, or inject context.
- **Stress the key distinction:** deterministic vs. probabilistic control. Instructions in a CLAUDE.md or system prompt are *suggestions*. A PreToolUse hook with exit code 2 *blocks* an action 100% of the time.

### Talking Points (5:00–10:00) — Why Analytics Teams Should Care

Cover these six capabilities quickly (one sentence each, with a concrete example):

- **Automated data validation** — PostToolUse hook runs schema checks every time a pipeline script is generated.
- **Code standards enforcement** — auto-format with Black/Prettier after every file edit.
- **Security guardrails** — PreToolUse hook blocks dropping database tables or writing to production directories.
- **Audit logging** — every tool call logged for compliance and debugging.
- **Auto-documentation** — trigger docstring/README generation after code is written.
- **Input/output transformation** — sanitize data paths or inject credentials transparently.

Close with the "non-coder advantage": a well-configured set of hooks means you don't need to understand every line of AI-generated code — the hooks enforce formatting, testing, documentation, and safety before anything reaches production.

### Suggested Visual Aid
A simple two-column slide or whiteboard comparison: "Prompt-based instruction (probabilistic)" vs. "Hook (deterministic)" with examples of each.

---

## Part 2: Hooks Across Platforms + Live Demo (10 min)
**Presenter B**

### Objective
Learners see how hooks are configured on the major platforms and watch a real hook built for an analytics data-cleaning skill.

### Talking Points (10:00–13:00) — Platform Landscape (3 min)

Quickly contrast the four platforms. Don't read the table — just highlight what makes each one different:

| Platform | Key Differentiator |
|---|---|
| **Claude Agent SDK** | Most fully featured — 17+ events, Python/TS callbacks, matchers, permission decisions, async support. |
| **Claude Code CLI** | Shell command hooks in `.claude/settings.json`. JSON I/O via stdin/stdout. Great for quick automation. |
| **GitHub Copilot** | Hooks live in `.github/hooks/` on the default branch. Repo-scoped and version-controlled by default. |
| **Cursor** | Hooks integrated with Rules & Skills. Supports "grind loop" — agent iterates until all tests pass. |
| **Kiro (AWS)** | Event-based (file save/create), not tool-based. Tied to spec-driven 3-phase workflow. |

### Live Demo (13:00–19:00) — Build a CSV Validation Gate for a Data Profiling Skill (6 min)

**Context for the audience (30 seconds):** "We're building a data-cleaning skill where a user uploads a raw CSV, the system profiles it with ydata-profiling, and the LLM writes a natural language report. The spec says the system *must* reject empty CSVs, catch duplicate column names, and flag special characters — every single time. That's a perfect hook use case: it must happen every time, it's pattern-matching, and failure should block the pipeline before the LLM ever sees the data."

Walk through the four steps live in a terminal:

**Step 1 — Create the hook script** at `.claude/hooks/validate-csv.sh`:

```bash
#!/bin/bash
# PreToolUse hook: validate CSV before the profiling pipeline runs
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Skip if no file path provided
if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  exit 0
fi

# Only validate CSV files
EXT="${FILE##*.}"
if [ "$EXT" != "csv" ]; then
  exit 0
fi

# Run validation checks via Python
python3 -c "
import pandas as pd, sys, json

errors = []
try:
    df = pd.read_csv('$FILE')
except Exception as e:
    print(json.dumps({'error': f'Not a valid CSV: {e}'}))
    sys.exit(2)  # EXIT 2 = BLOCK the operation

# FR-003: Reject empty CSVs (headers only, no rows)
if len(df) == 0:
    errors.append('Empty CSV — headers only, no data rows.')

# FR-009: Detect duplicate column names
dupes = [c for c in df.columns if list(df.columns).count(c) > 1]
if dupes:
    errors.append(f'Duplicate column names: {set(dupes)}')

# FR-010: Detect special characters in column names
import re
bad_cols = [c for c in df.columns if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', str(c))]
if bad_cols:
    errors.append(f'Non-standard column names: {bad_cols}')

if errors:
    print(json.dumps({'errors': errors}))
    sys.exit(2)  # BLOCK — do not proceed to profiling
"
```

**Step 2 — Make it executable:**

```bash
chmod +x .claude/hooks/validate-csv.sh
```

**Step 3 — Register it** in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Execute",
      "hooks": [{ "type": "command", "command": ".claude/hooks/validate-csv.sh" }]
    }]
  }
}
```

**Step 4 — Test it with a bad CSV:**

```bash
# Create a CSV with duplicate columns and special characters
echo 'Name,Name,Email Address,score!' > bad_data.csv
echo 'Alice,A,alice@test.com,95' >> bad_data.csv

echo '{"tool_input":{"file_path":"bad_data.csv"}}' | .claude/hooks/validate-csv.sh
echo $?  # Should print 2 (BLOCKED)

# Now test with a clean CSV
echo 'name,email,score' > clean_data.csv
echo 'Alice,alice@test.com,95' >> clean_data.csv

echo '{"tool_input":{"file_path":"clean_data.csv"}}' | .claude/hooks/validate-csv.sh
echo $?  # Should print 0 (ALLOWED)
```

**Demo tip:** The payoff is the exit code. Show `$? = 2` for the bad CSV and `$? = 0` for the clean one. Then connect it back to Presenter A's point: "We didn't ask the LLM to check for duplicate columns. We didn't put it in a system prompt and hope. The hook *guarantees* this CSV never reaches ydata-profiling unless it passes validation. That's the difference between probabilistic and deterministic."

### Talking Points (19:00–20:00) — What Stays Outside the Hook (1 min)

Use the same skill to show the boundary: "Our spec also requires PII detection — scanning columns for names, emails, SSNs. That's *not* a hook. PII detection requires the LLM to reason about the content and context of column values, not just pattern-match file structure. That belongs in a skill or prompt-based rule. The decision framework is simple: if it's mechanical validation, make it a hook. If it requires judgment, keep it in the LLM." This sets up Presenter C's discussion of skills vs. hooks vs. sub-agents.

---

## Part 3: When to Use Hooks & What Comes Next (10 min)
**Presenter C**

### Objective
Learners know when hooks are the right tool (and when they aren't), understand how hooks differ from skills and sub-agents, and leave with clear next steps.

### Talking Points (20:00–24:00) — The Decision Framework (4 min)

Frame this as five quick yes/no questions:

| Question | If Yes | If No |
|---|---|---|
| Must it happen every single time? | **Hook** | Skill or prompt rule |
| Does it need AI judgment about content? | Skill or sub-agent | Shell command hook |
| Is it a side effect like logging? | Async hook | — |
| Does it block dangerous actions? | PreToolUse + exit code 2 | Permission rules |
| Is it project-specific? | `.claude/settings.json` | `~/.claude/settings.json` |

Give concrete "don't use hooks" examples: exploratory research (hooks add rigidity), one-off operations (just ask the AI), and anything requiring content understanding (hooks are pattern-matchers, not reasoners). Also flag latency — synchronous hooks that run longer than 5 seconds degrade the experience.

### Talking Points (24:00–27:00) — Skills vs. Hooks vs. Sub-Agents (3 min)

Use one sentence per mechanism, then a concrete example:

- **Skills** are markdown instruction packages the AI loads on demand. They're probabilistic — the agent decides whether to use them. *Example: a "data-pipeline-conventions" skill that tells the agent to use Pandas and follow naming conventions.*
- **Hooks** are deterministic scripts that fire at lifecycle events. They run outside the LLM and can't reason about content. *Example: PostToolUse hook running Black on every Python file — the agent's preferences are irrelevant.*
- **Sub-agents** are isolated AI instances with their own context window. They prevent context pollution and can run in parallel. *Example: a "data-quality-reviewer" sub-agent that analyzes generated code without crowding the main conversation.*

**The one-liner:** Use CLAUDE.md for memory, skills for routines, hooks for guarantees, sub-agents for delegation.

### Talking Points (27:00–30:00) — Next Steps & Resources (3 min)

Give the team a concrete starting checklist:

1. **Start with two hooks:** an auto-formatter (PostToolUse on `Write|Edit`) and a security gate (PreToolUse on `Bash`). These cover the most common failure modes with minimal setup.
2. **Version-control your hooks.** Store them in `.claude/settings.json` or `.github/hooks/` so every team member gets the same safety gates.
3. **Try the `/powerup` command** in Claude Code — select "Hooks Basics" for an interactive in-terminal walkthrough.
4. **Explore spec-driven development** for complex analytics projects — combine specifications with hooks to ensure AI-generated code meets documented requirements.

Recommend these learning resources:
- DataCamp: "Claude Code Hooks: A Practical Guide to Workflow Automation"
- Blake Crosley: "Claude Code Hooks Tutorial: 5 Production Hooks From Scratch"
- DEV Community: "Claude Code Hooks Guide 2026"
- GitHub Docs: "Using Hooks with GitHub Copilot Agents"

### Close
Open the floor for questions. If time is short, remind the group that hooks are low-effort, high-impact — two hooks and 15 minutes of setup can eliminate entire categories of errors from AI-generated code.

---

## Preparation Checklist

- [ ] Presenter A: Prepare a whiteboard/slide showing the 5-step lifecycle diagram
- [ ] Presenter B: Set up a terminal with Claude Code, jq, and Python 3 (with pandas) installed
- [ ] Presenter B: Prepare two test CSVs — `bad_data.csv` (duplicate columns, special characters) and `clean_data.csv` (valid) — so you don't create them live
- [ ] Presenter B: Have the PII detection example ready as a talking point (not live-code) to contrast hook vs. skill
- [ ] Presenter C: Print or display the decision framework table for reference
- [ ] All: Test the demo end-to-end at least once before the session
- [ ] All: Share this lesson plan and the Hooks Report with attendees afterward
