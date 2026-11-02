envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T17:51:15Z

# Two review-signal traps: bot acknowledgements eat the review allowance, and a stale merge base fakes a weakened test

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-05-response-hygiene (PR #526), candidate lessons 001 and 004. Observed with plugin and executor 0.1.2010 to 0.1.2021.

## Observation

1. CodeRabbit grants one included review per hour on this repository and answers each resolved-thread reply with an in-thread acknowledgement. Those acknowledgements were charged against the allowance: twice an `@coderabbitai review` posted about 90 minutes after a batch of replies came back rate limited. Posting the held replies after the re-review request got a review on the first try.
2. The code-review test-integrity check reported `weakened_test` for an assertion that is present on `origin/main` and missing on the branch. It was base drift (another PR merged after the branch's merge base), not a weakened test. The same false positive has appeared before in other plans.

## What to consider

- When a review round has both held thread replies and a pending re-review request, issue the re-review trigger first and post the replies afterwards.
- Compare the weakened-test check against the current `origin/main`, or report base drift distinctly, instead of comparing against a stale merge base.
