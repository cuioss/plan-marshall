envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=candidate-lesson
created=2026-08-24T17:53:18Z

component=plan-marshall:automatic-review
category=anti-pattern
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_epic=truthful-signals

# An internal rejection was reversed only after two external bots re-raised it — with the reversal-rate metric proposal

**From:** `truthful-signals` (orchestrator). **DELEGATION** — this is yours under the standing
three-way routing rule (PR/review findings route to `review-apparatus`, and the PR test wins
outright). We have **removed it from our ledger** and stage no plan for it.

## What happened, verified first-party

PR **#1338** (`plan-marshall`, merged `77db1a0d3`) carried a defect in the landing-facts contract:
producer instructions routed *any* unreadable value to the `n/a` token, while the completeness check
treats `n/a` at `pr` / `merge_state` as a settled answer. A failed read therefore reached
`complete: true` — a could-not-read laundered into a fact.

**The run had already considered and dismissed this point.** From the disposition recorded on the
Sourcery finding `010fc0`:

> "Confirmed and fixed by TASK-015 on this branch. You are right, and **this reverses a prior internal
> rejection of the same point.** Traced on code rather than on the earlier verdict…"

Sequence: found internally → partial repair at one of two co-sites → the one-sided repair correctly
reverted (it left the contract self-contradictory) → **the revert was then carried forward as a
rejection of the FINDING rather than of the PATCH** → the defect survived to the PR.

## Two general mechanisms

**(1) A reverted partial fix reads as a refuted finding.** Nothing in the triage record distinguishes
*"this patch was wrong"* from *"this claim was wrong"*, so the revert discharged the finding instead
of re-queuing it with a widened site set.

**(2) The rejection was re-checked against the prior verdict, not against the code.** The reversal
only happened because this pass explicitly re-traced on source — the disposition names
`emit-landing.md:147` and `:208`, `_is_unsupplied` at 921-922, and the concrete key set
(`LANDING_SENTINEL_REJECTING_KEYS` omits `merge_state` and `pr`). That re-trace was available on the
first pass and was not performed. **This is the vacuous-authority archetype** — an earlier decision
treated as evidence about the code rather than as a claim to be re-derived from it.

## The corroboration structure is itself the finding

Two bots, two sites, one defect: **Sourcery** raised `emit-landing.md:208`, **CodeRabbit** raised
`landing-payload-spec.md:105-119`, and the correct fix (TASK-015) moved both documents in one commit.
⭐ **A single-site report is exactly what the earlier rejection had already survived** — it took the
PAIR to make the two-sidedness visible. That is a concrete argument for reviewer plurality, measured
rather than asserted.

## Proposed actions (theirs to accept or refuse)

- **A reverted fix re-opens its finding.** When a resolving commit is reverted, the finding returns to
  `pending` carrying the revert sha and reason, so "the patch was incomplete" can never be recorded as
  "the claim was wrong".
- **Require a re-trace on source when triage rejects a finding that restates a previously-rejected
  one.** The disposition must name file:line evidence; citing the earlier verdict is inadmissible as
  the ground of a rejection.
- **Record a rejected finding's SITE SET alongside the rejection**, so a rejection is falsifiable by a
  later report naming a site it did not examine.
- **Track reversal rate as a review-apparatus metric.** An internal rejection later reversed by an
  external reviewer is the highest-value signal the pipeline produces about its own triage, and it is
  currently visible only by reading resolution prose.

## A second, separate observation on the same PR — your dead-config population is no longer zero

Your corpus note records that pr-agent's last measured PR is **#1129**, the domain-routed charter
landed at **#1130**, and `/improve` at **#1334** ⇒ zero PRs measured under today's config. **#1338 is
a PR under today's config**, and it carries data:

| Author | Comments |
|---|---:|
| `coderabbitai` | 10 |
| `cuioss-oliver` (the plan's own responses) | 7 |
| `sourcery-ai` | 2 |
| `cuioss-review-bot` | 2 |
| **`pr-agent`** | **0** |

`marshal.json` declares `required_bots: pr-agent` and `optional_bots: coderabbit,sourcery`. **The
required bot contributed nothing; the two optional bots produced every actionable finding** — 6 filed,
5 `fixed`, 1 `taken_into_account`. Verified first-party via `ci pr comments --pr-number 1338`
(`total: 21`, `unresolved: 7`). The finalize step's *"0 comment(s) found — 2 reviewed, 1 empty"* is a
**re-review round zero**, not the PR's comment population — reading it as the latter would record this
PR as unreviewed.

⚠ **7 threads remain unresolved on the merged PR**, which is your post-merge-revisit case.

## Handling note

Treat all of it as a **lead**. The comment tally, the merge state, and the finding resolutions are
first-party from `ci pr comments` / `ci pr view` and are cheap to reproduce; the quoted disposition
text is the plan's own narrative and is quoted verbatim rather than paraphrased.
