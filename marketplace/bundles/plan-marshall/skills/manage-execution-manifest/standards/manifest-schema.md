# Execution Manifest Schema

The execution manifest is the single source of truth for which Phase 5
verification steps and which Phase 6 finalize steps a plan runs. It is
composed by `phase-4-plan` (Step 8b) and persisted to
`.plan/local/plans/{plan_id}/execution.toon`.

## Schema (TOON)

```toon
plan_id: {plan_id}
manifest_version: 1
phase_5:
  early_terminate: true | false
  verification_steps[N]:
    - <step-id>
    ...
  step_params:
    <step-id>: { <param>: <value>, ... }
    ...
phase_6:
  steps[N]:
    - <step-id>
    ...
  step_params:
    <step-id>: { <param>: <value>, ... }
    ...
```

The in-manifest `verification_steps` / `steps` arrays carry the ordered step-id list (a `list[str]`); the sibling `step_params` map carries each selected step's resolved per-step params alongside it, keyed by the same (bare) step id.

`<step-id>` notation:

- **Built-in (`default:` prefix)** — phase-6 default steps documented
  in [`../../phase-6-finalize/standards/required-steps.md`](../../phase-6-finalize/standards/required-steps.md).
  The `default:` prefix is optional in the manifest — both `commit-push`
  and `default:commit-push` resolve to the same step.
- **Project (`project:` prefix)** — project-local SKILL.md under
  `.claude/skills/{name}/`.
- **Skill (`bundle:skill` notation)** — extension-contributed
  finalize steps registered via the
  `plan-marshall:extension-api/standards/ext-point-execution-context-workflow`
  contract.

## `step_params` — per-step param snapshot + per-plan override

`phase_5.step_params` and `phase_6.step_params` are id-keyed maps (one entry per SELECTED step, keyed by the bare in-manifest step id) carrying each step's resolved per-step param object. They implement the **plan-local tier** of the two-tier source model:

- **Compose-time snapshot** — `compose` reads each selected step's param object from the marshal.json keyed map (`plan.phase-{5,6}-{execute,finalize}.{verification_steps,steps}['{step}']`) and snapshots it into the manifest body. The snapshot is taken at the same write time as the step list (the write-time-snapshot model). marshal.json is the compose-time default; the manifest is the plan-local runtime source.
- **Per-plan override** — `manage-execution-manifest step-params set --step-id {id} --param {k} --value {v}` writes an override into the manifest's `step_params` for that step. A subsequent `step-params get` returns the overridden value — the manifest value wins over the marshal.json default for the remainder of the plan.
- **Runtime read** — phase-5/6 consumers read params via `manage-execution-manifest step-params get --phase {5-execute|6-finalize} --step-id {id}`, returning `{phase, step_id, params}`. This replaces per-field `manage-config get --field {sonar_*|review_bot_buffer_seconds|pr_merge_strategy|…}` reads of step-owned params.

A step with no marshal-side params (e.g. a verify step) snapshots as the empty object `{}`. Only steps that survive selection into the manifest step list are snapshotted.

## Default phase-6 step set

Composed from `DEFAULT_PHASE_6_STEPS` in
`scripts/manage-execution-manifest.py`. The canonical default order:

```
commit-push
create-pr
ci-verify
automated-review
sonar-roundtrip
lessons-capture
branch-cleanup
archive-plan
```

`ci-verify` sits between `create-pr` and `automated-review` so CI
verdicts are triaged before the consumer steps that depend on them.

## Per-producer dispatch fan-out

`ci-verify` is the only built-in step that dispatches the
`verification-feedback` triage workflow once per producer string
(seven possible producers: `ci-verify-{build,policy,timeout,cancelled,
action-required,stale,missing}`). The manifest validator MUST NOT
double-count the per-producer dispatches — they are an internal detail
of the `ci-verify` workflow body, not separate manifest entries. The
manifest contains exactly ONE `ci-verify` row regardless of how many
producer strings the step fans out into at runtime.

## Validation

`manage-execution-manifest validate-loadable` checks that every step
named in `phase_6.steps` resolves to a readable standards file under
`phase-6-finalize/standards/{step}.md`. For `ci-verify`, the
standards file is [`../../phase-6-finalize/standards/ci-verify.md`](../../phase-6-finalize/standards/ci-verify.md).
