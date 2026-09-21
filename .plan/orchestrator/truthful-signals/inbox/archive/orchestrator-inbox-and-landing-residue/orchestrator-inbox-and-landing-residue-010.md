envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T17:02:18Z

component=plan-marshall:automatic-review
category=anti-pattern
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=automated_review

# An internal rejection was reversed only after two external bots re-raised it

## Context

PR #1338 carried a defect in the landing-facts contract: producer instructions routed *any* value that could not be read to the `n/a` token, while the completeness check treats `n/a` at `pr` / `merge_state` as a settled answer. A failed read therefore reached `complete: true` — a could-not-read laundered into a fact, which is the exact archetype this epic exists to close, reproduced inside the epic's own deliverable.

The run had already considered and dismissed this point. From the disposition recorded on the Sourcery finding (`010fc0`):

> "Confirmed and fixed by TASK-015 on this branch. You are right, and **this reverses a prior internal rejection of the same point.** Traced on code rather than on the earlier verdict…"

And from the CodeRabbit finding at the co-site (`638e97`):

> "…the earlier one-sided repair (392743820) **was reverted** because landing-payload-spec.md:105 still defines the answered class as sanctioned for a field the producer could not read. That sentence is the other half of the defect…"

So the sequence was: the defect was found internally → a repair was attempted at one of its two sites → the one-sided repair was correctly reverted (it was incomplete) → and the revert was then carried forward as a **rejection of the finding**, not as a rejection of the patch. The defect survived to the PR and was caught only because two independent external bots raised it at both of its sites in the same review.

## Root cause

Two distinct mechanisms compounded, and both are general.

**A reverted partial fix reads as a refuted finding.** The revert of `392743820` was the right call about the *patch* — repairing `emit-landing.md` while `landing-payload-spec.md:105` still sanctioned the same value leaves the contract self-contradictory. But nothing in the triage record distinguishes "this patch was wrong" from "this claim was wrong", so the revert discharged the finding rather than re-queuing it with a widened site set. A finding whose fix is reverted should return to `pending` with the reason attached; here it left the queue.

**The rejection was re-checked against the prior verdict, not against the code.** The reversal only happened because the run this time explicitly re-traced on source — the disposition names line numbers (`emit-landing.md:147` and `:208`, `_is_unsupplied` at lines 921-922) and the concrete key set (`LANDING_SENTINEL_REJECTING_KEYS` omits `merge_state` and `pr`). That re-trace was available on the first pass and was not performed; the earlier pass consulted the standing verdict. This is the vacuous-authority archetype: an earlier decision is treated as evidence about the code rather than as a claim to be re-derived from it.

The corroboration structure is worth recording too. Two bots, two sites, one defect: Sourcery raised `emit-landing.md:208`, CodeRabbit raised `landing-payload-spec.md:105-119`, and the correct fix (TASK-015) moved both documents together. A single-site report was exactly what the earlier rejection had already survived — it took the pair to make the two-sidedness visible.

## Proposed action

- Make a reverted fix re-open its finding. When a commit that resolves a finding is reverted, the finding returns to `pending` carrying the revert sha and the reason, so "the patch was incomplete" can never be recorded as "the claim was wrong".
- Require a re-trace on source when triage rejects a finding that restates a previously-rejected one. The disposition must name the file:line evidence it was checked against; citing the earlier verdict is not admissible as the ground of a rejection.
- Record a rejected finding's *site set* alongside the rejection. This defect had two co-sites and was rejected on a one-site reading; a rejection that names the sites it examined is falsifiable by a later report naming a site it did not.
- Track reversal rate as a review-apparatus metric. An internal rejection later reversed by an external reviewer is the highest-value signal the review pipeline produces about its own triage, and it is currently visible only by reading resolution prose.

## Evidence

- `manage-findings list --type pr-comment` → `010fc0` (sourcery-ai, `emit-landing.md:208`, `resolution: fixed`) — resolution_detail quoted above
- `638e97` (coderabbitai, `landing-payload-spec.md:119`, Major, `resolution: fixed`) — names the reverted commit `392743820` and the second co-site
- `ac29bf` (coderabbitai review_body) — "Actionable comments posted: 4 … Nothing from this review was declined"
- both findings resolved to TASK-015, which moved `emit-landing.md` and `landing-payload-spec.md` in one commit
- reviewed_commit_sha `a890161aff0f5944916efd7c10dbc0002bdd9131` for every finding in the review
