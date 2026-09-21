envelope_version=1
sender_type=plan
sender_id=dispatched-leaf-has-no-search-primitive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:19:05Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# A required review bot reported a green completed check-run while posting zero comments and zero reviews

## Observation

On PR #1046:

- `coderabbit` — a **required** reviewer — reported a check-run with `completed: true` and a green conclusion.
- Across roughly **32 minutes and 24 polls of both the comments endpoint and the reviews endpoint**, it posted **zero comments and zero reviews**.
- `sourcery` **hard-refused** on a weekly rate limit.
- Only `pr-agent` participated, and only with boilerplate.

The finalize step recorded `automatic-review: proceeded unreviewed (coderabbit absent, pr-agent clean)` and `review-retrospective: 1 reviewer compared, 0 actionable, coderabbit absent despite green check`. The operator merged the PR **unreviewed**.

## Why it matters

This is a direct instance of the epic's theme: a confident green signal hiding the caveat that nobody actually looked. The check-run state and the participation state are **independent facts**, and the check-run state is the one that reads as authoritative while carrying none of the evidence.

The existing project rule already says a comment *from* a bot is not a review *by* it, and that only `ci pr comments --pr-number N` is evidence of participation. This run extends that: a **green completed check-run is not evidence of participation either**, and the two-endpoint poll (comments AND reviews) confirming absence is not enough on its own to stop the pipeline — it correctly detected the absence and still proceeded.

## Corrective rule

Treat "required reviewer completed green" and "required reviewer participated" as separate, separately-evidenced predicates. When the detector already knows a required reviewer is absent despite a green check (as it did here — the `display_detail` says so verbatim), that state should be surfaced as a **blocking or explicitly operator-acknowledged** disposition, not folded into a `done` outcome that reads as success.

The detection worked. The **disposition** did not: a correctly-detected refusal was still carried forward as a clean review outcome. That is the same shape as the #1026 finding already in the corpus, recurring.

## Recurrence context

Prior occurrences already recorded: #1026 (a *detected* refusal reported as a clean review); the standing rule that check states lie in both directions; the inverse-polarity case where a GREEN verify was reported as `timeout/-1`.
