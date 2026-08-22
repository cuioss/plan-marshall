# Aspect: Direct gh/glab Usage (Surfaces A+B)

Detect CI-abstraction leaks where the GitHub CLI (`gh`) or GitLab CLI (`glab`) is invoked directly — bypassing the `plan-marshall:tools-integration-ci:ci` abstraction — across the plan's logs and the plan's diff. Direct usage is a hard-rule violation documented in `CLAUDE.md` under *Workflow Discipline → CI operations: use abstraction layer*.

**Domain-invariant**: this aspect runs for every plan, regardless of domain. The former **Surface C** (CI-wrapper source scan for tangled gh/glab + local-git mutations) was a meta-only check that scanned plan-marshall's own CI-abstraction sources; it moved to the `plan-marshall-plugin-dev` domain retrospective aspect `pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan`, contributed via the `provides_retrospective_aspects()` extension point. See [`../../extension-api/standards/ext-point-retrospective.md`](../../extension-api/standards/ext-point-retrospective.md) and the home reference `pm-plugin-development:plan-marshall-plugin/references/wrapper-tangle.md`.

**Conditional**: always runs; emits zero findings when the plan is clean.

## Purpose

The CI integration abstraction exists because `gh`/`glab` invocations mix two concerns the retrospective needs to keep separate: remote provider operations (PR, issue, review) and local git mutations (checkout, branch delete). This aspect surfaces every runtime or code-level direct-CLI leak so the plan retrospective report carries concrete, file-line-snippet evidence rather than a generic rule reminder.

## Inputs

Two detection surfaces, each inspected independently:

- **Surface A — plan logs**: `logs/work.log` and `logs/script-execution.log` inside the plan directory. Lines where `gh `, `glab `, or `gh.` appears outside comments and strings are flagged. This captures runtime leaks recorded during plan execution.
- **Surface B — plan diff**: `git diff {base}...HEAD` (where `{base}` is the plan's base branch, typically `main`). Added lines (`+` diff prefix) invoking `gh` or `glab` are flagged. This captures code-level leaks introduced by the plan.

## What It Detects

| Surface | Where | Category | Rationale |
|---------|-------|----------|-----------|
| A | `logs/work.log`, `logs/script-execution.log` | `log_leak` | Runtime evidence of a direct CLI invocation during plan execution |
| B | `git diff {base}...HEAD` added lines | `diff_leak` | Code-level evidence of a direct CLI invocation introduced by the plan |

## Finding Severity

Every distinct violation is emitted as **one finding at `severity: error`**. No batching — the retrospective compiles all findings verbatim so operators see the full surface area, not a deduplicated summary. When a single source file contains multiple violations (e.g., three `gh` invocations on different lines), each line yields its own finding.

## Heuristics (false-positive filters)

To avoid flagging commentary, documentation, or examples, the script applies the following filters to source inspection (Surface B):

- **Comment lines**: Lines whose first non-whitespace character is `#` are skipped.
- **Markdown/documentation context**: Surface B's diff scan only counts added lines in `.py` files.

Surface A (logs) does not apply comment/docstring filters because log lines are never commented-out source — every matched line is real runtime evidence.

## Output TOON Schema

```toon
aspect: direct-gh-glab-usage
status: success
plan_id: {plan_id}
counts:
  total: N
  by_surface:
    log_leak: N
    diff_leak: N
findings[N]{surface,file,line,snippet,category,severity}:
  log_leak,logs/work.log,42,"...gh pr view 123...","log_leak",error
  diff_leak,scripts/foo.py,17,"+    subprocess.run(['gh', ...])","diff_leak",error
```

## LLM Interpretation Rules

- Every finding MUST surface in the final report verbatim — the compiler does not reorder, group, or truncate them.
- A non-zero `counts.total` always produces at least one lessons-proposal entry (see `references/lessons-proposal.md`) categorized as `bug`, since it represents a hard-rule violation.
- Surface A findings without a matching Surface B finding indicate runtime-only leaks — typically an LLM manually typed `gh` into Bash despite the hard rule. These should be proposed as `improvement` lessons targeting the calling component.

## Finding Shape

```toon
aspect: direct-gh-glab-usage
severity: error
category: {log_leak|diff_leak}
file: {relative path}
line: {1-based line number}
snippet: "{trimmed line content, max 200 chars}"
message: "Direct {gh|glab} usage detected at {file}:{line}"
```

## Out of Scope

- Automated remediation — this aspect reports only; fixes are proposed as lessons and applied in a separate plan.
- Wrapper-tangle detection — scanning plan-marshall's own CI-abstraction sources for tangled gh/glab + local-git mutations is the `plan-marshall-plugin-dev` domain aspect `wrapper-tangle`, not this domain-invariant aspect.
- Runtime detection of git subprocess calls that do NOT involve `gh`/`glab` — plain `git checkout` outside worktrees is a separate concern handled by the worktree-isolation invariant.
- Documentation/example scanning — markdown files and docstrings are intentionally excluded per the heuristics above.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-direct-gh-glab-usage.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect direct-gh-glab-usage --fragment-file work/fragment-direct-gh-glab-usage.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
