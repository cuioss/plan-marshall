# Finalize Steps — Dispatched vs Inline Split

This document is the single source of truth for which of the default + project finalize steps **dispatch** (run under `Task: execution-context-{level}`) and which run **inline** (pure scripts or trivial orchestration in the main context). The phase-6-finalize `SKILL.md` § "Dispatched workflows vs inline steps" points here; the classification is consumed by the Execute Step Pipeline step's dispatch branch.

Of the 17 default + project finalize steps, **6 dispatch** and **11 run inline**. Every dispatched step resolves under the phase-scoped registry — `manage-config effort resolve-target --phase phase-6-finalize [--role <subkey>]`.

## Step → resolved role (dispatched steps)

- `pre-submission-self-review` → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`)
- `create-pr` → `phase-6-finalize` (no `--role`)
- `lessons-capture` + `adr-propose` → `phase-6-finalize --role post-run-review`
- `plan-marshall:automatic-review` + `sonar-roundtrip` → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`) — **FIND-only**: each files its own finding type (`pr-comment` / `sonar-issue`) and marks done, taking no `producer` runtime input at all
- `architecture-refresh` is hybrid (Tier 0 inline scripts; Tier 1 fans out under `phase-6-finalize` per affected module — the only per-iteration parallel dispatch in the contract)
- `project:finalize-step-plugin-doctor` (meta-project only) → `phase-6-finalize --role verification-feedback` (`producer=plugin-doctor` runtime input)

Two opt-in dispatched steps exist outside the default set: **retrospective** → `phase-6-finalize --role post-run-review` (8 LLM aspects iterate inside one envelope); `/workflow-pr-doctor` (slash-command surface) → `phase-6-finalize --role verification-feedback` (`producer=pr-state` runtime input).

**Dispatcher-owned unified triage (not a manifest step)**: after BOTH `plan-marshall:automatic-review` and `sonar-roundtrip` have filed, the phase-6-finalize dispatcher's Step 3 item 7c fires ONE additional dispatch — `phase-6-finalize --role verification-feedback` with `producer=finalize-feedback` — over the union of their pending `pr-comment` ∪ `sonar-issue` findings. This is the ONLY place `producer=finalize-feedback` triage happens in finalize; it produces no `phase_steps["6-finalize"]` record of its own and is not counted in the 6/17 roster above. See [`../SKILL.md`](../SKILL.md) Step 3 item 7c and [`../../plan-marshall/workflow/verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) § "Producer modes".

## Inline steps

The 11 inline steps (`finalize-step-sync-baseline`, `push`, `ci-verify`, `branch-cleanup`, `pre-push-quality-gate`, `record-metrics`, `archive-plan`, `finalize-step-print-phase-breakdown`, `architecture-refresh` Tier 0, `project:finalize-step-deploy-target`, `project:finalize-step-sync-plugin-cache`) are pure scripts or trivial orchestration that earn no envelope.

`ci-verify` is a deterministic taxonomy-classification script (`scripts/ci_verify.py`): its green pass-through (`final_status == success` AND no failing checks) marks the step done with ZERO dispatch, and only genuinely-red CI files one taxonomy finding per failing check and returns a per-producer needs-triage signal that the dispatcher routes to `verification-feedback` (the sole LLM step, red-CI only). This green-early-return / no-dispatch bypass is documented BEFORE the red-CI triage dispatch it bypasses.

CI completion is no longer a sibling step in this roster — it is a dispatcher-resolved precondition (`requires: [ci-complete]`) checked inline before any consumer step runs; see the SKILL.md Execute Step Pipeline step § "Precondition resolution".

For the rationale see [`dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md) § 5 (find the LLM core, not the wrapping step).
