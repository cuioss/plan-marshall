envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:52:29Z

component=plan-marshall:audit-archived-plan-retrospectives
category=bug
bundle=plan-marshall

# Both review-bot catches on PR #1086 were the same defect: a new aggregation summed a population it never constrained

`signal_automated_review_count` fired because 2 actionable review-bot findings were remediated in-run. Both were CodeRabbit inline comments on `audit.py`, both in D1's brand-new `billing-composition` check, and both are instances of one shape.

**Catch 1 — `_parse_billing_phase_fields` treated every `[...]` section as a phase.** Any non-phase section in `metrics.toon` carrying the same billing/byte keys was accumulated into `billing_total` and `denom_bytes`, while the omitted-row check still only reported the canonical `_TE_PHASES`. Fixed by restricting parsed sections to `_TE_PHASES` before accumulation; pinned by `TestBillingCompositionCanonicalPhaseScoping`, which compares a body with an added `[totals]` section against the same body without one and guards a non-zero denominator so the equality is not trivially true.

**Catch 2 — `billing-composition_undercounted` double-counted a plan carrying both under-counts.** `unabsorbed_loop_back_plans` and `omitted_row_plans` are independent plan counts; a plan in both was counted twice, so the sum could exceed `plans_in_corpus` and the persisted report diff would show a movement no plan produced. Fixed by returning a distinct `undercounted_plans` computed at the source from the authoritative dataclass rows; pinned by `test_undercounted_plans_counts_a_both_ways_plan_once` plus a matched disjoint-plan control.

## The shared shape

Catch 1 sums over a population **wider** than the declared domain (any bracketed section, not just canonical phases). Catch 2 sums over a population with **overlap** (two non-disjoint plan sets added as if disjoint). Different directions, one root cause:

> **An aggregate was written before its population was pinned down. In both cases the numerator was defined carefully and the set it ranged over was left implicit.**

This is uncomfortably pointed, because D1's *stated purpose* is to make every emitted figure name its population, and D4 of the same plan is literally titled "Verify every emitted figure names its population". The check that exists to enforce population-naming shipped two population bugs. Writing the rule into a check does not make the check's own arithmetic obey it.

## Where the pipeline did and did not catch it

Both defects passed: phase-5 verification, the whole-tree quality gate, `plugin-doctor`, `pre-submission-self-review` (which found and fixed a *different*, real issue — the subagent `cache_read` residual), and `finalize-step-simplify`. Both were caught by an external review bot reading the diff.

The plan's own gates are strong at *contract drift* — the 6-finalize Q-Gate finding `25958b` caught `data-format.md` claiming something the code did not do, entirely on internal review. They are weak at *set arithmetic inside newly-authored aggregation code*, because nothing in the pipeline asks "what set does this sum range over, and is it the declared one?".

## Solution

1. **Make population-scoping an explicit self-review candidate class.** `ext-self-review-plan-marshall` already surfaces deterministic candidates (symmetric-pair functions, flag-guard pairs, producer-consumer pairs). Add: *accumulation loops whose iteration source is not visibly constrained to a declared constant set*, and *sums of two or more independently-derived counts* (candidates for non-disjointness). Both catches here are mechanically detectable from that description.
2. **Pin at the source, not the call site.** Catch 2's fix is instructive and should be generalised: computing `undercounted_plans` inside the function that owns the rows, rather than adding two exported counts at the call site, keeps the semantics in one place. A count derived at a call site from two other counts is a standing smell.
3. **Both fixes carry matched controls** (`[totals]`-section-present vs absent with a non-zero-denominator guard; a disjoint-plan control). Preserve that pattern — it is what keeps the assertions from passing vacuously, which is this project's most-recurring test defect archetype.

## Impact

Applies to any newly-authored aggregation in the audit/metrics surface, which is most of what `code-intelligence-substrate` will produce. The epic's deliverables are, almost by definition, figures computed over corpora. **Every one of them is exposed to this exact defect class**, and this plan demonstrates that the existing internal gates do not catch it — an external reviewer did, twice, on the first instrumentation PR the epic shipped.

**Note for the orchestrator-side pickup:** not present in messages 001-006 — the retrospective's proposals were drawn from metrics/logging/dispatch aspects and did not cover the PR-review findings. Cross-epic routing note: this is *not* a `review-apparatus` item. The PR-review apparatus worked correctly here (CodeRabbit found real defects, both were fixed, `pr-agent` re-reviewed at the new HEAD). The lesson is about the code the review caught, not about the reviewing.
