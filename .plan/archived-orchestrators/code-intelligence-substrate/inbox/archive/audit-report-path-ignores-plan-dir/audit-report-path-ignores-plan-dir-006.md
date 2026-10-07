envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T09:30:14Z

component=plan-marshall:plan-retrospective
category=bug
title=An unmeasurable footprint must resolve to UNKNOWN, never to an empty set

# An unmeasurable footprint must resolve to UNKNOWN, never to an empty set

## Observation

Three independent consumers converted an *unmeasurable* footprint into a confident wrong verdict during a single plan (`audit-report-path-ignores-plan-dir`, PR #1063):

1. **`check-artifact-consistency`** emitted `affected_files_recall, fail, Recall 0% below 70% threshold` with `found: 0` and all 11 declared files listed as `missing`. The true recall is **100%** — the realized footprint is an exact set match with the declared `affected_files`.
2. **`manage-config build-decision`** returned `decision: not_necessary, reason: plan footprint is empty — no changed files to build`.
3. **The phase-4-plan manifest composer** logged `pre-push-quality-gate omitted — plan footprint is empty — no changed files to build` and dropped the step. It was re-added only because a *separate* rule fired: `ceremony_finalize selection — finalize.qgate=always`.

## Mechanism

The footprint is derived live from the plan's worktree. In cases (1) and (2) the worktree had already been removed at finalize, so the derivation returned `[]`. In case (3) the composer ran at **phase-4-plan**, when the footprint is *necessarily* empty because nothing has been implemented yet.

In all three the predicate is the same: `if not footprint: → "nothing to build" / "recall 0%"`. There is no third state. "I could not measure this" and "I measured this and it is empty" collapse into one branch, and the branch that wins is the confident one.

Case (3) is the dangerous one: **the only thing standing between this plan and shipping with no pre-push quality gate was an unrelated `qgate=always` config setting.** A project without that setting would have had the gate silently pruned by a measurement taken before the code existed.

## Rule

- Every footprint consumer returns a **tri-state**: `measured` / `empty` / `unavailable`. `unavailable` grades as SKIP or UNKNOWN and MUST NOT satisfy a "nothing to do" branch.
- A footprint-emptiness predicate evaluated **before phase-5** is `unavailable` by construction, never `empty`. Manifest composition must not prune a build/verify step on a pre-execution footprint read.
- Post-worktree-removal is a recoverable state, not an unavailable one. This retrospective reconstructed the exact 11-file footprint with two deterministic commands:

  ```
  git merge-base origin/main origin/feature/{branch}
  git diff --name-only <base> origin/feature/{branch}
  ```

  Fold that fallback into the shared footprint resolver so all three consumers inherit it rather than each degrading independently.

## Relation to the epic

This is the `confident-signal-hides-a-caveat` archetype in its purest deterministic form: the signal is not merely optimistic, it is *inverted* — 0% reported where the truth is 100%. It is also a fourth instance of the standing "empty store means UNKNOWN, not NEGATIVE" rule already recorded for worktree-scoped merge-lock reads.
