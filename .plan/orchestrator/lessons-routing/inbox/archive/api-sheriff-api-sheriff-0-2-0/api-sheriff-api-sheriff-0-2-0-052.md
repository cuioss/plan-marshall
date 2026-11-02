envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T19:31:20Z

# Candidate lesson: github_pr fetch_findings drops the inline comments of a later CodeRabbit re-review (plan-marshall:workflow-integration-github)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-22-demo-client-and-doc-leftovers (PR cuioss/API-Sheriff#512), inbox message plan-v02-22-demo-client-and-doc-leftovers-002.

## What happened

`github_pr fetch_findings` stored only CodeRabbit's review summaries for its re-reviews of later heads (64db644 and f7ffa02). It did not store the four inline comments those reviews posted. The plan answered the inline threads directly on the PR instead of through the findings ledger.

## Why it matters

The ledger is the work list for the reply-and-resolve step. A thread that never reaches it is answered only if someone reads the PR by hand, and the plan has no record that it did.

## Suggested direction

Check whether `fetch_findings` pages or de-duplicates review comments by review id, so that a re-review of a newer head is read for its inline comments as well as its summary. Add a case with two reviews on one PR where the second has inline comments.

# Possibly the same cause as a stale executor: `refresh-runtime-stamp` reported as an unknown verb

The same run could not call `plan-orchestrator:orchestrator refresh-runtime-stamp` at emit-landing: the executor (0.1.1977) rejected it as an unknown verb, while the newest cached plugin was 0.1.1986. This is probably executor staleness, which is what a steward run fixes, and not a missing verb. It is filed so that the owner can check that the verb exists in the cached plugin and that emit-landing degrades to the start-time stamp without an error. The plan did report the start-time stamp.
