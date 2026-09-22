# PLAN-PR-047: The counting stage reasons from inputs that were never persisted, and each gap changes a published number

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-061` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; D1–D4 are carried there as D8–D11, and **D0 is merged into that plan's D1**
> because it and `PLAN-PR-026` D1 name the same artifact from the producing and consuming side. ⛔
> **This file is NOT dead and is NOT deleted**: it remains the AUTHORITATIVE TEXT of every deliverable
> body, and `PLAN-PR-061` points here rather than retyping it.

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-04 from `truthful-signals-044.md`, itself carrying two first-party observations from
> `documented-invocations-cannot-succeed-as-written` (PLAN-TRUTH-101, PR #1386, merged `71279cc02`,
> 2026-09-03 17:53:36Z). ⛔ **One of the sender's four claims was REFUTED here before staging** — see
> Claim Labels. The spec is staged on the three that survived plus the inverted form of the fourth.

## Objective

The review-measurement stages publish numbers derived from inputs that are **absent, unpersisted, or
contradicted by observation** — and in every case the stage reports a value rather than reporting that
it could not compute one. Five gaps, one theme: *the instrument reasons from inputs nobody guaranteed.*

⭐ **This is distinct from `PLAN-PR-030`**, which owns *the instrument can report our gates perfect*.
That spec already carries seven items and is over the split guard, so these are staged separately rather
than folded — recorded so the omission reads as a decision, not an oversight.

⛔⛔ **The compounding selection effect is the reason this is a MEASUREMENT defect and not a coverage
gap.** On the current finalize ordering, `finalize-step-simplify` (order 8) and
`finalize-step-security-audit` (order 9) mutate source *after* the gates (5, 7), and a forward pass never
re-gates their edits. ⇒ **The only measurable PRs are those where neither step committed anything** —
systematically the PRs that needed no fixing. That is a biased population, not a random sample.

⛔ **The rule to carry regardless of the fix: a run of `excluded` rows across PRs means those PRs were
never measurable. It does NOT mean the gates were clean.**

## Deliverables

### D0 — Persist the reviewed-at-all classification where a post-merge step can read it

`reviewer_coverage` reported `0/3` (`enabled_bots`: coderabbit, pr-agent, sourcery; `reviewed_bots`: none
supplied) because **no persisted reviewed-at-all classification reaches a step ordered at 990, after the
merge gate**. `--reviewed-bots` was therefore supplied bare, which reads as *nobody substantiated as
having reviewed* — an **excluded** PR, never a clean zero.

⭐ **The data exists**: `review_completeness`'s `bot_states`, mapped to `author_login` / `bot_kind`. It is
simply not persisted anywhere a post-merge-ordered step can read it.

*Done when:* the reviewed-at-all classification is persisted into plan state at `automatic-review` time
and read by the retrospective. **Matched negative control required:** a PR where a bot genuinely did not
review still yields an excluded-or-zero reading distinguishable from this one. ⛔ Without D0,
`reviewer_coverage` is `0/N` on **every** run by construction — a vacuous figure, not a measurement.

### D1 — Model the reviewed tree per ROUND, not once per PR

A looped-back PR has **no single reviewed tree**. On #1386 the `pr-comment` findings carried **two**
`reviewed_commit_sha` values — seven at `1e4ef8e7`, three at `49769bd2f` — so `reviewed_head_sha` was
deliberately left empty, because *"deriving one SHA (for instance by taking the newest) would manufacture
a tree identity no reviewer actually reviewed against."*

⭐⭐ **Passing nothing was CORRECT and must stay correct** — the result (`verdict: excluded`,
`exclusion_reason: gate_tree_unsubstantiated`, `structural_share: null`) is honest. Seven escapes were
counted and partitioned (`gate_addressable: 1`, `gate_structural: 5`, `unpartitioned: 1`) with no share
computable.

*Done when:* the gate delta is computed **per round** over each round's own reviewed tree, so a
looped-back PR yields a sequence of measurable rounds instead of one unmeasurable PR. ⛔ The PR-wide
exclusion stays available and stays honest; this adds a level, it does not relax the guard.

### D2 — Give a stored refusal its MODE, because the two modes have different remedies

Sourcery's single record on #1386 was **not a review** — it was a budget-refusal notice, and two sources
disagreed about which kind with **no field to settle it**:

| Source | Classification | Remedy |
|---|---|---|
| the run context | `cause=size`, cap 150000 diff characters against 3202 changed lines — the per-PR ceiling | smaller diff |
| the notice in the findings store | the weekly account quota (250,000 chars / 7 days, reopening in 5d4h) | backoff |

⛔ **These are the two refusal modes the registry deliberately separates** (`sourcery.md:51` declares
`rate_limit_class: hard_quota` for the weekly quota, while `cause=size` resolves `refused_structural` on
its own). Only one of the two reported refusals reached the store.

*Done when:* a stored refusal record carries a mode discriminator (`size` vs `weekly_quota`) derived at
recognition time, and a disagreement between the run context and the stored notice is **reported**, not
silently resolved. ⭐ Adjacent to shipped `PLAN-PR-034` and lesson `2026-09-02-22-001` (*a refusal filed
as a finding*); **what is new is the two-mode discrimination**, which neither covers.

### D3 — Exclude a RECOGNISED refusal from `actionable_count`

Sourcery declares no `review_body_summary_patterns`; the empty default keeps every `review_body` comment
**COUNTED**, which is the fail-closed direction for a finding count (`sourcery.md:20-22`, verified). So
the refusal notice was scored as one **actionable** `review_body` and its `0.0%` resolved-as-fixed is
**arithmetic over a notice**. ⛔ `0.0%` here must not be read as *"Sourcery was wrong about everything"* —
Sourcery produced no review content on that PR at all.

*Done when:* a **recognised** refusal is excluded from `actionable_count`, while the fail-closed *counted*
default stays in force for an **unclassified** body. **Matched positive control required:** an
unclassified `review_body` is still counted — without it the change is a blanket exemption rather than a
recognition-gated one.

### D4 — Reconcile declared `publish_shape` against the observed one, and REPORT the divergence

⛔⛔ **The sender's framing of this gap is REFUTED and the spec deliberately inverts it.** The claim was
that *"the PR-Agent registry doc states this bot posts no inline comments at all"*, so an observed
`kind=inline` record contradicted the registry. **At the registry version that run actually read
(`31d42db87`, which predates PR #1386's merge) the doc declared BOTH shapes** — `issue_comment`
unconditional plus `inline` when `/improve` is enabled — and stated outright: *"An absent inline count is
therefore NOT evidence of non-participation, while a present one IS evidence of participation."* The
observed inline record is what the registry **predicts and endorses**.

⭐ **The real divergence is the opposite one, and it survives:** the Guide `issue_comment` is declared
**unconditional**, yet the run recorded **zero** `issue_comment` records for `cuioss-review-bot`. An
unconditional shape that did not appear is a genuine registry-versus-observation mismatch.

*Done when:* the counting stage compares the registry's declared kinds against the observed kinds — *both
already in hand at counting time* — and a mismatch is **a reported finding, not a silent premise**. ⛔ A
fix must not hard-code either shape: read beside `9f7923` (`github_re_review.py:394`,
`'head_sha_verified': matched_signal == 'review'`, verified first-party), pr-agent's declared and observed
shapes now disagree in **both directions**, and pr-agent is the only REQUIRED bot.

## Claim Labels

- OBSERVED: `reviewer_coverage: 0/3` with `reviewed_bots` unsupplied, because no persisted
  reviewed-at-all classification reaches a step ordered at 990. From the source run's artifact.
- OBSERVED: the `pr-comment` findings carried two `reviewed_commit_sha` values (`1e4ef8e7` ×7,
  `49769bd2f` ×3), so `reviewed_head_sha` was left empty and the PR resolved
  `verdict: excluded` / `exclusion_reason: gate_tree_unsubstantiated`. From the same artifact.
- OBSERVED: `finalize-step-simplify` (order 8) and `finalize-step-security-audit` (order 9) mutate source
  after the gates (5, 7) with no re-gate, so the measurable population is biased toward PRs that needed
  no fixing. From the assessor's own provenance. Confirm/refute against the composed finalize order.
- OBSERVED — **verified first-party at HEAD `cc5ea40a1`**: Sourcery declares no
  `review_body_summary_patterns` and the empty default keeps every `review_body` COUNTED
  (`sourcery.md:20-22`); `rate_limit_class: hard_quota` at `:51`.
- OBSERVED — **verified first-party at HEAD `cc5ea40a1`**: `github_re_review.py:394` reads
  `'head_sha_verified': matched_signal == 'review'` — a derived predicate the issue-comment path can
  never satisfy. This corroborates `9f7923` and this epic's own `e8bde7`.
- ⛔ REFUTED — **recorded so it is not re-adopted**: that the pr-agent registry declared no inline
  comments. At `31d42db87` — the version the source run read — the doc declared **two** publish shapes
  (`issue_comment` unconditional, `inline` under `/improve`) and explicitly warned that a present inline
  count IS evidence of participation. ⇒ The sender's consequence (*"a counting stage that assumed the
  documented shape would have concluded this bot found nothing"*) is backwards. **D4 carries the
  inverted, surviving form: the unconditional Guide `issue_comment` was absent.**
- ⚠ NOT ESTABLISHED: whether the zero-`issue_comment` observation is a fetch/persistence gap or a real
  non-publication by the bot. D4 must derive which; the two have different remedies and only one is a
  registry defect.

## Expected Surface

- OBSERVED: `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `test/plan-marshall/automatic-review/`
- OBSERVED: `test/plan-marshall/finalize-step-review-retrospective/`

## Dependencies and Sequencing

- ⛔ **Overlaps the `automatic-review` scripts and the retrospective** — never concurrent with
  PLAN-PR-030, PLAN-PR-042, PLAN-PR-026, PLAN-PR-043, PLAN-PR-046, PLAN-PR-031.
- ⛔ **NOT a fold onto PLAN-PR-030** despite the shared measurement subject: PR-030 already carries seven
  items, over the split guard. Recorded so the omission reads as a decision.
- ⭐ **Composes with PLAN-PR-046 / PLAN-PR-043**: both key on `participation_evidence` and the refusal
  recognition seam. Whichever lands second re-reads the other's changes rather than adding a parallel
  mechanism.
- ⚠ Re-derive the live-plan collision set before launch.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-047-the-counting-stage-reasons-from-inputs-that-were-never-persisted.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
