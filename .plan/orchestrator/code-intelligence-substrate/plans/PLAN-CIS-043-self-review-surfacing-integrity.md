# PLAN-CIS-043: The Self-Review Surface Over-Reports Its Own Coverage Three Ways

epic: code-intelligence-substrate
workstream: WS-05

> Staged 2026-08-09 from the PLAN-CIS-031 drain (inbox `-004`, `-005`) and the
> `review-apparatus-006` hand-over. All three arms **re-grounded first-party at HEAD** before
> staging, per § Structural Findings F0. Self-sufficient spec.

## Objective

`PLAN-CIS-031` shipped delta-scoped self-review rounds (#1126). Three defects in the surfacing
layer make the resulting verdict claim more coverage than it has, and the first two are made
**worse** by the scoping change rather than unaffected by it.

**A — the detector reads a narrower file set than its own sibling.**
`_detect_count_prose` (`_self_review_detectors.py:1070`) opens **only** `{skill_dir}/SKILL.md`.
Its sibling `_collect_skill_contract_sources` in the **same file** (`:276-279`) returns
*"SKILL.md plus every standards/*.md inside the skill directory"*. ⇒ **A stale count in a
`standards/*.md` doc is surfaced by no candidate list — delta round or full.** The closing
full-surface pass is not the backstop a reader assumes: *"full surface"* means the full **file**
surface, not the full **detector** surface. ⭐ On #1126 the two members living in
`ext-point-finalize-step.md` were found **only because a reader was pointed at the file by name**.

**B — two registry entries are counted as examined by nothing.**
`duplicate_claimable_keys` (N21) and `discard_without_report` (N22) carry `in_total: true`, so
they are summed into `counts.total`, into the Step 1b candidate-count **dispatch gate**, and into
the terminal verdict *"self-review clean: {N} candidates examined, no check matched"* — while the
workflow's check list stops at check 15. #1126's own closing verdict reads **"76 candidates
examined"**, two of which nothing examined. ⇒ **Volume-read-as-coverage inside the contract that
exists to detect volume-read-as-coverage.**

**C — a scoped round still reports whole-surface claims.**
`review-apparatus-006` handed over a hard requirement — *"every residual/absence claim must
publish `scope_searched` + `files_scanned`"* — with the reasoning that it *"converts your scoping
change from a risk into a safe one"*. ⛔ **Verified at HEAD: neither token appears anywhere in
`self_review.py` or `pre-submission-self-review.md`.** The message arrived **23 minutes after
CIS-031's `1-init` began** and was never read, so the delta scoping shipped without it.

Their first-party evidence for why this matters, from PR #1087's self-review: round 4 asserted a
literal appeared in *"ZERO test and source files"* while **three survivors were live in merged
main**, because the sweep was scoped to `marketplace/**` and the **claim** said *"test and
source"*. ⇒ ⛔⛔ **A delta-scoped pass is a scope restriction, and this is exactly how scope
restrictions fail — not by missing the delta, but by making a claim wider than the scope
searched.**

## Deliverables

1. **D1 — widen the detector's file set to match its sibling's.** ⛔ **Add a negative-control
   fixture**: a stale count planted in a `standards/*.md` doc MUST be surfaced. A positive-only
   fixture passes against the current broken resolver and proves nothing. ⭐ **Both functions
   resolve one conceptual input — "the docs carrying this skill's contract" — through two file
   sets with no shared resolver and no test pinning agreement.** Fix the asymmetry at the
   resolver, not by editing one call site.
2. **D2 — tie registry membership to check coverage by an invariant.** A registry entry with
   `in_total: true` MUST have a consuming check, enforced by a **population-derived** contract
   test over the registry — ⛔ never a hand-copied list (the standing epic rule: every
   set-guarding detector must be population-derived).
   ✅ **DIRECTION DECIDED BY THE OPERATOR 2026-08-09 — ADD THE TWO CONSUMING CHECKS.**
   `duplicate_claimable_keys` (N21) and `discard_without_report` (N22) each gain a consuming
   check, so `counts.total`, the Step 1b dispatch gate, and the *"{N} candidates examined"*
   verdict **stay at their current magnitude and become honest**.
   ⛔ **Do NOT re-derive this as an open question, and do NOT ship the alternative** — dropping
   `in_total` is recorded as the arm NOT taken. ⭐ **The decision is consistent with the epic's
   standing anti-goal**: dropping `in_total` would shrink the *number* without examining anything
   more, which is the "improve the metric by examining less" shape the #1069 analysis rejects on
   principle rather than on balance. Adding the checks is the arm that increases what is examined.
   ⚠ **Consequence this plan must own rather than discover**: two new checks mean the verdict's
   headline count now corresponds to real examination, so **the dispatch-gate threshold behaviour
   is unchanged by construction** — verify that at outline rather than assuming it.
3. **D3 — every residual/absence claim publishes `scope_searched` + `files_scanned`.** Adopted
   verbatim from `review-apparatus-006`. ⭐ **Adopt the positive shape the same message
   demonstrated**: finding `a494d3` *searched the CLAIM rather than the STRING* — enumerating
   the doc-quoted literals and matching each against the live source symbol — and closed its
   class exhaustively. **That is the shape a scoped round's final confirmation pass should use.**
   ⛔ **`2026-08-02-15-004` binds this plan against itself**: it authors a claim-scoping rule, so
   its own residual claims — in the PR body, in its own self-review rounds, in its report — must
   publish `scope_searched` + `files_scanned` **from round 1**. A rule applied to a sibling's
   work and not to one's own is not yet a rule.
4. **D4 — a mid-run inbox message has no reader; make that visible.** `review-apparatus-006`
   arrived 23 minutes into CIS-031's run and was drained a day after that plan merged, by which
   point its central requirement was unshippable. The drain is an orchestrator-tier act between
   plans, so **a message aimed at a running plan is architecturally undeliverable** and nothing
   says so. ⚠ **Scope carefully — this is a plan-lifecycle-facing deliverable in a WS-05 plan.**
   The minimum honest form is that a message naming a `running` plan is **reported as
   undeliverable at write time**, not silently queued. ⛔ **Do not build a mid-run delivery
   channel** — that is a much larger design question and is not this plan's to answer.

5. **D5 — the doc-claim half of self-review SELF-SEEDS; cap on convergence, not on budget.**
   ⭐⭐ **Folded 2026-08-09 from PR #1127, and it is the SECOND SIGHTING of a mechanism #1126 also
   recorded** — which makes it a pattern rather than an anecdote. On #1127 the self-review ran six
   rounds for **1,008,012 tokens (~60% of all 6-finalize spend)** and **closed on a recorded
   WARNING deviation rather than a clean pass**: the *behavioural* half converged (rounds 4–5 found
   real shipped-code defects, round 6 found none) while the *doc-claim* half did not, **because
   each correction authored new prose for the next round to audit.**
   ⛔ **This is the same shape lesson `2026-08-09-13-001` names** — correction breeds the next
   instance of the class, and only deletion converges — now observed at the level of the **round
   loop** rather than the individual claim.
   **Deliverable**: the termination criterion distinguishes *converged* from *out of budget*, and a
   round whose findings are all newly-authored-prose-about-this-plan's-own-edits is reported as
   **self-seeding** rather than counted as an ordinary non-clean round.
   ⛔ **NOT a round-count reduction** — that anti-goal is inherited verbatim from `PLAN-CIS-031` and
   binds here unchanged. ⚠ Coordinate with D3: publishing `scope_searched` is what makes a
   self-seeded round *identifiable* in the first place.

Five deliverables — at the edge of the split guard. ⚠ **Evaluate the split at outline**: the
natural cut is (D1+D2: what the detector sees) and (D3+D4+D5: what a round CLAIMS about what it
saw).

## Claim Labels

- **OBSERVED (first-party at HEAD, 2026-08-09)**: `_self_review_detectors.py:1070` opens
  `skill_dir / 'SKILL.md'`; `:276-279` documents *"SKILL.md plus every standards/*.md"*.
  The asymmetry is live.
- **OBSERVED (first-party at HEAD, 2026-08-09)**: `grep -n "scope_searched\|files_scanned"` over
  `self_review.py` and `pre-submission-self-review.md` returns **no matches**. Arm C is unshipped.
- **OBSERVED (#1126's own artifacts)**: the closing verdict reads *"76 candidates examined"*;
  `duplicate_claimable_keys` and `discard_without_report` carry `in_total: true` with no
  consuming check.
- **OBSERVED (second-hand, `review-apparatus-006`, flagged as such)**: PR #1087's round-4
  zero-claim with three live survivors at
  `test/plan-marshall/tools-integration-ci/test_ci_base.py:548,561,569`.
  ⛔ **Re-derive at outline before pinning a test to those line numbers** — the sibling epic's
  own caveat discipline applies to material it hands us.
- ⛔ **SCOPED OUT, deliberately**: lesson `2026-07-18-14-001` — *normative worked examples being
  semantically wrong* — is **NOT the same shape** and must not be folded into any deliverable
  here. A worked example that is structurally well-formed and semantically wrong is invisible to
  any sweep-scope discipline. `review-apparatus-006` states this explicitly and warns that
  silently absorbing it reproduces the exact defect.
- **Adjacent corpus**: `review-apparatus` routed a 9-lesson cluster (C18) on self-review
  completeness, snapshots at
  `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`. Read at
  outline; ⛔ **corpus retirement is deferred behind `PLAN-TRUTH-044` — retire nothing.**

## Expected Surface

- **OBSERVED**: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` (D1)
- **OBSERVED**: `.../ext-self-review-plan-marshall/scripts/_self_review_patterns.py` — the registry (D2)
- **OBSERVED**: `.../ext-self-review-plan-marshall/scripts/self_review.py` (D3)
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — the check list and the verdict shape (D2, D3)
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — the contract
- **HYPOTHESIS**: `marshall-orchestrator`'s `inbox write` verb — D4 (verify-at-outline)
- **OBSERVED**: `test/pm-plugin-development/` — tests

## Dependencies and Sequencing

- **Depends on**: nothing. `PLAN-CIS-031` shipped the surface this repairs.
- ⛔ **Never pair with `PLAN-CIS-021`** — same skill (`ext-self-review-plan-marshall`), and
  CIS-021 shipped the `duplicate_claimable_keys` detector arm B now finds uncounted.
  ⚠ **Re-verify against CIS-021's landing before scoping D2** — it may already carry part of it.
- ⚠ **D4 touches the orchestrator inbox surface** — coordinate with nothing currently staged, but
  re-verify at emit.
- ✅ Disjoint from every WS-01/02/04/06 plan.

## Anti-goals

- ⛔ **Do not fold `2026-07-18-14-001`.** Scoped out above, on the sibling epic's explicit warning.
- ⛔ **Do not decide D2's direction inside the plan.** It is an epic-level policy call.
- ⛔ **Do not build a mid-run message delivery channel** under D4.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-043-self-review-surfacing-integrity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
