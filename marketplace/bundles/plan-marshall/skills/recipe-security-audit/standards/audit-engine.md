# Shared Security-Audit Engine

The single, reusable security-audit procedure for the plan-marshall audit recipe family. Authored once here and consumed by two callers: `recipe-security-audit/SKILL.md` (on-demand entry point, this plan) and — later — the `default:finalize-step-security-audit` finalize step (automatic, pre-ship gate, workstream 05). Both callers run the **identical** five stages below; neither restates them. A caller that needs to diverge supplies an additive input to a stage, it does not fork the procedure.

The engine is a **cognitive workflow**, not a deterministic script: each stage names the structured tool calls that supply its inputs, but the audit itself (stage 4) is an LLM security review, consistent with the recipe-skill design model (recipe skills are `mode: workflow` cognitive procedures).

## Scope boundary — best-effort context, NOT the `security` profile

This engine gathers **best-effort, action-general** security context only. It explicitly does **NOT** use the `security` profile nor any `skills_by_profile.security` resolution — those do not exist yet and are workstream 05's deliverables. The engine's stage-3 context set is fixed at the three action-general skills named below.

Workstream 05 plugs into this engine **additively** at stage 3: it supplies the per-domain `skills_by_profile.security` skills (resolved for the affected domains from stage 2) as an **extra context input** layered on top of the action-general set. That addition touches stage 3 only — stages 1, 2, 4, and 5 are unchanged, and the engine procedure is never reshaped. This is the named plug-in point that lets 05 reuse the engine without forking it.

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `plan_id` | Yes | Plan identifier — every run is plan-bound (see the engine principle below). |
| `scope` | No | Optional path/file restriction. When supplied, the stage-1 footprint is bounded to these paths. When omitted, the footprint is the full current-branch-vs-base diff. |
| `base_branch` | No | Optional explicit base ref for the stage-1 diff. When omitted, defaults to `references.base_branch` (falling back to `main`) — i.e. the current-branch-vs-base diff. |
| `extra_security_skills` | No | **Workstream 05's additive plug-in.** A per-domain `skills_by_profile.security` skill set, resolved by 05 for the stage-2 affected domains, layered onto the stage-3 action-general context set. Absent on the on-demand recipe path. |

Every run — on-demand recipe or finalize step — is plan-bound and operates inside its own plan-directory, so `manage-references`, `manage-findings`, and the `ext-triage-*` extensions all work uniformly with no plan-less special case.

## The five stages

### Stage 1 — Compute the live footprint

Derive the live footprint from the worktree git state, bounded to the optional `scope` and defaulting to the current-branch-vs-base diff:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references compute-footprint \
  --plan-id {plan_id} --worktree-path {worktree_path} [--base-ref {base_branch}]
```

- Pass `--base-ref {base_branch}` only when an explicit `base_branch` input was supplied; otherwise omit it and the script defaults to `references.base_branch` (falling back to `main`).
- When a `scope` (path/file restriction) was supplied, intersect the returned footprint paths with `scope` and carry only the intersection into the later stages.

The footprint is the audit radius. An empty footprint means there is nothing to audit — the engine returns with zero findings.

### Stage 2 — Detect affected domains

For each footprint path, resolve its owning module:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture which-module --path {path}
```

Collect the distinct module values into the affected-domain set. This set drives stage 3's context relevance (and is the resolution key for workstream 05's additive per-domain `skills_by_profile.security` input).

### Stage 3 — Gather best-effort security context

Load the action-general security context — exactly these three skills, no more:

- `plan-marshall:persona-security-expert` — the action-general security identity: OWASP Top Ten, STRIDE, trust-boundary and secure-coding principles.
- `plan-marshall:untrusted-ingestion` — the untrusted-external-content ingestion contract (reader/orchestrator/writer isolation, the validator containment boundary).
- `plan-marshall:workflow-permission-web` — web-domain permission analysis and consolidation.

**This is the complete stage-3 set on the on-demand path.** It is NOT the `security` profile and NOT `skills_by_profile.security` — those are workstream 05's deliverables. When the caller is workstream 05's finalize step, it ADDS its resolved per-domain `skills_by_profile.security` skills (the `extra_security_skills` input) on top of these three; that addition is the only difference between the two callers, and it changes stage 3 alone.

### Stage 4 — Run the cognitive audit

Run the LLM security review across the stage-1 footprint, applying the stage-3 context. This is the cognitive core: read the in-footprint files, reason about each against the loaded security knowledge (OWASP Top Ten, STRIDE, trust boundaries, injection sinks, untrusted-input handling, secrets, supply chain), and identify concrete security defects and risky patterns. The review covers the footprint completely — every file in radius is examined, not sampled.

### Stage 5 — Emit findings and dispatch to triage

Emit each identified issue as a finding via `manage-findings add`. Security findings map onto the **closed `FINDING_TYPES` taxonomy**: a concrete defect is a `bug`; a risky-but-not-yet-exploitable structural pattern is an `anti-pattern`. **There is no `security-issue` type** — the taxonomy is closed and a new discovery surface maps onto an existing type, it never adds one.

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings add \
  --plan-id {plan_id} --type {bug|anti-pattern} --severity {error|warning|info} \
  --title "{short title}" --detail "{description}" \
  --file-path {file} --line {line} --module {module}
```

One `add` call per finding. Then dispatch each finding to its domain `ext-triage-*` extension (keyed on the finding's module/domain from stage 2) for the FIX / SUPPRESS / ACCEPT decision — the same resolution model every findings producer uses. The engine adds a producer; it does not add a new resolution model.

## Why findings, not a prose report

Emitting into `manage-findings` (rather than printing a report and stopping) is what buys triage, suppression, loop-back, and re-review for free — the structural difference from external audit tools. This is the universal-sink principle: anything that discovers a problem emits into the findings pipeline.

## Related

- `plan-marshall:recipe-security-audit` `SKILL.md` — the on-demand caller that loads this engine and runs the five stages.
- `plan-marshall:persona-security-expert` — the action-general security identity loaded at stage 3.
- `plan-marshall:untrusted-ingestion` — the untrusted-content ingestion contract loaded at stage 3.
- `plan-marshall:workflow-permission-web` — the web-permission analysis surface loaded at stage 3.
- `plan-marshall:manage-references` `compute-footprint` — the stage-1 footprint resolver.
- `plan-marshall:manage-architecture` `which-module` — the stage-2 domain detector.
- `plan-marshall:manage-findings` `add` — the stage-5 findings sink (closed `FINDING_TYPES` taxonomy; `bug` / `anti-pattern`, no `security-issue` type).
- `plan-marshall:extension-api` `standards/ext-point-triage.md` — the domain `ext-triage-*` resolution model the stage-5 findings flow into.
