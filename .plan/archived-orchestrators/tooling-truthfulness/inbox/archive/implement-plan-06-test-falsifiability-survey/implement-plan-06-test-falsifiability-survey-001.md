envelope_version=1
sender_type=plan
sender_id=implement-plan-06-test-falsifiability-survey
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T22:05:32Z

# Candidate lesson (proposal): Seed a rate-window claim from the bot-stated ETA

component=plan-marshall:automatic-review
category=improvement
source_plan=implement-plan-06-test-falsifiability-survey
source_pr=1476

## Problem

The `rate-window claim` verb defaults to a 3600s window when no ETA is
supplied. Twice this run the bot's own rate-limit notice stated a much shorter
reset (3 minutes, 18 minutes), so the default claim overshot the real reset by
an order of magnitude. Both claims were released and re-claimed at the stated
ETA after the mismatch was noticed by hand-reading the PR comments.

## Proposed guidance

Before claiming a rate window, read the latest refusal/rate-limit notice on
the PR for a stated reset interval and pass it as `--window-seconds`. Fall
back to the verb default only when no notice states one. A claim is a
reservation against a real reset clock, not a budget to spend.

## Evidence

- PR #1476 rate-limit notice: "Next included review available in 3 minutes"
  (first recovery; re-claimed at 240s) and "in 18 minutes" (second recovery;
  claimed at 1080s). Both recoveries converged on the re-claimed window.
