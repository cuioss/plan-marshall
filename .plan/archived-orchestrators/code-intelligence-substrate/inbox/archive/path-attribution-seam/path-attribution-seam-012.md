envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T20:48:44Z

component=plan-marshall:manage-status
category=improvement
bundle=plan-marshall

# `config_hash` drifted at 4 of 4 phase boundaries on a plan that changed no configuration — an invariant that warns at every boundary discriminates nothing

## What happened

`summarize-invariants` over PLAN-CIS-023 reported seven drift findings. Four of them are `config_hash`, one per recorded boundary — that is **every** boundary the plan crossed:

```text
config_hash,1-init,2-refine,93acf2ec06e7525e -> d99761ec7d492858
config_hash,2-refine,3-outline,d99761ec7d492858 -> 5c58dcd5af91733e
config_hash,3-outline,4-plan,5c58dcd5af91733e -> e8e8b3ea69f878ad
config_hash,4-plan,5-execute,e8e8b3ea69f878ad -> c7935ba60629440a
```

Five distinct hashes across five phases, each raised as a `severity: warning` finding.

The plan's realized footprint is 21 files: `marketplace/bundles/plan-marshall/**`, `test/plan-marshall/**`, `doc/concepts/*.adoc`, and one SVG. **No configuration file is among them.** The plan did not edit `marshal.json` or any config surface, and the first three drifts all occurred before any upstream absorption (the first baseline reconcile was at 17:24Z; the last config drift was at 13:26Z).

## Why this is worth reporting rather than dismissing

The other three drift findings are informative and correct:

- `main_sha` `4-plan → 5-execute` — expected; that is where the worktree materialises.
- `task_state_hash` twice — expected; 4-plan created 11 tasks and 5-execute completed them.

Those three tell a reader something. `config_hash` firing at 4 of 4 boundaries tells a reader nothing, because there is no boundary at which it *didn't* fire. An invariant whose warning is unconditional carries no information: it cannot distinguish the plan that genuinely mutated shared configuration mid-flight — which is a real hazard worth blocking on — from the ordinary case.

This is the same failure shape the epic tracks as the vacuous guard, in its inverted form. The usual vacuous guard never fires and therefore detects nothing. This one *always* fires and therefore, equally, detects nothing. Both are predicates whose output is independent of the input.

## What needs determining first

Two explanations fit the evidence, and they need different fixes, so the diagnosis must precede the change:

1. **The configuration genuinely changed four times** during a 3-hour window in which the plan touched no config file. If so, the interesting question is what mutated it, and the invariant is doing its job while the mutation is the defect.
2. **The hash covers volatile content** — plan-scoped config written during the run (2-refine logged `Config: compatibility=breaking` and `Config: simplicity=lean`), or the execution manifest composed at 13:17Z, or anything else that legitimately changes as the plan progresses. If so, the invariant is hashing a moving target and the fix is to narrow its input to the shared configuration it is meant to guard.

The plan's own artifacts cannot settle this: `marshal.json` lives under `.plan/` and is not in git history, so the "did it actually change" question is not answerable from the plan directory alone. That is why this is filed as an observation to determine rather than a defect to fix.

## The rules

**Do X — treat "this invariant fired at every boundary" as a signal about the invariant, not about the run.** A drift check that never reports agreement has no baseline, and its warnings are unactionable by construction.

**Do X — measure the fire rate of every boundary invariant across a corpus before trusting any single plan's drift report.** A 4-of-4 rate on one plan is suggestive; the same rate across the archived corpus is conclusive, and `audit-archived-plan-retrospectives` is the natural place to compute it.

**Not Y — do not raise a `warning`-severity finding for a condition that holds unconditionally.** It trains readers to skip the whole drift block, which is where the two genuinely-informative `task_state_hash` findings live.

## Detection

Cheap and corpus-shaped: for each of the six expected invariants, compute `drift_count / boundary_count` across archived plans. Any invariant at or near 1.0 is non-discriminating; any at 0.0 is vacuous in the other direction. Both ends deserve the same scrutiny.
