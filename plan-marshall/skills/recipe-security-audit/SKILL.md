---
name: recipe-security-audit
description: On-demand security-audit recipe that runs the shared five-stage audit engine over the current footprint and emits findings into the triage pipeline
user-invocable: false
mode: workflow
implements: plan-marshall:extension-api/standards/ext-point-recipe
lane:
  profile: full
metadata:
  verification_profile: security
---

# Recipe: Security Audit

On-demand entry point for the plan-marshall security-audit capability. This recipe runs the shared five-stage security-audit procedure over the current footprint and emits each discovered issue as a finding into the triage pipeline — the structural difference from external audit tools, which print a report and stop.

The procedure itself is NOT authored here. It lives once in [`standards/audit-engine.md`](standards/audit-engine.md) and is consumed by two callers: this recipe (the on-demand entry point) and — later — the `default:finalize-step-security-audit` finalize step (the automatic, pre-ship gate, workstream 05). Both callers run the **identical** five stages; neither restates them. This skill is the thin on-demand caller — it gathers the recipe inputs, loads the engine standard, walks the five stages over the footprint, and returns the run summary.

The engine is a **cognitive workflow**, not a deterministic script: each stage names the structured tool calls that supply its inputs, but the audit itself (stage 4) is an LLM security review, consistent with the recipe-skill design model (recipe skills are `mode: workflow` cognitive procedures).

## Foundational Practices

```text
Skill: plan-marshall:persona-plan-marshall-agent
```

## Enforcement

**Execution mode**: Load the shared audit-engine standard, then walk its five stages in order over the footprint. Each stage has a single explicit job — no improvisation, no extra discovery passes beyond what a stage names.

**Prohibited actions:**
- Never re-author or inline-copy the five-stage procedure here. The single source of truth is [`standards/audit-engine.md`](standards/audit-engine.md); this skill loads it and runs it. Restating the stage bodies forks the engine and is the prohibited anti-pattern.
- Never use the `security` profile or any `skills_by_profile.security` resolution on the on-demand path. Those do not exist yet — they are workstream 05's deliverables. The stage-3 context set is fixed at the three action-general skills the engine names, full stop.
- Never emit a `security-issue` finding type. The `FINDING_TYPES` taxonomy is closed: a concrete defect is a `bug`; a risky-but-not-yet-exploitable structural pattern is an `anti-pattern`. A new discovery surface maps onto an existing type — it never adds one.
- Never print a prose security report and stop instead of emitting findings. Emitting into `manage-findings` is what buys triage, suppression, loop-back, and re-review for free (the universal-sink principle).

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- Every run is plan-bound and operates inside its own plan directory — there is no plan-less special case.
- The cognitive audit (stage 4) covers the footprint **completely** — every in-radius file is examined, not sampled.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier — every run is plan-bound. |
| `scope` | string | No | Optional path/file restriction. When supplied, the stage-1 footprint is bounded to these paths. When omitted, the footprint is the full current-branch-vs-base diff. |
| `base_branch` | string | No | Optional explicit base ref for the stage-1 diff. When omitted, defaults to `references.base_branch` (falling back to `main`). |

These are the on-demand caller's inputs. The engine's fourth input, `extra_security_skills`, is **workstream 05's additive plug-in** and is absent on this path — see the engine standard's input table and its stage-3 plug-in note.

---

## Step 1: Resolve the worktree path

Resolve the active worktree path from `plan_id` — stage 1 of the engine needs it for the footprint computation:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status get-worktree-path \
  --plan-id {plan_id}
```

Capture the returned `worktree_path`. When `metadata.use_worktree == false` the returned path is empty — the footprint is computed against the main checkout directly.

---

## Step 2: Load the shared audit-engine standard

Load the single source of truth for the procedure this recipe runs:

```text
Read: marketplace/bundles/plan-marshall/skills/recipe-security-audit/standards/audit-engine.md
```

The standard defines the five stages, their inputs, the stage-3 action-general context set, and the closed `FINDING_TYPES` mapping. Do NOT restate the stages below — the steps that follow only bind the recipe inputs into the engine and walk it.

---

## Step 3: Run the five stages over the footprint

Walk the engine's five stages in order, passing this recipe's inputs (`plan_id`, the resolved `worktree_path`, and the optional `scope` / `base_branch`):

1. **Stage 1 — Compute the live footprint** via `manage-references compute-footprint` (bounded to `scope`, defaulting to the current-branch-vs-base diff). An empty footprint means there is nothing to audit — return with zero findings.
2. **Stage 2 — Detect affected domains** via `manage-architecture which-module` per footprint path; collect the distinct module set.
3. **Stage 3 — Gather best-effort security context** — load exactly the three action-general skills the engine names (`plan-marshall:persona-security-expert`, `plan-marshall:untrusted-ingestion`, `plan-marshall:workflow-permission-web`). This is the complete on-demand context set — NOT the `security` profile.
4. **Stage 4 — Run the cognitive audit** — the LLM security review across the full footprint, applying the stage-3 context (OWASP Top Ten, STRIDE, trust boundaries, injection sinks, untrusted-input handling, secrets, supply chain).
5. **Stage 5 — Emit findings, verify, and dispatch to triage** — one `manage-findings add` per issue (`type` = `bug` for a concrete defect, `anti-pattern` for a risky structural pattern). This recipe declares `verification_profile: security` (see the frontmatter `metadata:` block above), so each emitted finding passes through the [verify stage](../extension-api/standards/ext-point-verify.md) adversarial-refute pass FIRST: refuted false positives close `rejected` and never reach triage, while confirmed (surviving) findings dispatch to their domain `ext-triage-*` extension keyed on the stage-2 module.

The stage bodies — exact commands, flag rules, the verify-then-triage routing, and the no-`security-issue` taxonomy constraint — are the engine standard's, not this skill's. Follow them as written there.

---

## Step 4: Return the run summary

After the five stages complete, return the run summary as TOON:

```toon
status: success
plan_id: {echo}
audit_summary:
  footprint_paths: N
  affected_modules: [module, ...]
  findings_emitted: N
next_action: findings_dispatched_to_triage
```

When the stage-1 footprint is empty, return `findings_emitted: 0` with `next_action: nothing_to_audit`. The emitted findings flow into the same triage / suppression / loop-back / re-review pipeline every findings producer uses — this recipe adds a producer, not a new resolution model.

---

## Related

- `plan-marshall:recipe-security-audit` `standards/audit-engine.md` — the shared five-stage procedure this recipe loads and runs (single source of truth).
- `plan-marshall:persona-security-expert` — the action-general security identity loaded at stage 3.
- `plan-marshall:untrusted-ingestion` — the untrusted-content ingestion contract loaded at stage 3.
- `plan-marshall:workflow-permission-web` — the web-permission analysis surface loaded at stage 3.
- `plan-marshall:manage-references` `compute-footprint` — the stage-1 footprint resolver.
- `plan-marshall:manage-architecture` `which-module` — the stage-2 domain detector.
- `plan-marshall:manage-findings` `add` — the stage-5 findings sink (closed `FINDING_TYPES` taxonomy; `bug` / `anti-pattern`, no `security-issue` type).
- `plan-marshall:extension-api` `standards/ext-point-triage.md` — the domain `ext-triage-*` resolution model the stage-5 findings flow into.
- `plan-marshall:extension-api` `standards/ext-point-recipe.md` — the recipe extension point this skill implements.
