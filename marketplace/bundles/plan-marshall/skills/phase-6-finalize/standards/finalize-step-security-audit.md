---
name: default:finalize-step-security-audit
description: Proactive phase-6 security-audit pass — runs the shared five-stage security-audit engine over the plan's live footprint, layering each affected domain's skills_by_profile.security skills onto the action-general context; declared mutates_source so the dispatcher's commit instrumentation ships any hardening edits before the push barrier
persona: persona-security-expert
order: 9
mutates_source: true
default_on: true
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
configurable:
  - key: security_audit
    default: auto
    description: Run-at-all gate (auto|always|never) for the proactive security-audit sweep — auto defers to the security_audit_inactive pre-filter; always forces the step in; never forces it out.
---

# Finalize Step: security-audit

Proactive security-audit pass for the `default:finalize-step-security-audit` finalize step. Runs the shared five-stage security-audit engine over the plan's live footprint before the `push` barrier, applies any hardening edits directly to the worktree, and lets the dispatcher's commit instrumentation commit them. This is the proactive, ship-time complement to the on-demand `recipe-security-audit` command: the recipe runs a security review when a user asks for one; this step runs it automatically on every feature/bug-fix/tech-debt plan that touched files.

The step reuses the engine **additively at stage 3 only** — it supplies each affected domain's `skills_by_profile.security` skills (the `extra_security_skills` input) on top of the action-general context set. Stages 1, 2, 4, and 5 are unchanged; this step never re-authors an engine stage. See [`../../recipe-security-audit/standards/audit-engine.md`](../../recipe-security-audit/standards/audit-engine.md) for the normative engine contract and the `extra_security_skills` plug-in surface.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `finalize-step-security-audit` in `manifest.phase_6.steps` (bare name — the manifest holds un-prefixed step ids; the dispatcher prepends `default:` when looking up the dispatch-table row). The step is gated into the manifest at composition time by the two `manage-execution-manifest` decision surfaces described in **Activation and skip-reason** below, so this executor is never dispatched for the plans those surfaces exclude.

## Activation and skip-reason

