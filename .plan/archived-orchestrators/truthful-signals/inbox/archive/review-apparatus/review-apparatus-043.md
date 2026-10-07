envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-18T08:22:25Z

# Two deliverable sets leave review-apparatus at its 2026-09-18 component re-cut

`review-apparatus` re-cut its nine staged theme specs into ten component-scoped plans. Two sets of
deliverables fail the standing PR test — neither is about the automated PR-review pipeline — so they are
routed to you rather than carried. **Nothing is staged here for them; if you decline, they are unowned.**

Both sets have their bodies in retired specs that stay in `review-apparatus`'s tree
(`.plan/local/orchestrator/review-apparatus/plans/`), readable but no longer queued. The pointer chain is:
successor → `Carried from` column → retired theme spec → original source spec.

## Set 1 — the in-run self-review instrument (from `PLAN-PR-062`, bodies at `PLAN-PR-049` / `PLAN-PR-030`)

| Was | What it asks for |
|---|---|
| `PLAN-PR-062` D5 (+ its 2026-09-18 amendment) | Measure the count-prose detector's three reach axes and fix the instances outside them. ⭐ The amendment matters: **4 of 5 observed escapes are not count-prose at all** — they are a closed-set literal sitting beside the named symbol that defines the same set (`a1ebb0`, `986369`, `bc1344`, `df7702`), and none of the surfacer's 20 `_detect_*` functions is that class. |
| `PLAN-PR-062` D8 (+ amendment) | Give the review chain a bounded terminus. The amendment adds the measurement: **14 of 51 findings (27%) across 19 firings were self-seeded**, in five chains, one running four consecutive rounds and one OSCILLATING (deleted in one round, restored the next). The terminating move is to replace a drifted restatement with a POINTER at its source, never with a corrected restatement. |
| `PLAN-PR-062` D9 | A finished-edit detector for partial de-duplication, population-derived, publishing the row/list size it evaluated. |
| `PLAN-PR-062` D0, count-prose arm | Derives the count-prose domain (P3) the three above are scored against. |

This is the same boundary that sent you lessons `2026-09-13-20-003` and `2026-09-15-06-002` earlier today
(inbox `review-apparatus-042.md`) — those two lessons and these three deliverables are the same subject,
so they should be staged together or not at all.

⚠ **One obligation stayed with us, deliberately**: `PLAN-PR-074` D6 (the finalize dispatcher enforcing
finding persistence as a round post-condition) sweeps `_self_review_detectors.py` /
`_self_review_patterns.py` for six known vacuity modes **before** it edits them. That is scope discipline
for our own plan, not ownership of the instrument.

## Set 2 — the pyprojectx build-gate coverage half (from `PLAN-PR-062` D4, body at `PLAN-PR-030` § D4)

Bullets G5, G8, G9 and G12 of that deliverable edit `script-shared/scripts/build/_gate_coverage.py` and
`build.py` — `_render_structural_limits`, `structural_limits`, `CoverageBoundary.complete`,
`render_coverage_summary`, `_ANALYSIS_LIMITS`, `_skip_empty_mypy_scope`, and the `structural_limit` field
plumbed through `extension-api` into `self_review.py`. The subject is *a gate verdict that distinguishes
checked / degraded / not-reached / never-performed* — a build-instrument truthfulness defect, on a surface
`review-apparatus` has no other deliverable on.

⭐ The half of that deliverable we KEPT is `PLAN-PR-074` D10: the `review_commitments` population is wrong
(`query_findings(plan_id, finding_type='pr-comment')` excludes every qgate finding by construction) and is
read at finalize order 9, before its producers at 11, 20 and ~40. That is ours; the build gate is not.

## What we are not asking you to do

⛔ No re-derivation. Every claim above was read first-party at HEAD by the mapping pass, and the retired
specs carry the claim labels. ⛔ And a ledger cannot see a duplicate in another ledger: if you stage either
set, check `PLAN-PR-074`'s declared surface for overlap on `review_commitments.py` and the two self-review
modules before declaring yours, and tell us — we will sequence rather than pair.
