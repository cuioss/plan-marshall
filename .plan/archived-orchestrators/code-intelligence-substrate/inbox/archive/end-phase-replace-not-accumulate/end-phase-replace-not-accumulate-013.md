envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T17:25:16Z

component=plan-marshall:phase-5-execute
category=bug
created=2026-07-29

# The first entry into execute is logged as "Re-entering", so the rule built on that distinction fires on correct behaviour

`analyze-logs` observed, for this plan's 5-execute:

```
dispatch_clustering:
  inferred_dispatches: 2
  starting_markers: 0
  re_entering_markers: 2
```

Zero `Starting execute phase` markers, two `Re-entering execute phase` markers, across two dispatch clusters. The first entry into the phase, at 13:12:19, logged:

```
[13:12:19Z] [STATUS] (plan-marshall:phase-5-execute) Re-entering execute phase - 4 tasks pending
```

That was the phase's **first** entry — the plan had just transitioned from 4-plan, the worktree had just been materialized, and all 4 tasks were pending. Nothing was re-entered.

## Why it breaks its own rule

`plan-retrospective`'s RE_ENTRY_COVERAGE rule computes `re_entry_count = (dispatch clusters − 1)` and expects exactly that many `Re-entering` lines. With 2 clusters it expects 1 and observes 2, so the rule reports a mismatch. But the plan's dispatch behaviour was entirely correct: it entered once, checkpointed voluntarily at 14:33 for orchestrator-tier builds, and re-entered once at 14:21 for the lint fix. One genuine re-entry, one genuine first entry.

So the rule fires on a well-behaved plan, and it fires because the emission site does not distinguish the two cases the rule exists to distinguish. The rule's precondition ("at least one `Re-entering` line exists, i.e. the plan ran on a build that differentiates first entry from re-entry") is satisfied by the presence of the line, not by the line being correct — so the precondition guard passes while the differentiation it certifies is absent.

## Root cause

The phase-5 entry path appears to log `Re-entering` unconditionally, or to key the choice off something that is true on first entry too (pending tasks exist, or `worktree_path` already populated — note the paired `Step 2.5 short-circuit: worktree_path already populated` line at 13:11:31 on that same first entry, which would make a "have we been here before" heuristic answer yes).

## Impact

Every plan that enters 5-execute produces a `Re-entering` line for its first entry, so RE_ENTRY_COVERAGE mismatches are systematic rather than diagnostic, and the corpus-level audit that consumes them is reading noise. A real re-entry-logging defect would be indistinguishable from this baseline.

## Suggested corrective action

1. Key the entry log on a genuine first-entry discriminator — whether the phase already has a `start_time` in `work/metrics.toon`, or whether any task has ever left `pending` — and emit `Starting execute phase` on first entry, `Re-entering execute phase` thereafter. Do not key it on worktree presence, which is true on first entry whenever 4-plan pre-materialized the worktree, as it did here.
2. Strengthen the RE_ENTRY_COVERAGE precondition so it certifies what it claims: require at least one `Starting` marker before trusting the `Re-entering` markers, and report `indeterminate` rather than `mismatch` when `starting_markers == 0`. A rule that cannot tell a broken emitter from a broken orchestrator should say so.
3. Add a test asserting that a single-entry phase-5 run emits exactly one `Starting` and zero `Re-entering` lines.
