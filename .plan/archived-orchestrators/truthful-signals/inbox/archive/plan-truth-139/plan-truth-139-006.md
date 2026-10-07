envelope_version=1
sender_type=plan
sender_id=plan-truth-139
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T14:20:30Z

# Re-fire the pre-push quality gate after the mutates_source steps that follow it

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high
suggested_epic: review-apparatus
source_plan: plan-truth-139
source_pr: 1479

## Context

The gate/review delta instrument on PR #1479 returned `verdict: excluded`,
`exclusion_reason: gate_tree_unsubstantiated`, and withheld `structural_share` as
**null** — not 0. It counted 15 escapes (`gate_addressable: 10`,
`gate_structural: 5`) but could make no claim about gate/review parity.

Two independent reasons excluded it, and both are structural rather than accidental:

1. **The reviewed tree has no single identity.** The `pr-comment` findings carry
   three distinct `reviewed_commit_sha` values — `7e895b76`, `5b9126a4`, `1e2fddb7`
   — because the PR looped back twice and `fetch_findings` pre-filter 5 never
   re-stamps an existing value. No one tree was reviewed in full, so
   `--reviewed-head-sha` was deliberately passed as nothing rather than synthesised
   from the newest: deriving one sha from a mixed set would manufacture a tree
   identity no reviewer ever reviewed against.
2. **The gate tree is not any of them.** Two `mutates_source` steps —
   `finalize-step-simplify` (order 8) and `finalize-step-security-audit` (order 9)
   — run AFTER `pre-push-quality-gate`, so the reviewer saw lines the gates never
   did. The gate tree was `0e8ac4423`, which equals none of the three.

The instrument's own provenance names the consequence: "on the current finalize step
ordering, any step a forward pass reaches at or after the gates whose declaration
says `mutates_source` can land commits the gates never re-ran over — the gate step's
own item-5f commit included, since it lands after the tree it just certified — so the
ONLY measurable PRs are those where no such step committed anything. That is a biased
population, not a random sample, and few measurements will accumulate until the gate
re-fires after those steps."

## Root cause

Ordering. The gate certifies a tree, then three later steps are licensed to change
it, and one of them is the gate's own commit. A run of `excluded` rows therefore
means those PRs were never measurable — never that the gates were clean, which is
exactly the reading the word "excluded" invites.

The security-audit case makes the cost concrete rather than theoretical: that step
hardened 4 files in commit `7e895b76`, after the gate had certified an earlier tree,
and the one boundary it missed became CodeRabbit Major `266f33`. The gate never saw
either the fix or the gap.

## Proposed action

Re-fire `pre-push-quality-gate` after the `mutates_source` steps that follow it, so
the gate tree and the pushed tree are the same tree. Membership of that set should
be read from the step declarations rather than enumerated here, so a step that
declares `mutates_source` later is covered by its own declaration.

Second, smaller part: a loop-back invalidates the delta's *tree identity*, not just a
step's freshness. Three `reviewed_commit_sha` values on one PR is an expected
outcome of loop-back, and exclusion is the instrument's only correct response today.
If the delta is to be measurable on looped-back PRs at all, the per-iteration
stamping needs reconciling — the same `reviewed_commit_sha` re-stamp defect already
noted against the participation ledger.

Until one of these lands, the instrument accumulates nothing on any PR this
project's finalize ordering touches, which is all of them.

## Evidence

- review-retrospective.md § Review-versus-Gate Delta — `verdict: excluded`,
  `exclusion_reason: gate_tree_unsubstantiated`, `structural_share: null`,
  `gate_head_sha: 0e8ac4423`, `reviewed_head_sha: (not supplied)`
- review-retrospective.md § Recommendations items 3 and 4
- aspect: manifest_decisions — `phase_6.steps` ordering: `pre-push-quality-gate` at
  position 3, `finalize-step-simplify` at 6, `finalize-step-security-audit` at 7
- aspect: log_analysis — `pre-push-quality-gate` `firing_count: 7` with
  `head_at_completion 0e8ac4423`, against `automatic-review` `firing_count: 4` and
  three `reviewed_commit_sha` values in the findings store
- The escape that proves the cost: `266f33` (Major, CWE-116) landed in a file the
  security audit had edited in a commit the gate never re-ran over
