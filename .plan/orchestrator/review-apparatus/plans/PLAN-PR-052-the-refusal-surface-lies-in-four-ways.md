# PLAN-PR-052: The refusal surface lies in four ways, and one of them rewrites itself after the fact

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-057` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; D1, D2 and D4 are carried there as D8, D9 and D11, **D3 and 3a are carried as
> the single D10**, and D0 folds into that plan's merged D0 gate. ⛔ **This file is NOT dead and is NOT
> deleted**: it remains the AUTHORITATIVE TEXT of every deliverable body, and `PLAN-PR-057` points here
> rather than retyping it.

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-06 from the `PLAN-PR-036` landing (`exit-code-convention-stops-at-the-skill-boundary-007.md`),
> findings `260d31`, `bef3a0`, `0e29b2`, `01ff9a`. Every claim below is first-party to that run on
> PRs #1419 / #1423 / #1428 / #1429; the corroborated half is recorded in `landings/PLAN-PR-036.md`.

## Objective

Make a review refusal say which refusal it is, survive being read later, and reach the PR the work
actually landed on.

## Why this outranks its individual severities

**One run lost ≈ 4.5 hours to the refusal surface, and every hour of it came from a DIFFERENT one of
these four defects.** Individually each reads as a papercut; together they mean the epic's whole
refusal-handling stack — classification, escalation, persistence, and routing — is uninformative on
the one path that matters most, the path where no review happened.

⛔⛔ **Two of the four also REFUTE beliefs this epic held and acted on**, which is why they are staged
rather than merely noted: a refuted belief that stays in the corpus keeps producing the behaviour it
justified.

## Problem

**1 — "Review rate limited" names TWO structurally different conditions with OPPOSITE remedies
(`260d31`).** A quota wall is fixed by **waiting**. `@coderabbitai review` being the **INCREMENTAL**
verb with **no unreviewed commit** is fixed by **changing the verb** — waiting does nothing at any
duration. The message does not distinguish them.

⛔ **Four attempts were lost to that conflation, and three were 91–94 minutes apart — which an hourly
quota cannot explain.** What worked was `@coderabbitai full review`, **accepted in 10 seconds on the
same PR and the same HEAD.**

⛔⛔ **REFUTED, do not re-derive**: this epic previously held that closing and reopening a PR pushes
the CodeRabbit window. It does not. Converting the stated ETAs to absolute instants, #1419's
`12:49:31 +38m` and #1428's `13:06:37 +21m` **both resolve to `13:27:3x`** — the same instant, 6
seconds apart, **spanning a close and a fresh open.** The window is **ORG-scoped**: any other PR in
the org spends the same bucket, and no reset mechanism is needed to explain a later shift. Lesson
`2026-09-05-07-008` has been amended in place.

⭐⭐ **SHARPENED 2026-09-07, and the sharpening does NOT overturn the refutation** — both are
load-bearing and neither may be dropped for the other. `truthful-signals-051` item `-003` reports
**six `@coderabbitai` triggers over ~12 hours and five 90-minute waits that produced NO review, because
every trigger RE-ARMED the window**; closing and recreating the PR then obtained a full review in
**under 15 minutes**.

⇒ Close + reopen does not **RESET** the window (the same-instant ETA evidence stands). What is new is
that **triggering actively EXTENDS it.** ⛔ So the harm was never the absence of a close — it was the
repeated trigger. **Read the limit notice BEFORE triggering.**

⛔⛔ **DO NOT inherit the free-OSS-vs-Team explanation** for any of this. One reporting run attributed
its stall to a plan tier, then checked its own persisted envelopes and **retracted**: *"all three, on
both PRs, record `Plan: Team` with the same `0 remain` footer."* A plan-tier cause is **refuted**, not
open.

**2 — `refusal_structural` escalation is UNREACHABLE at the default configuration (`bef3a0`).** The
class exists to escalate exactly the case above — a refusal that no amount of waiting resolves — and
at the shipped defaults nothing can reach it. ⛔ A dead escalation path is worse than none: it reads
as coverage.

**3 — A bot refusal is a MUTABLE surface (`0e29b2`).** #1419's original comment said *"158 files, 58
over the limit of 100"*. **The same `issue_comment` was later EDITED IN PLACE** and now carries a
rate-limit body describing a **63-file diff that did not exist when it was posted.**

⇒ Any corpus that reads refusal bodies after the fact reads a surface that can be rewritten under it.
⭐ This is the sharper form of a shape the epic already carries — a re-review that edits one comment
in place — and it extends it: not only can participation hide in an edit, **the recorded reason can
be replaced by a different reason for a different diff.**

**4 — `automatic-review` does not follow a PR split (`01ff9a`).** #1419 was split into #1423 + #1429.
The findings filed against #1419 were not carried across, the `pr-comment` store stayed **empty**, and
`review-retrospective` returned **`indeterminate` with `reviewer_coverage: 0/3`** on a run where
CodeRabbit had filed **7 findings, 5 of them fixed**. ⛔ The measurement said *no reviewer covered
this* about a run that was reviewed and repaired.

## Deliverables

**D0 — GATE, mutates nothing.** Re-ground all four findings at HEAD. For defect 2, **derive** whether
`refusal_structural` is reachable at the shipped default configuration rather than asserting it, and
publish the configuration population the derivation walked. **HALT and report** if any of the four no
longer reproduces.

**D1 — Classify the refusal by CONDITION, not by message text.** `rate_limited` (wait), and
`no_unreviewed_commit` (change the verb) as separate ingestion verdicts with separate remedies, each
naming the remedy in its own record. *Done when:* an incremental-verb dead end is never reported as a
quota wall, and a test pins that the two conditions produce different verdicts from the same
`"Review rate limited"` string.

⭐⭐ **SECOND-REPO SIGHTING, AND IT SHOWS D1's REMEDY IS NOT EXECUTABLE — folded 2026-09-11 from
`truthful-signals-054.md` item 3** (relayed, Token-Sheriff `lessons-handling-…-049`; the sender rates it
the highest-reuse item of its run). An incremental `@coderabbitai review` on an already-reviewed HEAD
drew *"Already reviewed the last commit. Use @coderabbitai full review …"* as an `issue_comment` —
correctly a decline. The loop then re-triggered, re-declined and escalated (two `escalate_ask` rounds
burned), found only by reading the PR because the envelope said just "a comment was posted".

⛔ **Corroborated first-party at `356973d80`: there is no `full review` form to switch to.**
`coderabbit.md` declares a single `trigger_comment: "@coderabbitai review"`, and `github_re_review.py`'s
generic strategy posts exactly the registry's `trigger_comment`; the string `full review` occurs nowhere
in `automatic-review/` or `workflow-integration-github/scripts/`. ⇒ Classifying `no_unreviewed_commit`
correctly would name a remedy **the apparatus cannot perform**. *Done when (added):* the registry
declares the escalated verb (`@coderabbitai full review`) beside the incremental one, `github_re_review`
can post it, and a `no_unreviewed_commit` verdict on an unchanged HEAD selects it rather than the verb
that just declined. ⚠ **Recognising** that body as a refusal is `PLAN-PR-043` D2's (it already lists
*"Already reviewed the last commit…"*); **acting on it** is this deliverable's — do not double-own.
Surface: `github_re_review.py` added below.

**D2 — Make `refusal_structural` reachable, or delete it.** Both are legitimate outcomes; shipping a
class that cannot fire is not. *Done when:* either a default-config path reaches it (with a test that
exercises that path), or the class is removed and its consumers updated — and the decision records
the rejected arm.

**D3 — Capture a refusal body at ingestion, with its observed-at instant.** A later read compares
against the captured copy and reports a **divergence** rather than silently adopting the new text.
*Done when:* an edited refusal is detectable after the fact, and the corpus can state which reading it
is quoting.

**D4 — Follow the split.** When a PR is split or superseded, the findings and participation records
follow to the successor PRs. *Done when:* `review-retrospective` on a split landing computes over the
successors' comment stores rather than returning `indeterminate` over an empty one, and
`superseded_prs` is the input that drives it — the producer already records it.

**3a — `ci pr wait-for-comments` cannot SEE an in-place refusal edit.** ⭐ **Folded from
`test-suite-anti-vacuity-001.md` item 1 on 2026-09-07**, reproduced across **five** `automatic-review`
FIND passes on PR #1430 and live on main.

This is defect 3's other half and it is why 3 is not merely an archival concern: a refusal that arrives
as an **edit to an existing comment** produces no new comment, so a waiter counting comments never
wakes. ⇒ The mutable-refusal problem costs a **live wait**, not just a corrupted record.

*Done when:* the waiter's satisfying event includes an EDIT to a tracked comment, not only a new one,
and a test drives an in-place refusal edit through the waiter and pins that it wakes.

⭐⭐ **THE MECHANISM IS NOW LOCATED — folded 2026-09-13 from `PLAN-PR-033`'s inbox `-004` (finding
`658eec`, resolved `accepted`, STILL LIVE ON MAIN), observed live on #1473.** The reason the waiter
cannot see an in-place edit is not a missing event subscription: **`pr wait-for-comments` samples each
bot's NEWEST comment BY CREATION TIME** (`_github_pr.py`), so an edit to a persistent walkthrough never
changes which comment is sampled, whatever its `updated_at` says.

⛔ **And the damage is now measured at the CALLER**: `rate_limited_bots[]` named only `sourcery` while
CodeRabbit had in fact refused. ⇒ A caller trusting that list picks **wait-for-silence** when the
correct recovery was **wait-for-window** — the two have opposite costs, and this is the third distinct
consumer this epic has caught routing on a refusal surface that under-reports. *Done when (added):* the
sampling rule keys on the later of `created_at` / `updated_at`, matching the predicate
`github_re_review`'s comment arm already uses, and `rate_limited_bots[]` is derived over the same
population a refusal scan reads. Adds no file surface — `_github_pr.py` is already declared.

⛔⛔ **THIRD SIGHTING OF THE SAME SAMPLING RULE, and this one costs OPERATOR TIME — folded 2026-09-13
from `plan-pr-046`'s inbox `-001` item 1 (finding `2fa992`, live on #1477).** Same newest-comment
sampling, different consequence: **a notice whose stated ETA elapsed HOURS ago is indistinguishable
from a live refusal.** Finalize iteration 1 escalated on a notice posted at 20:31Z and never edited,
and **the operator spent a full 90-minute wait before anything tested whether the window had
reopened**. Only the next iteration's trigger — and the refusal it drew, carrying that trigger's own
invocation hash — established that the quota was genuinely spent.

⭐ **The distinguishing evidence is already in the same fetch and is simply unused**: the notice's
`created_at` / `updated_at`, and the ETA stated in its own body. *Done when (added):* a notice is
classified a CURRENT refusal only when it answers a trigger this run posted (its invocation hash
matches) **or** its stated window has not elapsed; a notice failing both is reported as stale, never as
a live refusal. ⛔ The three sightings are one mechanism with three costs — a missed wake (`052` 3a), a
wrong recovery choice (`658eec`), and a spent 90-minute wait (`2fa992`) — so a fix that addresses one
consumer and leaves the sampling rule alone closes none of them.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — D1: post the escalated `full review` verb; today it posts only the registry's single `trigger_comment`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`
- OBSERVED: `test/plan-marshall/automatic-review/`
- OBSERVED: `test/plan-marshall/workflow-integration-github/`

