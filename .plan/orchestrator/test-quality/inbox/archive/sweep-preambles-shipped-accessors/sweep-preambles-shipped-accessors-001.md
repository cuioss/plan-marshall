envelope_version=1
sender_type=plan
sender_id=sweep-preambles-shipped-accessors
epic=test-quality
kind=candidate-lesson
created=2026-09-08T01:45:37Z

# Drift recovery re-dispatches refine, which cannot clear a git-ancestry gate

Re-routed from the global lessons store as `2026-09-08-01-001`. It was filed there
because the finalize dispatcher asserted `orchestrated: false` without running the
orchestration-detection seam; the seam reports `orchestrated: true, epic: test-quality`
for this plan's `source_id`. The global-store copy is the same content.

## Context

Plan `sweep-preambles-shipped-accessors` hit `baseline_drift` at the phase-5-execute
entry gate twice, ~23 minutes apart:

```text
2026-09-07T21:09:49Z  baseline_drift  148442 tokens  20 tool uses  108844 ms
2026-09-07T21:33:11Z  baseline_drift  148063 tokens  25 tool uses  172341 ms
```

The first abort routed to the documented recovery: re-dispatch `2-refine`. Refine ran,
reconciled all 8 findings the baseline check had filed (2 real content conflicts against
upstream #1443 and #1427; the other 6 were an artifact of the locale bug in lesson
`2026-09-07-21-001`), and returned clean. Phase-5 was re-dispatched and aborted with the
identical `baseline_drift`. The leaf refused correctly and stated a third refine would loop.

## Root cause

The two halves of the recovery test different things.

- `2-refine` resolves the drift **as content**: it classifies each reconciliation finding
  and decides whether a deliverable needs re-authoring. On this run it concluded no
  re-authoring was required and deferred the rebase to finalize.
- The phase-5 Step 3 entry gate tests **git ancestry** — effectively
  `git merge-base --is-ancestor origin/main HEAD`.

Refine never advances the branch and never moves `main_sha`, so it cannot change the
predicate the gate evaluates. The second abort was structurally guaranteed, not unlucky.

## Observed impact

- **296,505 tokens** across two phase-5 envelopes that performed no task work — 5.7% of
  the plan's 5.23M-token total — plus a full `2-refine` re-cycle on top.
- The spend is invisible to retrospective waste accounting: `error_total_tokens` counts
  only fatal `error` terminations and `retryable_total_tokens` only
  `blocked_session_restart` + `harness_cancellation`, so a `baseline_drift` row lands in
  neither bucket and both read `0`.

## How the run recovered

The orchestrator diverged deliberately, logging its rationale (decision `c467fd`) under
persona Principle 8 — establish provenance, never blind-retry. It merged `origin/main` by
hand, resolved the 2 genuinely conflicting test files, verified green, and confirmed the
ancestry predicate passes before re-dispatching. Correct, but an improvisation the
documented workflow does not sanction, taken on the third attempt.

## Downstream cost of the hand-merge

The merge left commit `93b22eca6` on the branch. At finalize,
`finalize-step-sync-baseline` then tried `worktree-rebase-to`, which replays the
pre-merge commits and re-hit the conflicts the merge had already resolved, forcing a
second deviation (decision `a489f7`). The classifier reported `no_overlap` while the real
rebase conflicted — the documented best-effort-probe divergence — but the *reason* was the
merge commit the earlier drift recovery created. Neither step documents the interaction.

## Proposed action

1. **Make the drift recovery advance the branch.** The recovery for a git-ancestry abort
   must perform the git-level action the gate tests, either instead of or after the
   `2-refine` content pass. Re-dispatching refine alone is not a recovery for this gate.
2. **Bound the retry on the gate's own input.** The drift counter counts attempts, not
   progress. Refuse a second recovery of the same class when the ancestry predicate is
   unchanged since the previous attempt, and escalate instead.
3. **Teach `finalize-step-sync-baseline` about a merge commit on the branch.** When the
   branch carries one, `worktree-rebase-to` is structurally wrong — detect it and take the
   merge path rather than discovering it through a conflicted rebase.
4. **Count `baseline_drift` spend as waste.** It is a recoverable non-completion that
   performed no work; give it a bucket rather than leaving it outside both.

## Evidence

- `work/metrics-dispatch-boundaries-5-execute.toon` — two `baseline_drift` rows
- decisions `c467fd`, `104e28`, `a489f7`, and `9a64db` / `51056a` / `a6969a` / `b32ad0`
- lesson `2026-09-07-21-001` — the locale bug that inflated 2 real conflicts into 8
