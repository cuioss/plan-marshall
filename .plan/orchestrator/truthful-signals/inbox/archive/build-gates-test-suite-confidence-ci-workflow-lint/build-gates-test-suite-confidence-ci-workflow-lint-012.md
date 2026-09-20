envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:58:54Z

# ARGUMENT_NAMING findings over a stale executor are unfalsifiable, not defects

component=pm-plugin-development:plugin-doctor
category=bug
confidence=high
source=plan-retrospective
source_plan=build-gates-test-suite-confidence-ci-workflow-lint

## Context

Eight `ARGUMENT_NAMING` findings raised during this run's finalize band turned out to be artifacts of a stale worktree executor rather than source defects. Regenerating the worktree executor cleared all eight with zero source edits.

`project:finalize-step-plugin-doctor` fired 11 times across the run, so the false findings were re-raised on each firing until the executor was regenerated, and each raising cost a triage pass against the wrong artifact.

## Root cause

The `ARGUMENT_NAMING_*` rule cluster resolves argument surfaces through the GENERATED executor, while the finding it emits names a SOURCE file. When the executor is older than the bundle sources it was generated from, every rule in the cluster reports against a surface that no longer exists — and it reports it as a defect in a file that is, in fact, correct. Triage is then sent to the wrong artifact with no signal that the evidence is stale.

This is the repository's standing **stale-cache-as-evidence** archetype, occurring inside a lint gate. It is also, precisely, the theme this epic exists to close: a gate publishing a confident verdict over inputs whose currency it never checked.

## Proposed action

Make the cluster's currency a precondition rather than an assumption:

1. Record the executor's generation-input digest at generation time (the generator already knows its inputs).
2. Before running any rule in the `ARGUMENT_NAMING_*` cluster, compare that digest against the live bundle sources.
3. On disagreement, emit `indeterminate` for the cluster — naming the staleness as the reason — rather than emitting findings. Optionally regenerate and proceed.

An `indeterminate` here is strictly more truthful than either alternative: today's behaviour asserts defects that do not exist, and silently skipping would assert a clean gate the run never earned.

**Sibling, not duplicate.** Carried finding `971613` concerns `population_size` publication across 34 of plugin-doctor's 37 rules. This is a different defect in the same component: those zeros are uninterpretable, whereas these findings are positively wrong.

## Evidence

- 8 `ARGUMENT_NAMING` findings cleared by executor regeneration with zero source edits
- `project:finalize-step-plugin-doctor` `firing_count: 11`, final `display_detail: "plugin-doctor clean: 7 skills gated"`
- aspect: script_failure_analysis — 28 argparse-class failures over 14 unique signatures this run, confirming the argument surface was itself in flux
- aspect: llm_to_script_opportunities — candidate 4, complexity `low`, repetition_count 8
