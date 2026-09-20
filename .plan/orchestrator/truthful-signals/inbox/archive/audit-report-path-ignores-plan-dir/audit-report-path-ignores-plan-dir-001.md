envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=truthful-signals
kind=finding
created=2026-07-29T19:47:01Z

# `resolve-test-scope` returns a docs-only verdict for Python source under `.claude/skills/**`

## Theme fit

Confident-signal-hides-a-caveat. The verb returns a well-formed, successful-looking
verdict that the consuming workflow reads as an authoritative "no tests needed"
instruction. Nothing in the signal marks it as an unresolved case — the null
`recommended_target` is indistinguishable from a genuine docs-only change.

## Observed (verified during plan `audit-report-path-ignores-plan-dir`, deliverable 1)

For the changed path `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`
— a Python production source file with a live pytest module — the verb returns:

```
scoped_modules[0]:
recommended_target: null
```

`execute-task` documents that shape as the **docs-only short-circuit → run NO pytest**.

## Why it matters (near-miss, not hypothetical)

The executing task took the non-documented path deliberately and ran
`module-tests plan-marshall` instead. Had it followed the documented short-circuit,
deliverable 1 would have shipped with **zero test execution** — and the pass would
have looked clean, because a skipped test suite and a green test suite are reported
identically at the task-verification layer.

Two real defects were caught by the tests that the documented path would have skipped:

1. The mutation check that proved the new regression tests are non-vacuous
   (reverting `_resolve_repo_root` to `Path.cwd()` must fail exactly two tests).
2. A test branch that was initially **unconstructible**: pytest's basetemp sits under
   this project's own `.plan/temp/`, so every `tmp_path` has a `.plan/local`-bearing
   ancestor — making the "no marker anywhere up the tree" branch vacuously pass.
   It now uses `tempfile.TemporaryDirectory()` with an explicit precondition assertion.

## Suspected root cause (NOT verified — do not treat as established)

The scope resolver appears to map changed paths to modules via the marketplace
bundle layout (`marketplace/bundles/**`) and the registered test tree, and
`.claude/skills/**` — project-local skills — is outside both. A path that maps to no
module yields an empty `scoped_modules`, which the consumer then reads as docs-only.

⛔ This orchestrator did NOT read the resolver implementation. Confirm or refute at
the `resolve-test-scope` verb before scoping any fix.

## Population warning

One instance was observed. `.claude/skills/**` holds several project-local skills with
Python scripts and pytest modules. **Derive the population** — do not fix only the
single observed path. The same null-verdict class may also cover other path roots that
are outside the module inventory.

## Suggested shape of a fix (not prescriptive)

The failure is that "no module matched" and "no tests needed" are the same signal.
Separating them — so an unresolved path fails closed with an explicit unknown state
rather than resolving to a confident docs-only verdict — is the ADR-009-shaped
correction, and is the reason this belongs to this epic rather than to a local patch.

## Provenance

- Surfaced by: plan `audit-report-path-ignores-plan-dir` (epic `code-intelligence-substrate`, PLAN-11), deliverable 1.
- Out of scope for that plan; forwarded rather than actioned there.
- Operator directed it here rather than to the lessons corpus.
