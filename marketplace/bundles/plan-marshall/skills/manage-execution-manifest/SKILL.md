---
name: manage-execution-manifest
description: Compose, read, and validate the per-plan execution manifest that drives Phase 5 verification and Phase 6 finalize step selection
user-invocable: false
scope: plan
---

# Manage Execution Manifest Skill

Compose, read, and validate the per-plan **execution manifest** — a small declarative artifact emitted at the end of `phase-4-plan` that names the exact Phase 5 verification steps and Phase 6 finalize steps for this plan. Phases 5 and 6 become dumb manifest executors; per-doc skip logic in their standards is removed in favor of this single source of truth.

This skill is **script-only**: it has no user-invocable command and is not loaded into LLM context via `Skill:` directives. It is invoked exclusively through the 3-part script notation `plan-marshall:manage-execution-manifest:manage-execution-manifest`. Per the project memory's plugin.json registration rules, it MUST NOT be registered in `plugin.json`.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- The manifest file is the single source of truth for Phase 5/6 step selection — every decision MUST be reflected in the manifest, and every reasoning MUST be logged via `manage-logging decision`.
- The manifest stays lean and diffable. Do not embed reasoning, timestamps, or free-text fields — push those to `decision.log`.
- `compose` is idempotent: re-invocation overwrites the previous manifest. Callers responsible for re-entry semantics.
- The seven-row decision matrix is authoritative. See [decision-rules.md](standards/decision-rules.md) for the canonical table.

## Storage Location

The manifest is stored in the plan directory:

```
.plan/local/plans/{plan_id}/execution.toon
```

TOON format. Manifest schema:

```toon
manifest_version: 1
plan_id: {plan_id}

phase_5:
  early_terminate: false
  verification_steps[N]:
    - quality-gate
    - module-tests
    - coverage

phase_6:
  steps[M]:
    - commit-push
    - create-pr
    - automated-review
    - sonar-roundtrip
    - knowledge-capture
    - lessons-capture
    - branch-cleanup
    - archive-plan
```

### Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| `manifest_version` | int | Schema version (currently `1`) |
| `plan_id` | string | Plan identifier (echo) |
| `phase_5.early_terminate` | bool | If `true`, Phase 5 transitions directly to Phase 6 without running tasks (analysis-only plans with empty affected_files) |
| `phase_5.verification_steps` | list[string] | Ordered list of Phase 5 verification step IDs (e.g., `quality-gate`, `module-tests`, `coverage`). Empty list means no verification needed (e.g., docs-only plans) |
| `phase_6.steps` | list[string] | Ordered list of Phase 6 finalize step IDs to dispatch. Subset of the canonical step set: `commit-push`, `create-pr`, `automated-review`, `sonar-roundtrip`, `knowledge-capture`, `lessons-capture`, `branch-cleanup`, `archive-plan`, `record-metrics`, `review-knowledge`, `lessons-integration` |

---

## Operations

Script: `plan-marshall:manage-execution-manifest:manage-execution-manifest`

### compose

