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
  The `default:` prefix is optional in the manifest — both `push`
  and `default:push` resolve to the same step.
- **Project (`project:` prefix)** — project-local SKILL.md under
  `.claude/skills/{name}/`.
- **Skill (`bundle:skill` notation)** — extension-contributed
  finalize steps registered via the
  `plan-marshall:extension-api/standards/ext-point-execution-context-workflow`
  contract.

## `phase_6.steps` is the lane-resolved set

The persisted `phase_6.steps` array is the **execution-profile-resolved** finalize-step set, not the raw configured candidate list. `compose` reads the chosen posture from `status.metadata.execution_profile` (absent → `full` → no pruning) and applies the lane cutoff over each element's `lane:` frontmatter block (`class` / `tier` / `cost_size`) — the contract is owned by [`../../extension-api/standards/ext-point-lane-element.md`](../../extension-api/standards/ext-point-lane-element.md). The resolution rules, the twice-compose timing, and the q-gate / derived-state invariants are documented in [decision-rules.md](decision-rules.md) § "Execution-profile lane resolution". Because the same `lanes preview` projection feeds both the `phase-1-init` posture dialogue and this composed manifest, the previewed step set and the executed step set cannot diverge for the config-only part.

## `step_params` — per-step param snapshot + per-plan override

`phase_5.step_params` and `phase_6.step_params` are id-keyed maps (one entry per SELECTED step, keyed by the bare in-manifest step id) carrying each step's resolved per-step param object. They implement the **plan-local tier** of the two-tier source model:

- **Compose-time snapshot** — `compose` reads each selected step's param object from the marshal.json keyed map (`plan.phase-{5,6}-{execute,finalize}.{verification_steps,steps}['{step}']`) and snapshots it into the manifest body. The snapshot is taken at the same write time as the step list (the write-time-snapshot model). marshal.json is the compose-time default; the manifest is the plan-local runtime source.
- **Per-plan override** — `manage-execution-manifest step-params set --step-id {id} --param {k} --value {v}` writes an override into the manifest's `step_params` for that step. A subsequent `step-params get` returns the overridden value — the manifest value wins over the marshal.json default for the remainder of the plan.
- **Runtime read** — phase-5/6 consumers read params via `manage-execution-manifest step-params get --phase {5-execute|6-finalize} --step-id {id}`, returning `{phase, step_id, params}`. This replaces per-field `manage-config get --field {sonar_*|review_bot_buffer_seconds|pr_merge_strategy|…}` reads of step-owned params.

A step with no marshal-side params (e.g. a verify step) snapshots as the empty object `{}`. Only steps that survive selection into the manifest step list are snapshotted.

**Key-normalization invariant for the id-keyed accessor family.** The `step_params` map is keyed by the **bare** step id — the `default:` prefix is stripped before lookup, so `push` and `default:push` resolve to the same entry (the same normalization the step-id notation applies above). Every member of the id-keyed accessor family (`step-params get`, `step-params set`, `record-step`, and any future verb that keys into this map) MUST apply this SAME key-normalization before reading or writing. A newly-added accessor that keys the map by the raw, un-normalized step id silently misses the entry written under the bare key (or writes a duplicate entry under the prefixed key), so a `default:`-prefixed caller and a bare caller diverge. When adding a member to this id-keyed family, normalize the incoming step id the same way the existing members do — the normalization is a property of the family, not of any single verb.

**Step-owned run-at-all / escape-hatch knobs.** The three finalize knobs that each map to exactly one owning step — `simplify` (under `default:finalize-step-simplify`), `self_review` and `drop_review_on_scope_gate` (under `project:finalize-step-pre-submission-self-review`) — are step-owned params folded into their owning step's nested param object in marshal.json's `phase-6-finalize.steps` map. They snapshot into `phase_6.step_params[{owning-step}]` alongside the step's other params whenever that step survives selection. The composer's finalize-selection transform reads them at compose time directly from the marshal.json step map (via the owning step's param object), not from a flat phase-level sibling; `qgate` is the one finalize run-at-all gate that remains a flat `plan.phase-6-finalize.qgate` sibling and is NOT a step-owned param.

## Default phase-6 step set

Composed from `DEFAULT_PHASE_6_STEPS` in
`scripts/manage-execution-manifest.py`. The canonical default order:

```text
push
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
