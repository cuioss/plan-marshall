# Dispatch Logging Standard

Authoritative specification of the standardized post-resolve work-log emission that every `plan-marshall:execution-context-{level}` dispatch site MUST produce. This emission is the audit-trail evidence that the [`plan-retrospective:execution-context-dispatch-audit`](../../plan-retrospective/standards/execution-context-dispatch-audit.md) rule-set consumes, and is the mechanical observable that lets log readers reconstruct — from `logs/work.log` alone — which effort tier executed each subagent call, which workflow body was loaded, and which plan the dispatch belongs to.

## Why this exists

The dispatch pipeline had a logging blind spot: callers pre-logged a generic `[STATUS]` line that named only the about-to-dispatch role-key BEFORE `effort resolve-target` returned the concrete `target`. The pre-log captured the intent (which role-key was about to dispatch) but not the outcome — which `level` actually fired, which workflow body got loaded, which `plan_id` is bound. The audit trail therefore could not verify dispatch-envelope discipline mechanically.

This standard fixes that by mandating one canonical line emitted AFTER the resolve returns, with all five attribution fields carrying concrete resolved values. The line is the audit-trail evidence of every dispatch and the single observable the retrospective audit relies on.

## Emission contract

### Prefix marker

The line uses the `[DISPATCH]` prefix marker, distinct from the generic `[STATUS]` prefix used by phase-progress lines. The distinct marker lets log readers and the retrospective audit grep deterministically for the dispatch evidence:

```
[DISPATCH] (caller) target=<value> level=<value> role=<value> workflow=<value> plan_id=<value>
```

The five literal field names (`target`, `level`, `role`, `workflow`, `plan_id`) MUST appear verbatim — they are the keys the retrospective audit parses.

### Field semantics

| Field | Value | Source |
|-------|-------|--------|
| `target` | The resolved variant agent name (`execution-context-{level}` or canonical `execution-context` for `inherit`) | `effort resolve-target` return value's `target` field |
| `level` | The effort level the target encodes (`low`, `medium`, `high`, `xhigh`, `xxhigh`, `max`, `inherit`) | `effort resolve-target` return value's `level` field |
| `role` | The role-key the caller resolved against (e.g., `phase-2-refine`, `verification-feedback`, `default`) | The `--role` argument the caller passed to `effort resolve-target` |
| `workflow` | The bundle-prefixed notation of the workflow doc the subagent loads (e.g., `plan-marshall:phase-2-refine/SKILL.md`) | The caller's chosen workflow doc — the same value placed in the prompt body's `workflow:` field |
| `plan_id` | The plan identifier the dispatch is bound to (or `none` for standalone dispatches outside any plan) | The caller's plan context |

All values are concrete strings resolved at the time of emission — no `{placeholder}` tokens remain.

### Placement contract

The emission MUST fire:

1. **AFTER** `python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort resolve-target` returns and the caller has captured `target` and `level` from the return TOON, AND
2. **BEFORE** the `Task: plan-marshall:{target}` dispatch block.

This placement is load-bearing. Pre-resolve emission cannot carry the resolved `target`/`level` and is therefore incomplete; post-dispatch emission risks being skipped if the dispatch errors or the agent exits early before the caller reaches the line.

### Canonical invocation

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:{caller-skill}) target={target} level={level} role={role} workflow={workflow} plan_id={plan_id}"
```

The `(plan-marshall:{caller-skill})` caller prefix follows the standard two-segment convention from [`../../manage-logging/standards/log-format.md`](../../manage-logging/standards/log-format.md) — substitute the calling skill's notation (e.g., `plan-marshall:plan-marshall`, `plan-marshall:phase-5-execute`, `plan-marshall:workflow-pr-doctor`).

For standalone dispatches outside any plan, pass `--plan-id none` and use `plan_id=none` in the message; the rest of the contract is unchanged.

## Positive example

A phase-2-refine dispatch from `plan-marshall/workflow/planning.md`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-2-refine
```

