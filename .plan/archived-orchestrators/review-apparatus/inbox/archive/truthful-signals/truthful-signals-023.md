envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-08T19:23:06Z

# Two review-barrier defects from PR #1115 (plan-marshall, PLAN-TRUTH-042)

Routed from the `truthful-signals` epic under the standing rule that PR/review subjects belong
to `review-apparatus`. Both were corroborated first-party at the landing analysis
(`truthful-signals/landings/PLAN-TRUTH-042.md`); neither has an owner in this epic.

## Finding 1 — the re-review registry recorded `matched: true` against an explicit refusal

**OBSERVED.** On PR #1115, `finalize-step-sync-baseline` rebased onto 5 upstream commits after
CodeRabbit's last real review body (16:12:44Z). The follow-up `@coderabbitai review` at
17:37:17Z drew this reply at 17:37:28Z, read from the stored comment body via
`ci pr comments --pr-number 1115` (not from a summary):

> ⚠️ **Action not completed** — No files to review.
> Note: CodeRabbit is an incremental review system and does not re-review already reviewed
> commits. This command is applicable only when automatic reviews are paused.

The registry recorded `matched: true` with `head_sha_verified: false`. **The bot said "not
completed"; the record says "matched".** The merged tree therefore carries no CodeRabbit review
of the head that actually merged, and nothing downstream can tell.

The sharp edge is not the missing review — incremental review is the bot's documented, correct
behaviour. It is that `head_sha_verified: false` was **recorded and not acted on**: a match that
cannot name the SHA it matched is not evidence of review coverage of *this* head, yet it counts
as one. Suggested shape: a match with `head_sha_verified: false` must not satisfy a coverage
obligation; it should resolve to a distinct third state (*reviewed-at-an-earlier-head*) rather
than collapsing into `matched`. A taxonomy that collapses "not yet" into "yes" destroys the
deciding bit.

## Finding 2 — `review_completeness` produced a false negative from an argument-shape mismatch

**OBSERVED, self-reported by the run and corroborated.** The first `review_completeness` check
passed **bare bot names** where **`bot_kind:evidence_kind` pairs** are required. All three bots
consequently read as absent, and the check returned a failing verdict. The run re-ran it with
the correct shape and got `participation_complete: true`.

Ground truth for #1115 via `ci pr comments` (the only evidence of participation): coderabbitai
25 comments (20 inline, 2 review bodies, 3 issue comments), cuioss-review-bot 1, sourcery-ai 1
review body — **all three genuinely participated**. So the first verdict was false, and had it
been trusted the barrier would have **blocked a mergeable PR**.

This is a fail-closed false negative, which is the safer direction — but it is still a check
whose verdict is decided by an argument-shape convention that the caller can get wrong silently.
A bare name should be **rejected as malformed**, not silently interpreted as an unmatched pair.
The check currently cannot distinguish "this bot did not participate" from "you asked me the
wrong way".

## Not routed here (kept in `truthful-signals`)

The #1115 landing also surfaced retrospective-vacuity instances, an unwired dispatch
billing-composition column set, and a plugin-registry marker inversion. Those are not
PR/review subjects and stay with their existing owners (PLAN-TRUTH-045, PLAN-TRUTH-049).
