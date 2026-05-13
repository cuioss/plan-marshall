---
name: finalize-step-pre-submission-self-review
description: Finalize-phase wrapper that runs the pre-submission structural self-review — deterministic candidate surfacing (tools-self-review:self_review surface) + LLM cognitive review dispatched under --phase phase-6-finalize (no --role; tracks phase-6-finalize.default)
user-invocable: false
allowed-tools: Bash, Read, Task
order: 7
---

# Finalize Step: pre-submission-self-review

## Purpose

Structural self-review before `commit-push`: catches missing initialization in symmetric save/restore pairs, regex/glob over-fit, ambiguous user-facing wording, duplicate prose sections covering the same contract, and schema/contract drift. The class of defects PR-review bots reliably surface but local quality gates systematically miss.

This step is **meta-project-only** — registered in the plan-marshall repo's own `marshal.json` because the contract-drift check is load-bearing for the marketplace's own LLM-driven development cycle. Consumer projects rarely benefit (the deterministic helper usually produces a 0-candidate run on application code), so the manifest composer drops the step from `default:` finalize manifests.

## Interface Contract

Invoked by `plan-marshall:phase-6-finalize` for projects that include `project:finalize-step-pre-submission-self-review` in their `phase-6-finalize.steps` list.

Accepts the standard finalize-step arguments:

- `--plan-id` — plan identifier (required)
- `--iteration` — finalize iteration counter (accepted for contract compliance)

MUST be ordered **before** `default:commit-push` in the steps list.

## Workflow

The full workflow body (deterministic surface + dispatch of the LLM cognitive review + outcome bookkeeping) lives in [`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-submission-self-review.md`](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-submission-self-review.md). Execute that document end-to-end; this wrapper exists so the step appears as a `project:` entry in the meta-project's manifest rather than as a `default:` entry shipped to every consumer.

The LLM cognitive review the orchestration prose dispatches lives in [`marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md). The dispatch resolves under `--phase phase-6-finalize` (no `--role`; pre-submission-self-review tracks `phase-6-finalize.default`) via `manage-config effort resolve-target --phase phase-6-finalize`; the workflow doc is the addressable target.

## Error Handling

| Scenario | Action |
|----------|--------|
| Missing `tools-self-review` skill | Fatal config error — the project opted into the wrapper without the dependency |
| Deterministic helper exits non-zero | Halt with `outcome=failed`; surface helper error in `display_detail` (no LLM dispatch) |
| LLM workflow returns non-empty `findings` | Halt with `outcome=failed`; operator must address every finding before re-running |
| Empty `findings` list | Mark step `done` with the workflow's `display_detail` payload |

## Related

- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-submission-self-review.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-submission-self-review.md) — manifest-step orchestration (deterministic surface + dispatch)
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md) — LLM cognitive review workflow (the dispatch target)
- [marketplace/bundles/plan-marshall/skills/tools-self-review/](../../../marketplace/bundles/plan-marshall/skills/tools-self-review/) — deterministic candidate-surface helper