Two independent composition-time surfaces decide whether `finalize-step-security-audit` lands in `manifest.phase_6.steps` (both owned by `manage-execution-manifest` — see [`../../manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md)):

1. **The `security_audit_inactive` pre-filter** — drops the step when `change_type ∉ {feature, bug_fix, tech_debt}` OR `affected_files_count == 0`. This is the change-shape gate: a pure-analysis / verification plan, or a plan that touched zero files, has no change surface worth a proactive security sweep.
2. **The `plan.phase-6-finalize.security_audit` run-at-all gate** (`auto` default | `always` | `never`, read via `manage-config plan phase-6-finalize step get --step-id default:finalize-step-security-audit`, reading `params.security_audit`) — the operator override applied by the finalize-selection post-matrix transform. `auto` defers to the `security_audit_inactive` pre-filter; `always` forces the step in even when the pre-filter would have dropped it; `never` removes it unconditionally.

**Visible skip-reason**: whenever the step is skipped, the composer emits a decision-log line to the plan's `logs/decision.log` naming which surface fired, so the omission is observable rather than silent. A `record-step` row with `outcome: skipped` is additionally appended to the manifest's `execution_log[]` when the dispatcher resolves the step as absent.

## Two-layer focused-context model

The security review is focused along two layers, both supplied at stage 3 of the engine:

1. **Action-general layer** — `plan-marshall:persona-security-expert`: OWASP Top Ten, STRIDE, trust-boundary and secure-coding principles. Applies to every audit regardless of domain.
2. **Profile × domain layer** — for each domain in the stage-2 affected-domain set, the resolved `skills_by_profile.security` skill (e.g. `pm-dev-java:java-security`, `pm-dev-python:python-security`, `pm-dev-frontend:javascript-security`, `pm-dev-oci:oci-security`, `pm-dev-java-cui:cui-http`). Supplied as the engine's `extra_security_skills` input.

The action-general layer is constant; the profile × domain layer is the focused, footprint-relevant security knowledge that makes the review concrete for the languages the plan actually touched.

## HEAD-dependency

`finalize-step-security-audit` is a member of `HEAD_DEPENDENT_STEPS` (see `phase-6-finalize/SKILL.md`). Because it applies hardening edits directly to the worktree — which the dispatcher's commit instrumentation (`phase-6-finalize/SKILL.md` Step 3 item 5f) commits after the step records `done`, advancing HEAD — a loop-back fix task that advances HEAD past the recorded `head_at_completion` MUST re-fire this step so the audit runs against the newer tree. Capture `git rev-parse HEAD` immediately before the terminal `mark-step-done` call and forward it via `--head-at-completion {sha}`.

## Inputs

- `--plan-id` — plan identifier (required).
- `--iteration` — finalize iteration counter (accepted for contract compliance).
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All git commands and edits below MUST target `{worktree_path}`.

The step derives the plan's live footprint on demand from the worktree (engine stage 1) — it never audits files the plan did not touch.

## Workflow

### Step 1: Resolve the affected domains and their security skills

The engine's stage 1 (footprint) and stage 2 (affected domains) run as documented in the engine contract. From the stage-2 affected-domain set, resolve each domain's `skills_by_profile.security` skills via the Extension API to assemble the `extra_security_skills` input:

```bash
python3 .plan/execute-script.py plan-marshall:extension-api:extension-api resolve-skills \
  --profile security --plan-id {plan_id}
```

Capture the resolved per-domain `security`-profile skill set as `{extra_security_skills}`. A domain that declares no `security` profile contributes nothing (the resolver skips absent keys).

### Step 2: Load the security persona and invoke the shared engine

Load the action-general security identity in-context:

```text
Skill: plan-marshall:persona-security-expert
```

Invoke the shared five-stage engine documented at [`../../recipe-security-audit/standards/audit-engine.md`](../../recipe-security-audit/standards/audit-engine.md), supplying `extra_security_skills = {extra_security_skills}` at stage 3 ONLY (stages 1/2/4/5 run unchanged). The engine reads the in-footprint files, reasons about each against the loaded security knowledge plus the per-domain security skills, applies hardening edits directly to the worktree, and emits findings to the triage pipeline.

Do NOT re-author the engine stages here — follow the engine contract verbatim.

### Step 3: Capture HEAD, mark step done, and return commit_message

The hardening edits are applied directly to the worktree by the engine. This step does NOT commit them — the dispatcher's commit instrumentation (`phase-6-finalize/SKILL.md` Step 3 item 5f) commits any `mutates_source: true` step's output after it records `done`, using the `commit_message` this step returns.

Capture the live HEAD for the HEAD-dependency contract:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture as `{head_sha}`. Then mark the step done, forwarding the SHA:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step finalize-step-security-audit --outcome done \
  --head-at-completion {head_sha} \
  --display-detail "Security audit: {applied_edits} edits, {findings_count} findings"
```

Return a `commit_message` element in this step's return TOON so the dispatcher's instrumentation uses it when committing the applied edits (when no edits were applied the porcelain check is empty and the dispatcher commits nothing, so the returned message is simply unused):

```toon
status: done
display_detail: "Security audit: {applied_edits} edits, {findings_count} findings"
commit_message: "fix(security): apply security-audit hardening in {plan_id}"
```

### escalate_ask no-mark invariant

When the audit surfaces a finding that needs a user decision (a hardening edit that could break a consumer, or an ambiguous risk acceptance), return `status: escalate_ask` WITHOUT calling `mark-step-done` — the dispatcher owns the continuation and re-dispatches the step after the user resolves the prompt. Never mark the step `done` on the same iteration the escalation fires; a premature `done` record would let the phase transition past an unresolved security decision.

## Error Handling

| Scenario | Action |
|----------|--------|
| Live footprint empty (engine stage 1 returns no files) | Mark `done` with `display_detail "Security audit: no footprint"` — nothing to audit |
| No affected domain declares a `security` profile | Run the audit with the action-general layer only (`extra_security_skills` empty) |
| Engine returns an error TOON | Mark `failed` with the engine's error in `display_detail`; finalize halts per the dispatcher's error handling |
| User decision required | Return `escalate_ask` without `mark-step-done` (see the no-mark invariant above) |

## Related

- [../../recipe-security-audit/standards/audit-engine.md](../../recipe-security-audit/standards/audit-engine.md) — the normative five-stage engine contract and the `extra_security_skills` stage-3 plug-in surface
- [../../persona-security-expert/SKILL.md](../../persona-security-expert/SKILL.md) — the action-general security identity loaded at stage 3
- [../../manage-execution-manifest/standards/decision-rules.md](../../manage-execution-manifest/standards/decision-rules.md) — the composition rules that gate this step into `phase_6.steps`
- [finalize-step-simplify.md](finalize-step-simplify.md) — the peer `mutates_source: true` HEAD-dependent finalize step this doc mirrors
