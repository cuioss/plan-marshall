envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=landing
created=2026-07-29T16:38:11Z

## What landed

PR #1058 (plan `manage-lessons-mixes-local-time-and-utc`, epic queue ref PLAN-109) — `manage-lessons.py` mixed local time and UTC: `get_next_id()` derived the lesson-id date/sequence prefix from local time while every other date field on the record (retention math, `created`) was UTC, so on days near a UTC-vs-local boundary the id prefix could disagree with the record's own `created` field. Fixed by deriving the id prefix from UTC, matching every other date field.

## D1 gate outcome

D1 (intent classification) was discharged at outline with intent=ACCIDENTAL, on four independent git-history lines of evidence: commit 419e92b46 deliberately converged both sites on UTC; f4c27ac72 (PR #222) then reverted only `get_next_id()` back to local time as a side effect of adding the hour segment; #222's own PR body rationale supports computing `now` once, not local time; and nothing in docs/tests/comments anywhere asserts local ids are intentional. D2 therefore took the UTC-conversion branch, not the inverse (converting the rest of the record to local).

## Hypotheses refuted / corrected

- REFUTED: the spec's hypothesised sequence-allocation collision. `get_next_id()` is the sole allocator and all three reservation scans use the same locally-derived prefix, so the scan was already self-consistent in any zone — no collision existed.
- CORRECTED: the spec's claim that retention arithmetic was off-by-one. Retention was internally UTC-consistent all along; what actually diverged was the *id* relative to every other date field on the same record, not the retention math itself.
- CONFIRMED: same-command date divergence (id prefix vs `created`) was real and deterministic near a UTC/local boundary.

## Test-infrastructure defect found in-flight (not named by the request)

`_FakeDatetime` in `test/plan-marshall/manage-lessons/_lessons_helpers.py` could not express a zone divergence at all — its `now(tz=None)` did a bare tzinfo strip rather than projecting to local time, so a regression test written against it would pass identically whether the local/UTC bug was present or fixed. The freezer itself had to be corrected before the regression test could ever be observed red pre-fix. Filed as a companion candidate-lesson message — a direct match for the epic's "instrument can't see the defect it exists to detect" theme.

## Doc-contract defect this plan itself introduced

CodeRabbit caught a one-line doc-contract defect on a line THIS PLAN authored: `file-format.md` claimed an exact 3-digit sequence width, but `get_next_id()` formats with `:03d`, which is a *minimum*-width format that widens past 999. Fixed via loop-back TASK-4. Filed as a companion candidate-lesson message.

## Signal defects observed during this finalize run (epic inbox residue)

- The build wrapper's outer envelope reported `duration_seconds: 0` for a `module-tests` run that actually consumed 330s and then timed out (the inner log correctly recorded `status=timeout, duration_seconds=330`) — a confident outer signal hiding the real one. Filed as a companion candidate-lesson message.
- `pre-commit-verify-freshness` returned `status=fresh` with `matched_notation: plan-marshall:build-npm:js_coverage` on a Python-only project tree with no JS present anywhere — a mis-attributed ledger match. Filed as a companion candidate-lesson message.

## Review-coverage caveat

Sourcery never reviewed this PR (weekly quota exhausted). CodeRabbit reviewed the first HEAD substantively but refused the second HEAD (the one-line doc fix from the TASK-4 loop-back) on a rate limit — so the final diff that actually merged was seen by `pr-agent` only. Consistent with the epic's standing "review bots lie in both directions" finding; recorded here as additional confirming evidence, not a new lesson.
