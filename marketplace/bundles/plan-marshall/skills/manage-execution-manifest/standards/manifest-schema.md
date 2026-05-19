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
phase_6:
  steps[N]:
    - <step-id>
    ...
```

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

`ci-verify` (lesson-2026-05-18-16-001 deliverable 6) sits between
`create-pr` and `automated-review` so CI verdicts are triaged before
the consumer steps that depend on them.

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
