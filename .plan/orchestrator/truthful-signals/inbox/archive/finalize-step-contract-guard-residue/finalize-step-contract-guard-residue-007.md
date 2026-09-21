envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:23:27Z

component=plan-marshall:plan-marshall-plugin
category=anti-pattern
confidence=high
source_plan=finalize-step-contract-guard-residue

# Fail loudly when the seated plugin cache lags the repo source

## Context

Every skill body loaded into this retrospective envelope came from `~/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.1240/skills/...` — the path printed in each skill-load banner, so this is first-party evidence from the session itself.

That seated copy is materially behind the repository source. Two verified divergences:

1. `manage-metrics/SKILL.md` in the cache documents a **6-value** `--termination-cause` enum (`voluntary_checkpoint`, `task_complete_returned_verbatim`, `budget_yield`, `harness_cancellation`, `error`, `clean_exit_queue_empty`) and asserts that unrecognised values are rejected. The repo source documents **12** values and carries a contract test that fails until three enumeration sites agree with the `DISPATCH_TERMINATION_CAUSES` tuple. Argparse confirms 12.
2. The cache's `phase-boundary` output block lacks `prev_close_count`, which the repo source carries.

The operational consequence was nearly a false finding. Reading the seated body against this plan's actual dispatch rows, 10 of 11 rows carried causes absent from the documented enum — a textbook doc-contract-divergence signature, with a plausible severity and a plausible fix. It was refuted only because the repo source was checked before the finding was written. Had the check been skipped, the retrospective would have filed a confident defect against a contract that is correct and test-guarded.

Note also that the dispatching orchestrator stated the session was seated at `0.1.1526` against a cache of `0.1.1539`. The observed seating is `0.1.1240` — lower than both, so the orchestrator's own belief about the seated version was itself wrong.

## Root cause

Nothing in the load path compares the seated cache version against the repository source, and a skill body carries no provenance marker a consuming agent can check. An agent reasoning from a stale body has no signal that it is doing so, and stale contracts read exactly like current ones.

## Proposed action

Surface the seated version and its staleness at load time rather than leaving it to be discovered. Concretely: have the executor or a startup check compare the seated cache version against the marketplace source and emit a WARNING when they diverge, and record the seated version in the plan's decision log so any retrospective can attribute a contract claim to the body it actually read.

As a working rule for agents in the meantime: **verify any documentation-drift finding against `marketplace/bundles/...` before filing it.** A loaded skill body is a cache artifact, not the source of truth.

This is a recurrence of the standing plugin-registry-pin / orphan-GC family rather than a new failure; what is new here is the specific mechanism by which it manufactures a false positive in a quality report.

## Evidence

- session: every `Skill:` load banner resolved under `cache/plan-marshall/plan-marshall/0.1.1240/skills/`
- cache vs repo: `manage-metrics/SKILL.md` 6-value enum vs 12-value enum plus three guarding contract tests
- argparse probe: `--termination-cause` `choices` lists all 12 values
- cache vs repo: `phase-boundary` output block missing `prev_close_count`
- aspect: script_failure_analysis — 9 unique argparse rejections in this plan, the adjacent symptom class
