envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:47:21Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
created=2026-07-29

# A canned no-op comment reads like participation: per-bot evidence markers for review coverage

Review-bot participation must be established from a **per-bot evidence marker**, not from the
presence of a comment. Both bots this run emitted text that a reader — and an agent — naturally
scores as "the bot reviewed this", while the bot had reviewed nothing.

## Evidence from PR #1055

- **coderabbit**: "Review finished... does not re-review already reviewed commits" is a **canned
  no-op**. It is emitted whether or not any review occurred, and it reads exactly like a
  completion. The real state was visible only in the **walkthrough comment, edited seconds later**,
  which showed the rate-limited condition. The comment that looked like the verdict was not the
  verdict.
- **pr-agent**: its only reliable evidence is the `Review updated until commit <sha>` line inside
  its **edited-in-place** guide comment. Comment *creation* time proves nothing; the sha in the
  edited body is the fact.
- **Net outcome**: coderabbit never reviewed the final doc-only head despite **three** triggers
  (account rate limits). Operator merged anyway on a documented gap — a legitimate decision, but
  only because the gap was actually detected.

This extends the standing rule that review-bot check states lie in both directions: a comment
**from** a bot is not a review **by** it, and `ci pr comments` returning rows is necessary but not
sufficient.

## Solution

- **Assert per-bot on a sha-bearing marker, not on comment presence.** For pr-agent, parse
  `Review updated until commit <sha>` from the edited body and compare it to the PR head. For
  coderabbit, treat the "does not re-review already reviewed commits" string as a **no-op sentinel**
  that proves absence of review at the current head, not presence.
- **Read edited-in-place bodies, not creation events.** Both bots mutate a single comment. Any
  detector keyed on comment creation is reading a timestamp with no relationship to the review.
- **Re-check the marker against the FINAL head.** A doc-only last commit still needs coverage;
  three triggers producing three no-ops is a detectable, reportable gap, and it must be surfaced to
  the operator as a gap rather than absorbed into a green step verdict.

## Impact

Applies to the `automatic-review` finalize step and to the review-retrospective comparison. The
`automatic-review` display detail this run — "proceeded: pr-agent confirmed 7ec9673, coderabbit
reviewed code at e41cd64" — is the shape to keep: per-bot, sha-bearing, and honest about which
head each bot actually saw.