## Claim Labels

- OBSERVED: `@coderabbitai full review` was accepted in 10 s on the same PR and HEAD where
  `@coderabbitai review` had returned "Review rate limited" four times.
- OBSERVED: three of the four refusals were 91–94 minutes apart — inconsistent with an hourly quota.
- OBSERVED: #1419's ETA (`12:49:31 +38m`) and #1428's (`13:06:37 +21m`) both resolve to `13:27:3x`,
  spanning a close and a fresh open.
- OBSERVED: #1419's refusal `issue_comment` was edited in place; its current body describes a 63-file
  diff that did not exist when it was posted.
- OBSERVED: `review-retrospective` returned `indeterminate` / `reviewer_coverage: 0/3` on #1429 with
  an empty `pr-comment` store, against 7 CodeRabbit findings and 5 fixes.
- ⛔ **RETRACTED, do not re-derive**: "closing and reopening a PR pushes the CodeRabbit window."
  Refuted above. The window is org-scoped.
- HYPOTHESIS: `refusal_structural` is unreachable at the shipped default configuration —
  confirm/refute at
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
  § the escalation-class selection (verify-at-outline). ⛔ **D0 derives this over the configuration
  population rather than asserting it**; an unreachability claim asserted from one config is exactly
  the vacuous-authority archetype this epic keeps re-finding.

## Dependencies and Sequencing

- Depends on: none.
- ⛔ **Overlaps `PLAN-PR-043`, `-045`, `-046`, `-047`, `-048` and `-051`** on the `automatic-review`
  scripts and standards — **sequence, never pair** with any of them.
- ⭐ **Closest neighbour is `PLAN-PR-048` D3** (*rate-limit notices are transport failures, classified
  at ingestion*). D1 here is the **discrimination inside** that classification, and D3 here is its
  **durability**. They are complementary, not duplicates — but if PR-048 is launched first, re-check
  this spec's D1 and D3 against what it shipped before emitting.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-052-the-refusal-surface-lies-in-four-ways.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
