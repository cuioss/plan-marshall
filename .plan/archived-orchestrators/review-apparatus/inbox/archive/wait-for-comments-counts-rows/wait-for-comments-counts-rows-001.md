envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=landing
created=2026-08-01T17:07:47Z

## What landed

**PLAN-PR-001 — `wait-for-comments` count-vs-timestamp blindness** (spec: `plans/PLAN-PR-001-wait-for-comments-counts-rows.md`).

PR: **#1071** — branch `feature/wait-for-comments-counts-rows`.

`cmd_pr_wait_for_comments`'s completion predicate in `_github_pr.py` detected a re-review only by unresolved-comment COUNT growth against a baseline. PR-Agent re-reviews by editing its single persistent Guide comment **in place**, so the count never grows and the await burned its full timeout even when PR-Agent had reviewed correctly and on time (observed: a 23-minute dead await).

The predicate is now widened to detect **movement** — the LATER of `updated_at`/`created_at` strictly after the trigger time — for any bot whose registry record declares `participation_requires_update: true` (PR-Agent today). Count-growth detection is retained unchanged for bots that append a new comment per review (`participation_requires_update: false` — CodeRabbit, Sourcery). The widening is a PORT of the timestamp-movement pattern already implemented in `github_re_review.py`, not a new mechanism.

The plan also separates the **"detector can never succeed"** case (an await whose observable cannot change) from a genuine timeout, so the two produce distinct operator signals.

## Tasks

3/3 done, all under `plan-marshall-plugin-dev`:

1. Widen the wait-for-comments completion predicate to detect in-place re-review edits (implementation, 9/9)
2. Same deliverable, module_testing (3/3)
3. End-to-end regression tests for the widened-predicate arms (1/1)

Tests cover the in-place-edit arm, the mixed-bot arm, and the unanswerable-detector arm; each was verified to fail against the pre-fix predicate.

## Coordination honoured

The population-derivation step named sibling-owned sites and **handed them over rather than absorbing them** — notably PLAN-PR-005's `cmd_fetch_findings` "Pre-filter 5" site. `github_re_review.py` and `bot_registry.py` were read-only reference patterns, not edit targets. No change to PLAN-115 (`tools-integration-ci` plan-less-PR correction) or PLAN-119 (pre-merge refusal-deadlock barrier). `pr-agent-settings`' `final_update_message` was deliberately NOT re-enabled — the fix belongs in the detector, not in reverting the config that suppressed a content-free update comment.

## Residue the epic should track

Five separate messages accompany this landing — four `finding` messages carrying defects surfaced by this run's finalize steps but **not owned by this plan** (all squarely in the epic's automated-PR-review-reliability domain), and one `candidate-lesson`:

- **finding** — `github_pr.py cmd_post_responses` has no already-responded marker (re-transmits on every invocation).
- **finding** — PR-Agent's "## PR Reviewer Guide" boilerplate is missing from that bot's registry `ignore_patterns`, so it lands as a pending hand-triage finding on every PR.
- **finding** — the review-retrospective aggregator maps `resolution: accepted` → `false_positive`, so a clean PR reports PR-Agent as 100% false-positive / 0.0% resolved-as-fixed.
- **finding** — project-local `finalize-step-plugin-doctor` Step 5's WARNING command contains literal semicolons and can never execute under this repo's one-command-per-Bash-call hook.
- **candidate-lesson** — a plan that fixes a finalize-time component cannot have that fix exercised by its own finalize.

## Self-referential note on this run

This plan fixed `wait-for-comments` count-vs-timestamp blindness, and its own finalize `automatic-review` await then **timed out at 192s with `new_count: 0`** — because the code that ran is the installed plugin-cache copy, which is pre-fix. The fix is in the PR, not in the running plugin. Do not read that timeout as evidence the fix is ineffective; it is evidence the fix had not yet been installed. See the accompanying `candidate-lesson`.
