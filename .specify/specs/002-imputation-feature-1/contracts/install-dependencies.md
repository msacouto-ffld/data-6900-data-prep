# Contract: Install Dependencies

**FR(s):** Pre-pipeline setup | **Owner:** Script | **Freedom:** Low | **Runtime:** Executed

## Purpose

Installs ydata-profiling and verifies the installation before any other pipeline code runs. This is the first step in every pipeline execution.

## Inputs

None — this step has no user inputs.

## Outputs

On success — console output:

```
📦 Installing profiling dependencies...
✅ ydata-profiling installed successfully.
```

On failure — console output:

```
❌ Dependency error: ydata-profiling could not be installed.
   Please try again in a new Claude.ai session.
```

## Logic

1. Run `subprocess.check_call([sys.executable, "-m", "pip", "install", "ydata-profiling", "-q"])`
2. Import `ydata_profiling` to verify
3. If import fails, halt pipeline with error message

## Error Conditions

| Condition | Message |
|-----------|---------|
| pip install returns non-zero exit code | "Dependency error: ydata-profiling could not be installed. Please try again in a new Claude.ai session." |
| Import fails after install | Same message as above |

## Dependencies

- `subprocess` — standard library
- `sys` — standard library