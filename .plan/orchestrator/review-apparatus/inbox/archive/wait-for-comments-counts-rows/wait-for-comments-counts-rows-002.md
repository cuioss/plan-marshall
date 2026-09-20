envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=finding
created=2026-08-01T17:07:53Z

## Finding — `cmd_post_responses` has no already-responded marker; it re-transmits every triaged PR finding on every invocation

**Surfaced by:** PLAN-PR-001 finalize (unified triage, while checking a precondition). **Not this plan's defect.**

**Component:** `plan-marshall:workflow-integration-github` — `github_pr.py` § `cmd_post_responses`.

### Observation

`cmd_post_responses` selects the findings to transmit by testing each finding's resolution against `_RESPONDABLE_RESOLUTIONS`. It carries **no already-responded marker** — nothing records that a given finding's response has already been posted to the PR. Every invocation therefore re-selects the whole set and re-transmits.

The Sonar provider does not have this shape: it carries a documented `responded` marker and skips findings that already carry it. The two providers implement the same verb with different idempotency contracts.

### Why the documented rationale does not hold

`verification-feedback.md` Step 8 asserts the re-transmit is safe because "already-responded findings are terminal and no longer pending".

That reasoning is **inverted**. The selection predicate IS the set of non-pending terminal states — `_RESPONDABLE_RESOLUTIONS` is precisely the terminal set. Saying "terminal findings are not re-selected" is false by construction: terminal is the *selection criterion*, not an exclusion criterion. A finding becoming terminal is what makes it eligible, and it stays eligible forever.

### Blast radius

Bites any plan that loop-backs with several PR comments already triaged: each loop-back iteration re-posts every previously-answered response to the PR, producing duplicate reply comments on the PR thread and additional API traffic.

This run did **not** get bitten, but only incidentally: the findings store held exactly one finding, so a re-transmit was indistinguishable from a first transmit. The n=1 population masked the defect — it is not evidence of safety.

### Suggested direction (not a decision)

Either give the GitHub provider the same `responded` marker the Sonar provider already carries, or make the selection predicate narrower than "the terminal set". Whichever way, the `verification-feedback.md` Step 8 rationale needs rewriting — as written it documents a guarantee the code does not provide.

### Epic relevance

Automated-PR-review reliability: a reviewer-facing surface that duplicates its own output on replay is a truthfulness defect in the review channel, in-domain for `review-apparatus`.
