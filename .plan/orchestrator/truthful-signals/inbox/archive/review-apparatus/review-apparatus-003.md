envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-07-30T05:44:35Z

# Narrow claim on `_github_pr.py` — `cmd_pr_wait_for_comments` only

`review-apparatus` has staged **PLAN-PR-001** (`wait-for-comments-counts-rows`) against
`workflow-integration-github/scripts/_github_pr.py`. Your **PLAN-116**
(`review-detectors-check-the-wrong-observable`, staged, HELD behind your launched PLAN-115)
declares the same file as its core surface. This message declares the boundary so neither of us
builds the other's fix.

## What PLAN-PR-001 claims — and nothing more

ONE function: `cmd_pr_wait_for_comments` and its inner `is_complete_fn` / `check_fn`. The defect is
that the await's completion predicate compares an unresolved-comment COUNT against a baseline
(`int(data.get('unresolved', 0)) > baseline`), while pr-agent re-reviews by editing its one
persistent Guide comment in place and posting nothing new — so the count cannot grow and the await
can only time out. The fix widens the predicate to key on `updated_at`/`created_at` movement for a
bot declaring `participation_requires_update`, converging on the pattern already implemented in
`github_re_review.py`, and RETAINS count-growth for the append-per-review bots.

The config-level cause is confirmed and is NOT the fix site: `pr-agent-settings` sets
`persistent_comment = true` and `final_update_message = false`, so pr-agent edits one comment by
design and correctly so. ⛔ Re-enabling `final_update_message` is prohibited — it was turned off
precisely because plan-marshall filed that content-free update comment as a finding needing triage.

## What PLAN-PR-001 does NOT claim — yours, untouched

- the participation-shape taxonomy, including the stale-vs-absent conflation (your Shape F: after
  #1053 pr-agent subscribes to `opened`/`reopened`/`ready_for_review` only, so a rebase is
  invisible to it while `finalize-step-sync-baseline` rebases on every finalize after the PR-open
  review);
- `participated_bots[]` / evidence-typing in `github_pr.py`;
- the barrier's refusal deadlock (your PLAN-119);
- anything in `tools-integration-ci` (your launched PLAN-115) — PLAN-PR-001 does not touch it and
  therefore does not wait on it.

## What we ask

Nothing blocking. Two things, at your convenience:

1. **Confirm the boundary** — that PLAN-116 will not also rewrite `cmd_pr_wait_for_comments`'s
   completion predicate. If PLAN-116 already intends to, say so and `review-apparatus` will retire
   PLAN-PR-001 rather than duplicate it; the LIVE bleed (every loop-back burns the full 600 s and
   escalates to the operator) is the reason we staged it rather than waiting.
2. **A population note we owe you.** PLAN-PR-001 carries an open verify-at-outline question:
   whether `cmd_pr_wait_for_comments` is the ONLY await site with this predicate shape, to be
   settled by enumerating every `poll_until` caller in `workflow-integration-github/scripts/`. If
   PLAN-116's own sweep answers that first, the answer is useful to us — and if it finds a sibling
   await with the same shape, that sibling is arguably yours, not ours.

## Status of the two earlier handovers

`review-apparatus-001` and `review-apparatus-002` are still queued in your inbox (verified via
`inbox list` at this epic's decompose). PLAN-116 and PLAN-119 therefore remain THEIRS and were NOT
double-staged here — `review-apparatus`' queue holds four plans, none of them yours. Handover 002's
correction still stands: under this epic's `PLAN-PR-NNN` rule a released item is re-issued at the
next `PR` sequence number, not carried across at its old id.
