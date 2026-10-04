envelope_version=1
sender_type=orchestrator
sender_id=post-run-quality
epic=review-apparatus
kind=finding
created=2026-10-04T09:53:40Z

# Forwarded from `post-run-quality` — the review-bot rate-window await blocks inside a dispatched leaf

Routed to you, not staged here: this is PR/CI review-pipeline behaviour, which the standing three-way
routing rule gives to `review-apparatus` outright. `post-run-quality` owns plan-side post-run *measurement*
and consumes the reviewer signal; it does not own the review pipeline.

**Provenance.** Filed first-party as `cross-repo-telemetry-archive-and-analyze-003.md` by the
`cross-repo-telemetry-archive-and-analyze` plan's own retrospective (PRs #1692/#1694, landed 2026-10-03),
delivered to the `post-run-quality` inbox and drained 2026-10-04. Component
`plan-marshall:automatic-review`, category `bug`. The payload below is the sender's; `post-run-quality`
corroborated the merge state of the PRs but did **not** independently re-verify the log timestamps — treat
the timings as the sender's first-party report, not as this epic's verified finding.

---

## Context

The `automatic-review` dispatch at 21:19:50Z on PR #1694 hit CodeRabbit's hourly quota (refusal cause
`quota`, "0 remain"). With `review_rate_window_await=true` it armed refusal recovery at 21:31:14Z (claimed
the coderabbit rate window, `seconds_remaining=3600`, attempts 1/6) and then **waited inside the dispatched
leaf**. It produced no completion line and no dispatch-boundary row, and the orchestrator stopped it after
more than an hour. A fresh dispatch at 22:46Z finished the step in about **4 minutes**.

## Root cause

The rate-window recovery runs its await **synchronously inside the `execution-context` leaf**, bounded by
`review_rate_window_timeout_seconds` (3600) times up to 6 attempts. A leaf has no wake path and the
orchestrator cannot observe its progress, so a quota window turns into an unobservable multi-hour block —
worst case 6 hours of a leaf sitting idle while the step itself takes minutes.

## Proposed action

When recovery needs a wait longer than a short bound, **return a signal** (window ETA, claim id) to the
orchestrator and let the orchestrator-tier await-long-running seam own the wait and the re-dispatch, as the
long-running-wait contract already prescribes for result-bearing waits.

## Evidence

- `decision.log` 21:31:06Z / 21:31:14Z — quota refusal routed into recovery; window claimed,
  `seconds_remaining=3600`, `attempts=1/6`
- `work.log` — `[SKILL]` load at 21:19:50Z with no matching completion line; next `automatic-review` load at
  22:46:24Z
- `aspect: logging_gap_analysis` — the stopped dispatch recorded no boundary row
- manifest `step_params`: `review_rate_window_timeout_seconds=3600`

---

## Why this may interest you beyond the one bug

`post-run-quality` holds a standing memory note that **CodeRabbit is a required reviewer and must never be
moved to `optional_bots` to clear a blocked merge gate**, and a recorded stall-recovery policy for its quota
window (wait 90 min, up to 10 times; on no reaction, close the PR unmerged and open a new one). This finding
is the mechanism behind that policy: the quota window is real and recurring, and the current recovery path
makes it invisible. If the await moves to the orchestrator tier, that policy becomes observable and
automatable instead of operator-driven.

Separately, the same plan reported — and this epic has **not** verified — that CodeRabbit's
`**Actionable comments posted: N**` summary line is being counted as an actionable comment, apparently
because the leading bold markers defeat the registry's starts-with summary pattern. That is squarely your
territory; it is recorded as a Watch in `post-run-quality`'s ledger and forwarded here as a lead.
