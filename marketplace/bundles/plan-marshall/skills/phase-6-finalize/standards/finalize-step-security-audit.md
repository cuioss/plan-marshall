---
lane:
  class: adversarial
  tier: full
  cost_size: L
name: default:finalize-step-security-audit
description: Proactive phase-6 security-audit pass — runs the shared five-stage security-audit engine over the plan's live footprint, layering each affected domain's skills_by_profile.security skills onto the action-general context; declared mutates_source so the dispatcher's commit instrumentation ships any hardening edits before the push barrier
persona: persona-security-expert
order: 9
mutates_source: true
default_on: true
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step: security-audit

Proactive security-audit pass for the `default:finalize-step-security-audit` finalize step. Runs the shared five-stage security-audit engine over the plan's live footprint before the `push` barrier, applies any hardening edits directly to the worktree, and lets the dispatcher's commit instrumentation commit them. This is the proactive, ship-time complement to the on-demand `recipe-security-audit` command: the recipe runs a security review when a user asks for one; this step runs automatically.

Activation is **change-type-independent**: any plan carrying a change surface at all — a non-empty declared `affected_files_count` **or** a non-empty live footprint — gets the audit, and only a plan with neither is dropped. The operator's escape hatch is the step's per-element `lane` override, which forces the step in or out irrespective of that gate. The normative rules live in **Activation and skip-reason** below; this summary states no gate of its own.

The step reuses the engine **additively at stage 3 only** — it supplies each affected domain's `skills_by_profile.security` skills (the `extra_security_skills` input) on top of the action-general context set. Stages 1, 2, 4, and 5 are unchanged; this step never re-authors an engine stage. See [`../../recipe-security-audit/standards/audit-engine.md`](../../recipe-security-audit/standards/audit-engine.md) for the normative engine contract and the `extra_security_skills` plug-in surface.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `finalize-step-security-audit` in `manifest.phase_6.steps` (bare name — the manifest holds un-prefixed step ids; the dispatcher prepends `default:` when looking up the dispatch-table row). The step is gated into the manifest at composition time by the two `manage-execution-manifest` decision surfaces described in **Activation and skip-reason** below, so this executor is never dispatched for the plans those surfaces exclude.

## Activation and skip-reason

Two independent composition-time surfaces decide whether `finalize-step-security-audit` lands in `manifest.phase_6.steps` (both owned by `manage-execution-manifest` — see [`../../manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md)):

1. **The `security_class_inactive` pre-filter** — drops the step only when `affected_files_count == 0` **AND** the plan's live footprint is resolvable and genuinely empty. An UNRESOLVABLE footprint (the worktree not yet materialised) is no evidence about the change surface rather than evidence of an empty one, so it keeps the step — the same fail-toward-inclusion discipline the absent `change_type` leg follows. It is deliberately a *fail-toward-inclusion* gate: there is no `change_type` leg, because `change_type` is an outline-time semantic label the composer's caller forwards from the **first deliverable**, so a plan opening with a read-only discovery deliverable reports `verification` however much production code its later deliverables mutate. Only a plan with no change surface at all — nothing declared and nothing in the worktree — has nothing to audit.

   The pre-filter operates on a **security class**, not a step id: a finalize step belongs to it by declaring the frontmatter scalar `persona: persona-security-expert` (which this step does — see its frontmatter above). A future second security-class finalize step inherits this activation treatment by declaring the same persona, with no change to the composer.
2. **The `steps.default:finalize-step-security-audit.lane` override** (`off` | `minimal` | `auto`/absent) — declared in EITHER of the two channels the composer merges: the project-wide `plan.phase-6-finalize.steps` map in marshal.json (read via `manage-config plan phase-6-finalize step get --step-id default:finalize-step-security-audit`, reading `params.lane`) or the plan-scoped `status.metadata.finalize_step_overrides` map written by `manage-config finalize-steps set-lane --plan-id …`. The composer resolves this gate from the merged plan-local-over-marshal source, so a per-plan declaration governs it exactly as a project-wide one does. It is the operator override applied by the finalize-selection ceremony transform, which maps the per-element lane override onto the force-in / force-out decision (`off→never`, `minimal→always`, `auto`/absent→auto). `auto`/absent defers to the `security_class_inactive` pre-filter; `minimal` forces the step in even when the pre-filter would have dropped it; `off` removes it unconditionally. The per-element `lane` override contract (values, resolution) is owned by [`../../manage-config/standards/data-model.md`](../../manage-config/standards/data-model.md) § phase-6-finalize and [`../../extension-api/standards/ext-point-lane-element.md`](../../extension-api/standards/ext-point-lane-element.md); this step is the consumer.

**Visible skip-reason**: whenever the step is skipped, the composer emits a `[STATUS]` decision-log line to the plan's `logs/decision.log` naming which surface fired. For the `security_class_inactive` pre-filter it additionally reports the drop in the `compose` result as a `security_class_omitted` `{step, reason}` record, which `phase-4-plan` Step 7b surfaces in its phase return — the operator-facing channel. This step's reporting is the **reference implementation** of the composer's subtraction-visibility convention: every other narrowing site — the pre-filters, each narrowing matrix row, and the lane-resolution pass — reuses this same `{step, reason}` record plus one `[STATUS]` line per dropped step, rather than inventing a second shape. The convention is normative in [`../../manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md) § "Every subtraction is reported". `decision.log` alone is not sufficient: it has no live reader, so a drop recorded only there is observable in a retrospective but invisible at the moment it happens. A `record-step` row with `outcome: skipped` covers the different case where the step IS in `manifest.phase_6.steps` and the dispatcher skips it at execution time; a step the pre-filter removed is never iterated by the dispatcher, so it produces no such row.

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
python3 .plan/execute-script.py plan-marshall:extension-api:extension_api resolve-skills \
  --profile security --plan-id {plan_id}
```

Capture the resolved per-domain `security`-profile skill set as `{extra_security_skills}`. A domain that declares no `security` profile contributes nothing (the resolver skips absent keys).

### Step 2: Load the security persona and invoke the shared engine

Load the action-general security identity in-context:

```text
Skill: plan-marshall:persona-security-expert
```

Invoke the shared five-stage engine documented at [`../../recipe-security-audit/standards/audit-engine.md`](../../recipe-security-audit/standards/audit-engine.md), supplying `extra_security_skills = {extra_security_skills}` at stage 3 ONLY (stages 1/2/4/5 run unchanged). The engine reads the in-footprint files, reasons about each against the loaded security knowledge plus the per-domain security skills, applies hardening edits directly to the worktree, and FILES its findings to the ledger **find-only**.

**Find-only; defer triage.** This step is a generator on the FIND side of the consolidated find → ingest → one-triage → one-respond pipeline: it files each security finding to the ledger (with the audited free-text quarantined under `raw_input` where applicable) and STOPS — it does NOT itself decide FIX / SUPPRESS / ACCEPT dispositions on those findings. Disposition is owned by the single consolidated triage pass later in finalize, which reads the promoted top-level fields and dispositions each finding once. The engine's `verification_profile` validity pre-stage (the adversarial-refute pass that closes refuted findings as `rejected` before triage) is unchanged — find-only concerns the disposition step, not the validity step.

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
