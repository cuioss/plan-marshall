# ci-wait TOON fixtures

Representative `ci checks wait --pr-number {N}` TOON stdout fixtures used
by `test_ci_complete_precondition.py` to drive the fixture-based
resolver tests (plan
`ci-complete-resolver-still-mis-maps-green-ci-mock`).

Each fixture is a verbatim-shape TOON envelope that mirrors what
`workflow-integration-github:github_ops.cmd_ci_wait` emits via
`serialize_toon(result, table_separator='\t')`. The exact envelope shape
matches the contract in
`marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/api-contract.md`
under "ci wait" and the production emit path in
`marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py`
function `cmd_ci_wait`.

These are **representative** (authored to mirror real-stdout structure)
rather than captured from live `gh pr checks` runs. The deliverable
description in the parent plan (`solution_outline.md` § 2) initially
listed live capture as the preferred source, but the verification
criterion is "fixtures load without error in the fixture-driven
tests" — i.e. parse-and-extract round-trip. Authored fixtures cover the
full CI state matrix (lesson `2026-05-24-14-001` § "Root cause 1" —
mock-only unit tests cannot reproduce the live failure mode, but
representative TOON envelopes exercise the same `parse_toon` →
`resolve()` code path that the live failure exercises).

## Fixture catalogue

| Fixture | CI state | Why it matters |
|---------|----------|----------------|
| `green-success.toon` | All-green (mix of pass + skipping) | Baseline regression — the exact case PR #454 hit; resolver must return `wait_succeeded / ci_final_status: success`. |
| `failure-with-failing-checks.toon` | One failing check (rest pass) | `failing_checks[]` enumeration end-to-end. Resolver returns `wait_failed / ci_final_status: failure`. |
| `no-checks.toon` | Empty `checks[]` (no CI configured) | `final_status: none` → resolver maps to `ci_final_status: no_checks`. |
| `timeout-deadline-exceeded.toon` | True timeout — checks still running at deadline | `status: error / wait_outcome: deadline_exceeded`. Resolver maps to `ci_final_status: timeout`. |
| `pending-then-cancelled.toon` | Workflow run cancelled before completion | All checks terminal with `result: cancelled`. Exercises non-failure terminal classification. |
| `mixed-success-failure.toon` | Multiple failing checks alongside passing ones | Multi-row `failing_checks[]` parsing. |
| `skipped-checks.toon` | Mix of pass + skipping rows | Variant of green-success without the failure-suspect SKIPPED block elsewhere — distinguishes "all pass" from "pass with skips". |
| `single-check-success.toon` | Exactly one check, green | Minimum non-empty checks table — exercises the inline-table parser at the smallest table size. |
| `many-checks-success.toon` | Eight checks, all green | Larger inline-table to exercise parser performance and column-alignment on realistic check counts. |

### Stress fixtures (Q-Gate finding e2c3ee re-direction)

Added under the phase-5-execute review's directive to widen TASK-002's
fixture set with the six stressor categories the original 9 captures
didn't cover. The (b) category surfaced a live parser bug — see TASK-004
for the fix.

| Fixture | Stressor | Why it matters |
|---------|----------|----------------|
| `url-with-commas-and-quotes.toon` | (a) URL with commas/quotes | URL columns of tab-separated rows may contain commas, quotes, and escaped percent codes — the tab-mode splitter must ignore commas. |
| `check-name-special-chars.toon` | (b) Check name with `:`, `[]`, `()`, `/`, `=` | Real CI check names like `lint:strict`, `coverage = 95%`, `build (linux/amd64)`. The colon-bearing names triggered the live bug in `parse_toon`'s key/value-detection heuristic — fixed in TASK-004. |
| `multi-line-error-summary.toon` | (c) Multi-line `\|` content | Older `gh` envelopes carry multi-line error summaries via the TOON `\|` block. Must parse cleanly with a trailing `checks[N]:` table. |
| `older-gh-envelope.toon` | (d) Older `gh` CLI envelope | Older `gh` versions emitted empty `url` and `run_id` fields; the parser must tolerate empty tab-separated columns and the resolver must still classify by `final_status`. |
| `huge-checks-block.toon` | (e) >50-row checks table | Pins parser correctness at realistic large-PR counts (55 rows). |
| `mixed-skipped-cancelled-neutral.toon` | (f) SKIPPED + CANCELLED + NEUTRAL + FAIL | A failure envelope mixing all four non-success terminal states. The `failing_checks` enumeration must include CANCELLED, NEUTRAL, AND FAILURE conclusions. |
| `failing-checks-with-colon-names.toon` | (b) companion | Companion to `check-name-special-chars`: a failure envelope whose `failing_checks[N]:` rows have colon-bearing names. Before the TASK-004 fix the resolver returned `failing_checks: []` — consumers depending on this enumeration (e.g. ci-verify consume-failures mode) silently received no failing-check signal. |

## Envelope shape

The wait envelope's top-level keys (per `cmd_ci_wait` in `github_ops.py`):

| Key | Type | Notes |
|-----|------|-------|
| `status` | `success` \| `error` | `error` only on timeout; success path covers final pass/fail. |
| `operation` | `"ci_wait"` | Fixed. |
| `pr_number` | int | PR identifier. |
| `final_status` | `success` \| `failure` \| `none` | Absent on timeout envelopes — the resolver branches on `status` first. |
| `duration_sec` | int | Total wait duration. |
| `polls` | int | Number of polls before terminal. |
| `elapsed_sec` | int | Total elapsed across all checks. |
| `checks` | uniform array, fields `{name,status,result,url,workflow,elapsed_sec}` | Tab-separated table rows (the `serialize_toon` `table_separator='\t'` mode). |
| `failing_checks` | uniform array, fields `{name,conclusion,workflow_name,job_name,started_at,completed_at,run_id,run_url}` | Empty on full-green; populated on failure or timeout. |
| `wait_outcome` | `completed` \| `deadline_exceeded` | Forwarded verbatim to the resolver. |
| `run_id` | string | First non-empty run id from the checks block. |
| `head_sha` | string | PR head commit SHA. |

## Resolver mapping

The resolver
(`marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_complete_precondition.py`)
classifies each envelope into one of four outcomes. The fixtures in
this directory cover every branch:

| Envelope key combination | Resolver outcome |
|--------------------------|------------------|
| `status: success`, `final_status: success` | `wait_succeeded / ci_final_status: success` |
| `status: success`, `final_status: failure` | `wait_failed / ci_final_status: failure` |
| `status: success`, `final_status: none` | `wait_failed / ci_final_status: no_checks` |
| `status: error` (timeout) | `wait_failed / ci_final_status: timeout` |

## Provenance

Authored 2026-05-24 as part of plan
`ci-complete-resolver-still-mis-maps-green-ci-mock`. Each fixture's
`pr_number`, `run_id`, and `head_sha` values are illustrative and do
not need to correspond to real GitHub artifacts — the fixture-driven
tests assert on resolver-classification keys (`final_status`,
`failing_checks`, `wait_outcome`, `status`), not on identifier round-
trip. If a fixture needs to be regenerated from a live run, use:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  checks wait --pr-number <N> > new-fixture.toon
```
