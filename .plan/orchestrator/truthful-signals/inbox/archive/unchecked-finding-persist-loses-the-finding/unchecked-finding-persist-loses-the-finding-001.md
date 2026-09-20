envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=landing
created=2026-07-28T16:28:28Z

## What landed

PR #1038 — `fix(phase-5-execute): fail loud on unchecked finding-persist`. Shipped a
population-derived sweep and fix for silently-dropped finding persists across the
marketplace, not just the originally-requested five sites.

## Scope vs request

The request hypothesized five sites needing a checked-persist fix. A sweep-derived
population found **10** production persist sites — the request's list was short by two
and wrong in shape (a sample, not an enumeration).

## Defects found (both were 100% silently dropping findings pre-fix)

- `scope_creep_check._emit_finding` — vacuous `returncode == 0` guard combined with an
  argv that never validated, so every call silently no-op'd. All six existing unit tests
  stubbed `_emit_finding` to return `True`, so the real function (and its malformed argv)
  was never exercised — untestable by construction.
- `_cmd_baseline_reconcile.py:461` — `finding_type not in FINDING_TYPES` silently dropped
  the persist instead of failing loud.
- All four producer-mismatch emitters were themselves unchecked persists: the guard whose
  job is reporting lost findings was itself a lost-finding vector.

## Self-caught during finalize

Pre-submission self-review caught a live silent-loss consumer that this plan itself
introduced: `phase-4-plan` Step 8 parsed only `total_failed`/`ambiguous`, so a rejected
persist would have been dropped at a call site the plan introduced — same defect class,
one level up.

## Other notable signals

- The whole-tree test-compile gate caught two `no-any-return` mypy errors that
  mypy-over-test-only would not have surfaced.
- Environment defect: dispatched leaves receive a truncated `PATH` missing
  `/opt/homebrew/bin`, so `gh`/`ci` calls fail with a misleading "Not authenticated" that
  reads like an auth problem rather than a PATH problem.

## Residue for the epic

None outstanding — PR #1038 is green with 3 reviewers compared and 4 actionable comments
triaged. See the candidate-lesson messages that follow this landing for the individually
proposed lessons.
