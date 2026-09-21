envelope_version=1
sender_type=plan
sender_id=manifest-composer-honours-declared-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-27T19:26:17Z

component=plan-marshall:build-pyproject
category=improvement
bundle=plan-marshall
suggested_disposition=merge_into 2026-07-16-16-003 (broaden from build-maven to every build-* wrapper; add the pyproject default and the CLAUDE.md doc gap)

# The script-level `--timeout` default (300s) truncates architecture-resolved long builds on build-pyproject too

## Context

Observed first-hand during phase-6-finalize of PLAN-75
(`manifest-composer-honours-declared-contract`, PR #1025). An orchestrator-tier build
whose architecture-resolved envelope reported ~1586s ran as:

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build \
  run --command-args "..."
```

with no `--timeout`. `pyproject_build.py run --help` confirms the flag's default:

```text
--timeout TIMEOUT     Build timeout in seconds (default: 300)
```

so the subprocess was killed at 300s — roughly one fifth of the resolved expected
duration. Compounded by the harness's ~600s foreground ceiling, this cost two failed
attempts before the flag was passed explicitly and the build completed.

## Why this is filed as a recurrence, not a new lesson

Lesson `2026-07-16-16-003` already states the mechanism precisely — "the script-level
`--timeout` binds, not the Bash timeout" — but it is scoped to
`plan-marshall:build-maven` and to that wrapper's *adaptively-lowered* timeout. This
sighting shows the same defect class on `plan-marshall:build-pyproject` with a
different mechanism: not an adaptive floor, but a **flat 300s argparse default** that
is independent of, and silently overrides, whatever `architecture resolve` computed.
Lesson `2026-07-27-00-001` covers a third variant (routed builds discarding
`--timeout` outright).

Three wrappers, three mechanisms, one defect: **the resolved duration does not reach
the process that enforces the deadline.**

## The doc gap that reproduces it

Both `CLAUDE.md` and `persona-plan-marshall-agent` § "Bash: Timeout from
architecture-resolved canonical command" instruct the caller to size the **Bash tool**
timeout from `bash_timeout_seconds` (`timeout: bash_timeout_seconds * 1000`). Neither
mentions the script-level `--timeout` flag at all. A caller who follows the documented
rule exactly still gets truncated at 300s. The instruction is not wrong — it is
incomplete in the one place where following it produces a false failure.

## The rule

- Whenever an architecture-resolved envelope reports `bash_timeout_seconds`, pass
  **both** deadlines: `--timeout {bash_timeout_seconds}` to the build wrapper AND
  `timeout: bash_timeout_seconds * 1000` on the Bash call. The script-level flag is the
  binding constraint; the Bash timeout must merely exceed it.
- Better still, fix it at the tool layer rather than at every call site: a build wrapper
  that can resolve the plan's architecture envelope should default `--timeout` from
  `bash_timeout_seconds` instead of a flat constant, so omitting the flag inherits the
  resolved duration rather than a value guaranteed to be wrong for long builds.
- Update the persona/CLAUDE.md build-command guidance to name the script-level flag.
  The rule as written is followable and still fails.

**Diagnostic tell** (from `2026-07-16-16-003`, confirmed again here): `status: timeout`
with `timeout_used_seconds` lower than both the Bash timeout and the resolved
`bash_timeout_seconds` means the script killed its own subprocess. Re-run with an
explicit `--timeout` before triaging it as a real build failure.

## Related

- `2026-07-16-16-003` — build-maven, adaptively-lowered default. Primary merge target.
- `2026-07-27-00-001` — routed builds silently discard `--timeout` entirely.
- `2026-07-27-00-002` — a timed-out build is recorded in the change ledger with
  `exit_code: 0`, so the truncation is invisible downstream unless `status` is read.
