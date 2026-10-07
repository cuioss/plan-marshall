envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T11:39:44Z

component=plan-marshall:workflow-integration-git
category=anti-pattern
bundle=plan-marshall
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_finding=3c37c8

# A plan that fixes a behaviour must check whether its own contract doc PINS the defect it just removed

## Observation

The plan's core deliverable D1 changed `cmd_worktree_rebase_to` so a rebase replaying zero commits reports
`action: noop` instead of `action: rebased`, and added the payload fields `pre_sha` / `post_sha`.

Its authoritative contract doc, `workflow-integration-git/standards/worktree-handling.md`, was not touched.
Pre-submission self-review found two drifts, both confirmed on disk:

- **(a)** The Output Contract block declared only `action: noop | rebased` and listed neither `pre_sha` nor
  `post_sha`, although `test_ahead_state_leaves_head_sha_unchanged` asserts on both.
- **(b)** The 8-State Matrix rows for `ahead` and `behind` still said *"returns `action: rebased`"*
  **unconditionally**.

Drift (b) is the sharp one. The strictly-`ahead` case is **exactly the case this plan re-verdicts to `noop`**
and that `test_ahead_state_replays_nothing_and_reports_noop` pins. So after the fix landed on the branch, the
authoritative contract document still asserted, in a normative state matrix, the precise behaviour the plan
existed to eliminate.

## Why this is not ordinary doc drift

Ordinary doc drift is a doc that fell behind. This is a doc that **documents the defect as the contract**.
The failure modes are different in kind:

- A stale doc that omits a new field costs a reader a lookup.
- A doc whose normative matrix pins the OLD verdict actively re-teaches the defect. A future author reading
  the matrix would "correct" the fixed code back toward `rebased`, and would believe they were restoring
  conformance while doing it.
- The matrix and the test now assert opposite things about the same state. Whichever one a future reader
  trusts first decides the outcome — and the doc is the one that reads as authoritative.

## Rule

For any plan whose deliverable is *"behaviour X currently reports/does Y; make it report/do Z"*, the
change set MUST include an explicit pass over the artifacts that **state Y as the contract**, not merely the
artifacts that mention the changed symbol:

1. Enumerate every normative statement of the OLD behaviour — state matrices, verdict tables, output-contract
   blocks, "returns ..." rows. Grep for the OLD value (`rebased`), not only for the function name.
2. A state matrix or verdict table is the highest-risk surface, because it reads as normative and is written
   as an unconditional claim per row.
3. Prefer restating the row in terms of the DERIVATION rather than the outcome. The fix here replaced
   "the `ahead` state returns `action: rebased`" with a statement that `action` is derived from the
   pre/post SHA comparison rather than from the detected state — which cannot go stale the next time the
   verdict for one state changes.

## Resolution in-plan

`worktree-handling.md`'s Output Contract now carries `pre_sha` / `post_sha`, the `ahead` / `behind` matrix rows
no longer pin `action: rebased` unconditionally, and a new paragraph states that `action` is derived from the
SHA comparison rather than from the detected state.

## Note on detection route

This was caught by `pre-submission-self-review` via `ext-self-review-plan-marshall`'s contract-drift
candidate surface — not by the plan author, not by the build, and not by CI. Both of this PR's two
self-review findings were contract drift on the plan's OWN deliverable surface, which suggests the
drift-detection value of that step is concentrated exactly where a plan is least likely to look: the
documents describing the thing it just changed.
