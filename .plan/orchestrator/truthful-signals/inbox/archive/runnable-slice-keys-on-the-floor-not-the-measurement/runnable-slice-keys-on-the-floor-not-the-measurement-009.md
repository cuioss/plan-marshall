envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:56:10Z

component=automatic-review
category=bug
created=2026-07-29

# Zero actionable review comments can mean zero review, not a clean review

On PR #1044: sourcery refused (weekly 500000 diff-char quota, hard), coderabbit
refused (rolling window, 22 min out), and pr-agent posted only a content-free
"no major issues" guide. TWO OF THREE configured review bots produced ZERO
review. The operator was offered wait-and-retrigger and explicitly chose
merge-now on green CI + local gates + the plan's own self-review catch. The
`0-actionable` comment count on the finalize step reflects ABSENCE of review
from 2 of 3 bots, not validation of the diff.

## Impact

Never read a `0 actionable comments` / green `automatic-review` step outcome as
proof the diff was reviewed — check which reviewers actually participated
(`ci pr comments`) before trusting a zero-finding count as a clean signal.
