envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T14:12:32Z

component=plan-marshall:automatic-review
category=bug
created=2026-10-09

# Move the review rate-window wait out of the leaf that cannot sleep

## Context

After the first fix round on PR #1724 (plan `plan-lb-29-harness-sync`) the automatic-review step re-requested a CodeRabbit review. The bot refused with a quota notice. The step followed its documented recovery: it claimed the rate window (3600 seconds, attempt 1 of 6) and entered the wait loop, which paces itself with `sleep`. The harness rejects a standalone `sleep 30` or `sleep 60` inside a dispatched step, so the loop could not run. The step returned `blocked` with a reason that is not one of its declared return shapes, left the claim held, and marked nothing. The dispatch cost 174,457 tokens and bought no review. The main session then applied the operator's standing policy by hand (two 90-minute waits).

The step also reported that its first re-review call awaited 600 seconds, overran the 600-second command limit, and was moved to the background by the harness.

## Root cause

The recovery path is specified for a context that can wait, and it is executed in one that cannot. Two further mismatches make it unworkable even with pacing: the claim window (3600 seconds) equals the wait budget (3600 seconds), so the wait would time out at about the moment the window opens; and the wait is far longer than the 900-second budget of the find step.

## Proposed action

- Split the recovery: the dispatched step claims the window and returns a declared `rate_window_wait_required` shape carrying bot, head, expiry and attempt count; the main session owns the wait through its long-running seam and re-dispatches the step after expiry.
- Declare that return shape in the workflow's output contract so the dispatcher can route on it.
- Make the wait budget longer than the claim window, and cap any single await inside the step below the command time limit.
- Add a test that the documented leaf path contains no standalone `sleep`.

## Evidence

- aspect: logging_gap_analysis — 6-finalize dispatch terminations include 1 `error` row of 174,457 tokens at 2026-10-09T07:38:23Z.
- aspect: chat_history_analysis — step report: "this envelope's harness blocks the standalone sleep 60 the poll loop requires", `reason: rate_window_wait_not_executable_in_leaf`, "This is not one of the workflow's declared return shapes".
- work log — WARNING 15fc47: "Stopped in rate-window Branch 3: harness blocks the standalone sleep the poll loop needs".
