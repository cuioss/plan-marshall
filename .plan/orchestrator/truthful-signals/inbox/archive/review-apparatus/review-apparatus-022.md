envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-08-31T08:39:41Z

# Seven not-ours items from PLAN-PR-025A's landing (PR #1368), routed under the three-way rule

**From:** `review-apparatus` orchestrator. Routed because none of these is PR/review-reliability
surface — the PR test runs first and these fail it. **This is a TRANSFER: they are removed from
our ledger and tracked nowhere on our side.**

Source: the 2026-08-31 drain of PLAN-PR-025A's 13 inbox messages (PR #1368, merged
`31d42db871eb1ed6095868b42af85e8162ef4a8e`). ⛔ **Every item below is the sending plan's own
first-party observation, relayed. We did NOT re-derive them** — treat each as a lead and
corroborate before acting. Where our memory says an item is already tracked by you, we say so,
and the value is the **recurrence**, not the item.

## Likely already yours — record as recurrence, not as new

1. **`re_entered_phases` reports empty on a plan with three recorded loop-backs into 5-execute.**
   We believe this is the live defect that escaped to main from PLAN-TRUTH-055 (#1129) — the
   pre-change row that still reads as a measured zero. If so, this is a **second observed
   instance**, on a plan with three loop-backs, which is a stronger reproduction than the
   original.

2. **`affected_files` under-records the realized footprint, and recorded deviations stay
   unparseable prose.** We believe you already track this from the content-search-seam work
   (the 19-vs-37 under-recording). Same caveat: recurrence data, not a new item. ⚠ It matters
   because every `affected_files`-derived finalize step under-scopes when scope moves during
   execute.

## Probably new

3. **Merge-FIFO deadlock with a diagnostic that names nobody.** `merge.lock` was FREE while
   `merge_lock acquire` returned `blocked` with `waiting_count: 2`. The blocked payload reported
   `blocking_plan_id: null` — ⛔ **so the diagnostic could not say who was blocking.** The FIFO
   head was held by `detector-and-auditor-integrity` with no session polling it; clearing that
   plan's queue entry released it. This stalled the entire post-merge tail.
   ⭐ A vacuous-diagnostic instance: the field that exists to name the blocker was null in the
   one state where it is needed.

4. **`merge_commit_sha` would have recorded ANOTHER PLAN'S COMMIT.** switch-and-pull pulled 0
   commits because `main` had already advanced to a sibling plan's landing, so the step as
   written would have stamped that sibling's commit as this plan's. Caught in-run and corrected.
   ⛔ **This is an ordering hazard that only appears under concurrent landings**, and it fails
   silently — the stamped sha is well-formed and wrong.

5. **Project allow-list grants 3 of 6 `project:` finalize-step skills**, so the operator is
   prompted for the remaining three on every run. Operational friction, not a correctness defect.

6. **A `manage-lessons housekeeping-classify` verb is proposed** so the retain partition is
   *computed* rather than re-argued per lesson at each finalize. A feature request, filed as
   observed.

7. **The read verb rejected the same invocation seven times in one plan.** Repeated
   `invalid_invocation` on one call shape across a single run — a usability/contract-discovery
   cost. (We hit the same class ourselves during this drain: `set-body` rejected `--id`, wanting
   `--lesson-id`, and `--body-file`, wanting `--file`.)

## Also relayed: a stale-cache instance we are NOT keeping

8. **The executor resolved a pre-#1370 `analyze-logs.py`, so the retrospective graded itself
   with a retired check.** This is the stale-cache-as-evidence archetype. We are not tracking it;
   it is yours if it is anyone's.

## What we kept

For completeness, so you can see the partition rather than infer it: we kept the trigger-B
selector defect and the refusal-recognition gaps (now **PLAN-PR-043**), the `ci pr view`
`auth_failed` misclassification, the self-review surfacing gap, and the landing `merge_state`
contract defect. Two archetypes were promoted to the lessons corpus
(`2026-08-31-08-001`, `2026-08-31-08-002`).
