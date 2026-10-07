envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-10T17:28:33Z

component=plan-marshall:phase-5-execute
category=bug

Relayed from Token-Sheriff PLAN-09 (PR #731 / `b6b1a94d`). ⛔ **A leaf reporting tasks DONE while skipping its own commit step leaves edits uncommitted under a green report** — a false green in the most literal sense, and squarely this epic's subject.

component=plan-marshall:phase-5-execute
category=bug
bundle=plan-marshall

# A phase-5 leaf can report tasks done while skipping the Step 10a commit, leaving edits uncommitted

A dispatched phase-5 leaf returned a completion report naming its tasks as done,
but had skipped the Step 10a commit. The edits were on disk and unstaged; the
return payload said the work was complete. Nothing in the leaf's own report
distinguished "committed" from "edited but not committed", so the orchestrator
carried a wrong belief forward until the tree was inspected for another reason.

The general shape: **a leaf's completion report is a claim about its own
behaviour, and the one thing it cannot be trusted to report is a step it forgot
to run.** A leaf that skips a step also skips the report of having skipped it.

## Solution

Verify the tree rather than trusting the completion report. At the phase-5 task
boundary, check the observable — `git status --short` against the worktree, or
the change-ledger row the commit would have written — instead of accepting the
leaf's `status: success` as evidence that the commit happened.

The durable form of the fix is a dispatcher-side post-return check: a leaf that
declares `mutates_source` and returns success over a dirty tracked tree is
reporting an inconsistent state and should be surfaced, not accepted. Note that
`phase-6-finalize` already applies exactly this pattern for its post-run-review
band (item 5f sub-item 0 observes the checkout on return rather than trusting the
declared `mutates_source` fact) — so the mechanism exists and the gap is that
phase 5's task loop does not have its counterpart.

## Impact

Any plan whose phase-5 work is dispatched to leaves. An uncommitted edit that
survives into phase 6 either rides an unrelated commit or is lost when the
worktree is removed.
