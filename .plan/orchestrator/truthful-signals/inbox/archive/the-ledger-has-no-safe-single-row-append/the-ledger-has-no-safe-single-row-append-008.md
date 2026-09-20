envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:20Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high

# Fall back to the shared footprint resolver when a base-ref diff is empty

## Context

`check-manifest-consistency` obtains its diff from `--diff-file` or `--base-ref`. Its canonical-invocations block instructs supplying `--base-ref` whenever `--diff-file` is absent, because that is how the script obtains a diff at all.

Run against this plan AFTER it merged, with `--base-ref origin/main`, the script reported `diff_available: true`, `files_total: 0`, and failed rule M4 with the finding:

> phase_6.steps includes branch-cleanup but the observed diff is empty - the footprint resolved to no changed path at all, so no implementation file changed

The plan changed seven files. The diff was empty only because `origin/main` already contained them.

The same retrospective run, at the same instant, resolved the real seven-path footprint twice: `check-routing-decisions` and `check-outline-vs-shipped` both reported `footprint_source: resolved` with the correct paths, through the shared footprint resolver. The evidence was available; this script simply did not use it.

Without `--base-ref` the rule correctly skips (`diff_available: false`, M4 skipped, zero findings). So the documented invocation is the one that produces the false failure.

## Root cause

A resolved-but-empty diff is treated as positive evidence of no change. Post-merge, an empty diff against the merge target means the opposite. The script has no second source to cross-check against, even though its two sibling aspects use one.

## Proposed action

When the base-ref diff resolves empty, fall back to the shared footprint resolver before concluding no file changed - or report `indeterminate` rather than a failing check. A verdict over evidence that cannot distinguish "nothing changed" from "the base already has it" is not a clean result.

## Evidence

- Run A, `--base-ref origin/main`: `diff_available: true`, `files_total: 0`, `branch_cleanup_changes` = **fail**, one `branch_cleanup_without_changes` finding.
- Run B, no `--base-ref`: `diff_available: false`, `branch_cleanup_changes` = **skip**, zero findings.
- Same retrospective, same instant: `check-outline-vs-shipped` reported `footprint_source: resolved`, `footprint_path_count: 7`; `check-routing-decisions` reported `footprint_source: resolved`.
- `retro_sections.py` lines 42-52 explicitly note that `manifest-decisions` publishes no footprint-degradation verdict and so reads as resolved on every run.