Extract the `target` and `level` fields from the TOON output (e.g., `target=execution-context-high`, `level=high`). Substitute those values into the post-resolve log line below as `{target}` and `{level}`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:plan-marshall) target=execution-context-high level=high role=phase-2-refine workflow=plan-marshall:phase-2-refine/SKILL.md plan_id={plan_id}"
```

```
Task: plan-marshall:{target}
  prompt: |
    name: phase-2-refine
    plan_id: {plan_id}
    skills[3]:
    - plan-marshall:manage-architecture
    - plan-marshall:manage-references
    - plan-marshall:manage-plan-documents
    workflow: plan-marshall:phase-2-refine/SKILL.md
    WORKTREE: {worktree_path}
```

The resulting work-log line is fully attributed, machine-parseable, and audit-ready. The retrospective audit pairs it with the matching `effort resolve-target` decision-log entry and the subsequent agent-completion signal to verify the dispatch rode the canonical envelope.

## Anti-pattern (forbidden)

A pre-resolve placeholder line, which carries only the role-key intent and no resolved attribution. The forbidden shape combines a generic `[STATUS]` work-log line emitted BEFORE the resolver runs (carrying only the role key — for example, `[STATUS] (plan-marshall:plan-marshall) About to dispatch execution-context for role <role-key>`) with a subsequent `target=$(... effort resolve-target --role phase-2-refine)` shell-substitution that captures the resolver result into a Bash variable, and finally a `Task: plan-marshall:{target}` dispatch — three separate forbidden patterns layered together. The `target=$(…)` shape is itself a violation of the no-`$()` Bash hard rule documented in `dev-general-practices/standards/tool-usage-patterns.md`; the pre-resolve `[STATUS]` line is a violation of this dispatch-logging contract; together they hide the actual dispatched variant from the audit trail.

Failure mode the post-resolve shape prevents: the audit trail can identify only the role-key the caller intended to dispatch under. The actual `target`, `level`, and `workflow` are absent from the log — so the retrospective audit cannot tell whether the dispatch rode `execution-context-high`, `execution-context-medium`, or (worst case) bypassed the dispatcher entirely via `Task: general-purpose`. The shape also uses the generic `[STATUS]` prefix, which collides with phase-progress lines and breaks deterministic grep.

The single canonical `[DISPATCH]` line specified above is the sole permitted dispatch-emission shape. Callers that today emit no dispatch log MUST add one; callers that emit the pre-resolve placeholder MUST replace it with the post-resolve emission.

## Cross-references

- [`../../dev-general-practices/standards/general-development-rules.md`](../../dev-general-practices/standards/general-development-rules.md) **lines 196 and 241** — the authoritative rule prohibiting unconstrained generic subagents inside plan-marshall phase work, and the Quick Reference decision-matrix row that directs callers to `plan-marshall:execution-context-{level}` instead. The `[DISPATCH]` emission is the mechanical observable that lets the retrospective audit verify compliance with this rule.
- [`../../plan-retrospective/standards/execution-context-dispatch-audit.md`](../../plan-retrospective/standards/execution-context-dispatch-audit.md) — the rule-set that consumes `[DISPATCH]` work-log lines as evidence and emits per-spawn findings (`shape_violation`, `envelope_violation`, `generic_subagent_violation`).
- [`dispatch-walkthrough.md`](dispatch-walkthrough.md) — the canonical worked-example trace of a dispatch round-trip; includes the `[DISPATCH]` emission between resolve and dispatch.
- [`agents.md`](agents.md) — the dispatch contract (prompt-body fields, role-key resolution, mandatory rules) that the `workflow` field in this emission references.
- [`../../manage-logging/standards/log-format.md`](../../manage-logging/standards/log-format.md) — the canonical work-log line format (caller-prefix convention, level vocabulary, prefix markers).