Compose and write the execution manifest from inputs gathered at the end of phase-4-plan.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  compose \
  --plan-id {plan_id} \
  --change-type {change_type} \
  --track {simple|complex} \
  --scope-estimate {none|surgical|single_module|multi_module|broad} \
  [--recipe-key {recipe_key}] \
  [--affected-files-count {N}] \
  [--phase-5-steps {step1,step2,...}] \
  [--phase-6-steps {step1,step2,...}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (kebab-case)
- `--change-type` (required): `analysis|feature|enhancement|bug_fix|tech_debt|verification`
- `--track` (required): `simple|complex` — outline track from phase-3-outline
- `--scope-estimate` (required): `none|surgical|single_module|multi_module|broad` — from solution outline metadata (deliverable 2)
- `--recipe-key` (optional): If the plan was generated via a recipe (e.g., `lesson_cleanup`)
- `--affected-files-count` (optional, default 0): Count of affected files surfaced by the outline; used by the `early_terminate` rule
- `--phase-5-steps` (optional): Comma-separated candidate Phase 5 verification step IDs from `marshal.json` (e.g., `quality-gate,module-tests,coverage`). The decision matrix selects a subset. If omitted, defaults to `quality-gate,module-tests`.
- `--phase-6-steps` (optional): Comma-separated candidate Phase 6 finalize step IDs from `marshal.json` (e.g., `commit-push,create-pr,automated-review,sonar-roundtrip,knowledge-capture,lessons-capture,branch-cleanup,archive-plan`). The decision matrix selects a subset. If omitted, defaults to the full canonical set.

**Output** (TOON):
```toon
status: success
plan_id: my-plan
file: execution.toon
created: true
manifest_version: 1
phase_5:
  early_terminate: false
  verification_steps_count: 2
phase_6:
  steps_count: 6
rule_fired: surgical_tech_debt
```

### read

Read the manifest as TOON.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  read --plan-id {plan_id}
```

**Output** (TOON): the full manifest content (see schema above), wrapped with `status: success` and echoed `plan_id`.

### validate

Verify the manifest schema and that all step IDs exist in the candidate `marshal.json` set.

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  validate --plan-id {plan_id} \
  [--phase-5-steps {step1,step2,...}] \
  [--phase-6-steps {step1,step2,...}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--phase-5-steps` (optional): Comma-separated allowed Phase 5 step IDs to validate against
- `--phase-6-steps` (optional): Comma-separated allowed Phase 6 step IDs to validate against

**Output** (TOON):
```toon
status: success
plan_id: my-plan
valid: true
phase_5_unknown_steps_count: 0
phase_6_unknown_steps_count: 0
```

On failure: `status: error`, `error: invalid_manifest`, plus a `message` and per-section unknown-step list.

---

## Scripts

**Script**: `plan-marshall:manage-execution-manifest:manage-execution-manifest`

| Command | Parameters | Description |
|---------|------------|-------------|
| `compose` | `--plan-id --change-type --track --scope-estimate [--recipe-key] [--affected-files-count] [--phase-5-steps] [--phase-6-steps]` | Compose and write execution.toon |
| `read` | `--plan-id` | Read manifest as TOON |
| `validate` | `--plan-id [--phase-5-steps] [--phase-6-steps]` | Validate manifest schema + step IDs |

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `invalid_plan_id` | plan_id format invalid |
| `file_not_found` | execution.toon doesn't exist (read/validate) |
| `invalid_change_type` | --change-type not in the valid enum |
| `invalid_scope_estimate` | --scope-estimate not in the valid enum |
| `invalid_track` | --track not `simple` or `complex` |
| `invalid_manifest` | Manifest schema invalid or step IDs unknown |

---

## Decision Rules

The seven-row decision matrix is documented in [standards/decision-rules.md](standards/decision-rules.md). The matrix maps the inputs (`change_type`, `track`, `scope_estimate`, `recipe_key`, `affected_files_count`) to:

- `phase_5.early_terminate` (true/false)
- The subset of `phase_5.verification_steps` chosen from the candidate set
- The subset of `phase_6.steps` chosen from the candidate set

For each rule fired, `compose` emits one `decision.log` entry via `manage-logging decision` with the canonical prefix `(plan-marshall:manage-execution-manifest:compose)` and the rule name. This satisfies the request example "one entry per decision".

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-4-plan` | compose | Emit manifest as terminal step before phase transition (Step 8b) |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-5-execute` | read | Read `phase_5.early_terminate` and `phase_5.verification_steps` to drive verification dispatch |
| `phase-6-finalize` | read | Read `phase_6.steps` to drive finalize-step dispatch loop |
| `plan-retrospective` | read | Cross-check manifest assumptions against end-of-execute diff |

## Related

- `manage-references` — Plan-scoped references including `affected_files` and `scope_estimate` consumed by the composer
- `manage-logging` — Decision-log target for the per-rule reasoning entries emitted by `compose`
- `manage-config` — Source of `marshal.json` candidate Phase 5/6 step lists
