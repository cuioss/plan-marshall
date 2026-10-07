envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=review-apparatus
kind=finding
created=2026-08-26T21:13:59Z

# Review triage discipline: the rejection half, the acceptance half, and the softening half

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 3 lessons. **Suggested fold target:** yours to decide — they are small and
complementary, and two of them already arrived in your inbox once as delegations from
`truthful-signals` before being captured as lessons.

## Why these three belong together

They close **one** rule from three sides. Each was filed by a different plan on a different
PR; none is a restatement of another.

| Side | Lesson | The rule |
|------|--------|----------|
| **Rejecting** | `2026-08-25-09-016` | A rejection re-checked against the prior verdict is vacuous authority. |
| **Accepting** | `2026-08-25-09-017` | A disposition that ACTS on a finding must cite the same evidence a rejection must. |
| **Softening** | `2026-08-09-22-002` | A review may raise a severity by reasoning; it may not lower one without executing the code. |

## The rejecting half — `2026-08-25-09-016`

PR #1338 carried a landing-facts defect where a failed read reached `complete: true`. **The
run had already considered and dismissed the point.** The recorded sequence:

found internally → partial repair at one of two co-sites → the one-sided repair correctly
reverted (it left the contract self-contradictory) → **the revert was carried forward as a
rejection of the FINDING rather than of the PATCH** → the defect survived to the PR.

Two general mechanisms:

1. ⭐ **A reverted partial fix reads as a refuted finding.** Nothing in the triage record
   distinguishes *"this patch was wrong"* from *"this claim was wrong"*.
2. ⭐ **The rejection was re-checked against the prior verdict, not against the code.** The
   reversal happened only because a later pass explicitly re-traced on source. That re-trace
   was available on the first pass and was not performed.

⭐⭐ **The corroboration structure is itself the finding.** Two bots raised two different
sites of one defect — Sourcery at `emit-landing.md:208`, CodeRabbit at
`landing-payload-spec.md:105-119` — and the correct fix moved both documents in one commit.
**A single-site report is exactly what the earlier rejection had already survived.** It took
the *pair* to make the two-sidedness visible. That is a concrete, measured argument for
reviewer plurality.

## The accepting half — `2026-08-25-09-017`

⭐ **The asymmetry is the finding.** Triage discipline is written almost entirely around
*rejecting*: a rejection must cite evidence, name its sites, survive a re-trace. **Accepting
carries no equivalent obligation**, because acceptance feels like the safe direction.

It is not. An accepted-but-unverified finding writes a change into the tree on the reviewer's
premises, and the pipeline then reports it as resolved-as-`fixed` — ⛔ **the disposition the
corpus scores most favourably is its least-verified one.**

The proposed rule is not a heavier process, it is the *same* one applied symmetrically: a
disposition that acts must cite the same file:line evidence a rejection must.

## The softening half — `2026-08-09-22-002`

**Two independent read-only review passes** — phase-2-refine and phase-3-outline — each
recorded the same severity softening: that a collapsed empty string *"currently fails safe to
`False`"* at its one call site.

⛔ **Executing the pre-fix source refuted it.** The helper returned `True` — it fails **OPEN**,
mis-classifying traversal paths as in-bundle.

⭐⭐ **Independence did not help, because the error was in the method both used, not in either
reviewer.** Two independent reviews agreeing is not corroboration when both used the same
unsound method. ⇒ *A red test proves a test fails. Executing the pre-fix source proves what
the code does.*

## The four concrete proposals across the three

- **A reverted fix re-opens its finding**, carrying the revert sha and reason, so "the patch
  was incomplete" can never be recorded as "the claim was wrong".
- **Record a rejected finding's SITE SET alongside the rejection**, so a rejection is
  falsifiable by a later report naming a site it did not examine.
- **Track reversal rate as a review-apparatus metric** — an internal rejection later reversed
  by an external reviewer is the highest-value signal the pipeline produces about its own
  triage, and it is currently visible only by reading resolution prose.
- **Citing an earlier verdict is inadmissible as the ground of a rejection.**

## Claim labels

- **OBSERVED** — all three instances, each first-hand from a named PR (#1338, #1342, and
  `PLAN-TRUTH-070`/#1132) with quoted disposition text and, for `09-22-002`, the executed
  return value that refuted the softening.
- ⚠ **`2026-08-25-09-016`'s own handling note applies here too**: the comment tallies and
  merge states in it are first-party from `ci pr comments` / `ci pr view`, but the quoted
  disposition prose is the filing plan's own narrative. Treat the prose as a lead.
- **HYPOTHESIS** — that reversal rate is measurable from the existing findings store.
  Confirm/refute at `manage-findings` § the resolution/disposition schema, checking whether a
  reversal is distinguishable from an ordinary `fixed`. Verify-at-outline.
