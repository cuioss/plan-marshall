envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T11:20:00Z

component=plan-marshall:automatic-review
category=bug
proposed_title=A green CodeRabbit check can mean "we refused to review" — the check is not the review

# A green CodeRabbit check can mean "we refused to review"

## Status

**OBSERVED first-party, TWICE within one hour, on two different PRs.** Not fixed. This is the
cleanest single instance of the epic's theme surfaced so far: a signal that is green *because
the work did not happen*.

## The observation

On PR #1052 (11:09:59Z) the aggregated check list reports:

```
CodeRabbit	SUCCESS	pass	-	-	""
```

while CodeRabbit's own comment on the same PR, same minute, says:

> **Review limit reached** — `@cuioss-oliver`, you've reached your PR review limit, **so we
> couldn't start this review.** Next review available in: **34 minutes**

The check is `SUCCESS`. The review did not happen. The same pair occurred on #1049 at
09:23:24Z, where the identical green check accompanied an identical refusal — and the review
that eventually ran, ~70 minutes later, found **2 actionable issues (1 Major)**. So the green
check was not merely uninformative; it was green over a diff that genuinely contained defects.

## Why this is worse than a missing signal

An absent check reads as "unknown" and a consumer treats it cautiously. A `SUCCESS` check
reads as "reviewed, clean" and a consumer treats it as evidence. The refusal is *legible* — it
is right there in the comment body, machine-readable, with a named reason and a retry window —
but it is legible only on the `pr comments` surface, which no gate consults for this purpose.
The check surface, which gates DO consult, has already collapsed it to `pass`.

**Silence would be safer than this.** The failure mode is not under-reporting; it is confident
mis-reporting.

## Corroborates the existing operating rule

The standing rule "only `ci pr comments --pr-number N` is evidence of participation" is
correct and is now confirmed by direct counter-example rather than by inference. The rule's
converse also holds and should be stated explicitly: **a green bot check is not evidence of
participation, and MUST NOT be read as one.**

Note this is the inverse of the #1026 finding (a *detected* refusal reported as a clean
review). Both directions are now observed. The `review_completeness check` guard DID classify
the refusal correctly on #1049 from the comment surface — so the detector works; the defect is
that a parallel, contradicting, higher-visibility signal exists and is not reconciled against it.

## Proposed action

1. **Never derive participation from a check conclusion.** Where a gate currently reads a bot's
   check state, replace it with the `review_completeness check` verdict, which reads comments.
2. **Reconcile, don't ignore.** When a bot's check is green AND its comment surface reports a
   refusal, that contradiction is itself a finding worth emitting — it is a provider-side bug
   or a semantics mismatch, and either way a consumer is being misled.
3. **Name the refusal reason in the participation verdict** (`refused_awaitable` with the
   window, vs `refused_hard`), so a caller can distinguish "wait 34 minutes" from "wait a week".
   The current run had both simultaneously: coderabbit `refused_awaitable` (34 min), sourcery
   `refused_hard` (weekly quota).

## Evidence

- PR #1052 `checks status` at 11:09Z — `CodeRabbit SUCCESS pass`
- PR #1052 `pr comments` at 11:09:59Z — "Review limit reached … we couldn't start this review"
- PR #1049 same pair at 09:23:24Z; the eventual real review at 10:32:41Z posted 2 actionable
  findings, 1 Major — see messages 011 and 012
