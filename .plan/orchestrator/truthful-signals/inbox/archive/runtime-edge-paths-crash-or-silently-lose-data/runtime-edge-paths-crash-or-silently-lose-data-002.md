envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:24:30Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_aspects=direct_gh_glab_usage,artifact_consistency

# direct-gh-glab-usage Surface B reports a zero it never earned

## Context

The `direct-gh-glab-usage` aspect fragment for this plan reads:

```
counts:
  total: 0
  by_surface:
    log_leak: 0
    diff_leak: 0
findings[0]:
```

Surface B is documented as "`git diff {base}...HEAD` added lines — code-level leaks introduced
by the plan". At the time this aspect ran, the plan's worktree had been removed by
branch-cleanup and the PR had already landed on `main`, so `project_root` was the main checkout
and `base` defaulted to `main` — making `main...HEAD` an empty diff. Surface B examined zero
lines and reported `diff_leak: 0`, which is indistinguishable in the output from having
examined the plan's whole diff and found it clean.

## Root cause

Two independent paths produce the same undiscriminated zero in
`_git_diff_added_lines(base, project_root)`:

1. `if proc.returncode != 0: return []` — a git failure (bad ref, not a repo, detached state)
   returns an empty added-line list, identical to a clean diff.
2. `except (FileNotFoundError, subprocess.TimeoutExpired): return []` — same.

and a third at the caller level: a legitimately empty diff, which is what happened here. The
fragment's output schema has no field that could tell the three apart, because it carries only
`counts` and `findings`.

## Proposed action

Emit coverage on the fragment: `surface_b_scanned: true|false`, the resolved `base`, the
resolved `project_root`, and `diff_files_examined`. When the diff is empty or git failed,
report Surface B as `not_scanned` with the reason, rather than folding it into a `0` count.
Optionally reuse the landing-commit resolution proposed for `check-artifact-consistency` so
Surface B has a real diff to scan post-merge.

## Evidence

- aspect: direct_gh_glab_usage — `counts.total: 0`, `by_surface.diff_leak: 0`, no coverage field
- source: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/direct-gh-glab-usage.py`, `_git_diff_added_lines` returns `[]` on `returncode != 0` and on subprocess exceptions
- contrast within the same skill: `check-manifest-consistency` reports `branch_cleanup_changes,skip,"rule M4 skipped — no diff data available (base=unknown or empty diff)"` on the identical condition, and `check-artifact-consistency` reports `inconclusive`

## Why this one matters

Surface A (log scan) genuinely ran and is genuinely clean — 438 work-log and 1255
script-execution entries, zero matches. So the aspect's headline `total: 0` is probably
correct. The defect is that it is not *checkable*: a reader cannot tell which half of the
aspect was actually exercised, and the same output would be produced if Surface B never ran on
any plan.
