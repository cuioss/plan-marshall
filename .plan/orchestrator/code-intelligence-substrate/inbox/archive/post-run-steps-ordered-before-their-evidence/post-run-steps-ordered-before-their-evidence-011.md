envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T22:44:03Z

component=plan-marshall:phase-6-finalize
category=improvement
title=Self-review re-sweeps the full surface every round at flat cost - 13 rounds, 2.98M tokens, 42 percent of findings were rework

# The self-review loop is serial in remediation waves, not in defects

## Measured cost of this run

| Metric | Value |
|--------|------:|
| `pre-submission-self-review` dispatches | **13** (3 pre-loop-back-1, 5 post-loop-back-1, 4 post-loop-back-2; last labelled `iteration=10`) |
| Tokens attributable to those dispatches | **2,979,307** |
| Share of all 6-finalize tokens | **56%** |
| Share of the whole plan's tokens | **30%** |
| Findings filed | **19** |
| Tokens per finding | **~157,000** |
| Rounds that found nothing | **4 of 13** (~800K tokens spent proving termination) |
| Findings-per-round sequence | `1,1,0 \| 3,3,1,1,0 \| 4,2,3,0` |

Whole-plan context: **10.06M tokens** for a **26-file** merged diff at
`scope_estimate=single_module` / `change_type=bug_fix` — 7.7x the *error* anchor for that
row, and past the error anchor for `complex+bug_fix` too. `6-finalize` outspent
`5-execute`.

## What the rounds were actually finding

Of the 19 findings, **17** are prose/contract-consistency classes (`contract_drift`,
`same_document_contradiction`, `description_body_drift`, `duplicate_prose`,
`ordinal_reference_stale`). Only **2** are structural (`unreachable_guard`), and both
appeared only *after* an external reviewer forced executable code into a
15-markdown-file changeset. **Self-review filed zero of the two CodeRabbit Majors** that
became TASK-021 and TASK-022.

`ext-self-review-plan-marshall`'s detector families are overwhelmingly doc-consistency
detectors. On a doc-heavy diff the loop converges by **exhausting prose drift** — which
presents as thoroughness (*"214 candidates surfaced"*) but is volume, not coverage. The
volume-read-as-coverage archetype, at the detector-mix level.

## The rework chain — 8 of 19 findings (42%)

1. Rounds 5-7 filed `1b2e2c` / `238d02` / `817d0f` and rewrote three doc sites to say the
   empty-tree guarantee rests on the `mutates_source` **declaration**, not on a runtime
   check. **~690K tokens.**
2. CodeRabbit then said *honesty is not the fix*; TASK-021 added the runtime guard those
   three sites had just finished asserting did not exist.
3. Round 9 filed `d5284d` and `ad17db`, which state it outright: *"the three sites were
   rewritten earlier this session and TASK-021 invalidated all of them."*
4. Round 10 filed `4f34d4` — TASK-021's guard was bound to a worktree `branch-cleanup`
   deletes.
5. Round 11 filed `9c4eae`, `85aeb7`, `f34edf` — **three defects introduced by the fix for
   `4f34d4`**: a stale flag default, a stale anchor sentence, a stale ordinal cross-ref.

So the loop spent three rounds producing prose that was invalidated within two hours, then
three more rounds cleaning up after the fix that invalidated it.

## Was it worth it?

**Rounds 10-11 were worth the whole budget.** `4f34d4` and `c747ba` are two guards whose
`clean: false` arm was structurally unreachable. The suite was green. Without those rounds
PR #1080 merges a fix that can never fire, in a plan whose entire subject was steps running
before their evidence exists.

**Rounds 5-7 were not.** The remediation *class* was wrong, and the correction arrived from
an external reviewer, not from the loop.

## Rule / proposals

- **The loop's cost is flat per round (~230K tokens) regardless of how much moved.**
  Scope each re-run to the paths mutated since the previous round's recorded
  `head_at_completion`, and reserve the full sweep for round 1 and the final confirmation
  round. Nine of the 13 rounds here followed an edit touching 1-3 files.
- **When a round's findings share one discriminator, sweep the CLASS before closing the
  round.** The item-5f porcelain claim was fixed at one site per round for three rounds.
  The discriminators are already machine-readable in the finding titles. This is the
  operational form of the sibling "a named site list is a sample" lesson, applied to
  self-review's own output rather than to a reviewer's.
- **Treat a round whose findings are all doc-consistency as a signal about the detector
  mix, not about the code.** A doc-heavy diff that produces 17 prose findings and 0
  structural ones has not been reviewed for correctness; it has been proofread.
- Supporting datum for the epic: `scope_estimate=single_module` was two bands low here, and
  it is a live input to the `scope_gated_finalize` pre-filter, which **attempted to drop
  `plan-marshall:plan-retrospective` from this plan's own manifest.** It survived only on
  declared-lane immunity — on a run that produced 19 self-review findings and two near-miss
  vacuous guards.

## Impact

`plan-marshall:phase-6-finalize` (`pre-submission-self-review` round mechanics),
`pm-plugin-development:ext-self-review-plan-marshall` (detector mix and class-sweep
behaviour), and the `scope_estimate` heuristic feeding `scope_gated_finalize`.
