envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T16:08:45Z

component=plan-marshall:automatic-review
category=bug

# THIRD RECURRENCE: a sourcery rate-limit refusal is credited as review participation

## Observation

On PR #1387, sourcery posted a `review_body` reading: "Sorry @..., you've used your own review budget of 250,000 diff characters for the last 7 days ... You can request another review in 2 days and 13 hours". That is a rate-limit REFUSAL, not a review.

The producer returned `refused_bots[]` empty and credited sourcery as participated on `review_body` evidence, so `review_completeness` reported `participation_complete: true` and a `review_state_summary` of "3 reviewed" when only 2 bots actually reviewed. Neither the `refusal_patterns` registry in `automatic-review/standards/sourcery.md` nor the structural arm recognised the phrasing — the notice frames the budget as "you have used your own review budget of N diff characters", a shape the patterns do not match.

## Recurrence

This is the **third** recorded instance. Prior lessons: `2026-08-25-09-012`, `2026-09-02-08-001`. This run produced the **third acceptance** of the same defect. Three acceptances of one defect is itself the signal: the remedy belongs in a plan that owns `automatic-review/standards/sourcery.md`, not in a fourth finding.

## Recommended rule

Two levels:

1. **Immediate** — extend the sourcery `refusal_patterns` to cover the diff-character-budget phrasing.
2. **Structural** — the pattern registry keeps missing new phrasings because it enumerates known refusal texts. Add a structural arm that treats a `review_body` carrying no actionable comments AND a rate-limit / quota / budget shape as a refusal by default, so an unseen phrasing fails CLOSED (not credited) rather than open (credited as participation).

## Why it matters beyond this run

Contained here only because sourcery is in `optional_bots` on this project, so no quorum or participation gate depended on the miscredit. The same pattern gap on a REQUIRED bot would let a refusal satisfy a participation gate — exactly the false-participation class the bot-participation contract exists to prevent.

## Evidence

- Plan: `output-volume-standard` (epic `operator-ux`), PR #1387
- Q-Gate finding `714552`, phase `6-finalize`, type `bug`, component `plan-marshall:automatic-review`
- Resolution: `accepted` with stated rationale at the wait-region triage gate
- Corroborating plan finding `b07863` (`pr-comment`, sourcery-ai `review_body`) carries the refusal text verbatim
