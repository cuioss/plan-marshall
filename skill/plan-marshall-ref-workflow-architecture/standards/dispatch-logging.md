# Dispatch Logging Standard

Authoritative specification of the standardized post-resolve work-log emission that every `plan-marshall:execution-context-{level}` dispatch site MUST produce. This emission is the audit-trail evidence that the [`plan-retrospective:execution-context-dispatch-audit`](../../plan-retrospective/standards/execution-context-dispatch-audit.md) rule-set consumes, and is the mechanical observable that lets log readers reconstruct — from `logs/work.log` alone — which effort tier executed each subagent call, which workflow body was loaded, and which plan the dispatch belongs to.

## Why this exists

The dispatch pipeline had a logging blind spot: callers pre-logged a generic `[STATUS]` line that named only the about-to-dispatch role-key BEFORE `effort resolve-target` returned the concrete `target`. The pre-log captured the intent (which role-key was about to dispatch) but not the outcome — which `level` actually fired, which workflow body got loaded, which `plan_id` is bound. The audit trail therefore could not verify dispatch-envelope discipline mechanically.

The first fix mandated one canonical line, but as a **hand-written** `manage-logging work` step the caller placed once per role in the workflow doc, co-located with the initial resolve. That left a second blind spot: a step that re-fired N times (a head-advance re-stale, a verification-feedback loop, an envelope re-dispatch) logged **once** — the re-fires re-pointed at the prior `Task:` block without re-running the hand-written logging line, so they vanished from the trail. The record was per-role, not per-firing.

This standard closes that by moving the emission **into the resolution seam itself**. `effort resolve-target` — the one script call every execution-context dispatch makes to compute its target — emits the record as a side-effect of the resolve, per firing, when the caller passes the dispatch context (`--workflow` and `--plan-id`). Every firing resolves, so every firing emits; a re-fire that re-resolves re-emits, by construction, with no separate logging step to forget. The line is the audit-trail evidence of every dispatch and the single observable the retrospective audit relies on.

## Emission contract

### Prefix marker

The line uses the `[DISPATCH]` prefix marker, distinct from the generic `[STATUS]` prefix used by phase-progress lines. The distinct marker lets log readers and the retrospective audit grep deterministically for the dispatch evidence:

```text
[DISPATCH] (caller) target=<value> level=<value> role=<value> workflow=<value> plan_id=<value>
```

The five literal field names (`target`, `level`, `role`, `workflow`, `plan_id`) MUST appear verbatim — they are the keys the retrospective audit parses.

### Field semantics

| Field | Value | Source |
|-------|-------|--------|
| `target` | The resolved variant agent name (`execution-context-{level}` or canonical `execution-context` for `inherit`) | `effort resolve-target` return value's `target` field |
| `level` | The effort level the target encodes (`level-1`, `level-2`, `level-3`, `level-4`, `level-5`, `level-6`, `level-7`, `inherit`) | `effort resolve-target` return value's `level` field |
| `role` | The role-key the caller resolved against (e.g., `phase-2-refine`, `verification-feedback`, `default`) | The `--role` argument the caller passed to `effort resolve-target` |
| `workflow` | The bundle-prefixed notation of the workflow doc the subagent loads (e.g., `plan-marshall:phase-2-refine/SKILL.md`) | The caller's chosen workflow doc — the same value placed in the prompt body's `workflow:` field |
| `plan_id` | The plan identifier the dispatch is bound to (or `none` for standalone dispatches outside any plan) | The caller's plan context |

All values are concrete strings resolved at the time of emission — no `{placeholder}` tokens remain.

### Placement contract

The emission is a side-effect of the resolve, not a separate step the caller places. `effort resolve-target` emits the line **itself**, immediately after it computes `target`/`level` and only on a successful resolve, when the caller supplies the dispatch context (`--workflow`, and `--plan-id`/`--caller`). This placement is load-bearing and now structural:

1. It fires **AFTER** the resolve — the resolver already holds the concrete `target`/`level`, so the line carries them with no `{placeholder}` gap a pre-resolve line would leave.
2. It fires from the resolver every time the resolver runs — so a re-fire that re-resolves re-emits, and there is no separate logging step for a re-dispatch to skip.

The caller's only obligation is to pass the dispatch context to the resolve it already performs; it MUST NOT also hand-write a separate `manage-logging work "[DISPATCH]"` line (that reintroduces the per-role blind spot and double-emits). A resolve that carries no `--workflow` is a bare query and emits nothing.

### The second surface — the resolve record

The same seam call also writes the paired **decision-log** record — a `(plan-marshall:manage-config) effort resolve-target …` line naming the resolved role and target. Both surfaces (this decision-log record and the `[DISPATCH]` work-log line) are emitted together, from the one resolve. Because they share that emitter their agreement is a consistency check on the seam, never a completeness check on the set of dispatches — see [`../../plan-retrospective/standards/execution-context-dispatch-audit.md`](../../plan-retrospective/standards/execution-context-dispatch-audit.md) § Inputs "Corroboration limit".

### Canonical invocation

The caller resolves the target with the dispatch context, and the resolver emits both records:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role {role} \
  --workflow {workflow} --plan-id {plan_id} --caller plan-marshall:{caller-skill}
```

The resolver returns the `target`/`level` TOON (which the caller uses in the `Task:` block) AND, as a side-effect of the resolve, writes the `[DISPATCH]` work-log line and the paired decision-log resolution record. There is no separate `manage-logging` step.

The `--caller plan-marshall:{caller-skill}` value becomes the `[DISPATCH]` line's caller prefix and follows the standard two-segment convention from [`../../manage-logging/standards/log-format.md`](../../manage-logging/standards/log-format.md) — substitute the calling skill's notation (e.g., `plan-marshall:plan-marshall`, `plan-marshall:phase-5-execute`, `plan-marshall:workflow-pr-doctor`). It defaults to `plan-marshall:manage-config` (the seam) when omitted.

For standalone dispatches outside any plan, pass `--plan-id none`; the record routes to the dated global work/decision log and carries `plan_id=none`, the rest of the contract unchanged.

## Positive example

A phase-2-refine dispatch from `plan-marshall/workflow/planning.md`. One resolve call carries the dispatch context, so the seam emits both records; the caller then dispatches:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --role phase-2-refine \
  --workflow plan-marshall:phase-2-refine/SKILL.md --plan-id {plan_id} \
  --caller plan-marshall:plan-marshall
```

Extract the `target` and `level` fields from the TOON output (e.g., `target=execution-context-level-3`, `level=level-3`) and use `{target}` in the dispatch block. The same call has already written the `[DISPATCH]` work-log line (`[DISPATCH] (plan-marshall:plan-marshall) target=execution-context-level-3 level=level-3 role=phase-2-refine workflow=plan-marshall:phase-2-refine/SKILL.md plan_id={plan_id}`) and its paired decision-log resolution record — no further logging step is needed.

```text
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

The resulting work-log line is fully attributed, machine-parseable, and audit-ready — and, because it rode the resolve, it is written again on every re-fire that re-resolves rather than once per role. The retrospective audit pairs it with the matching `effort resolve-target` decision-log entry (written by the same seam call) to trace the dispatch from intent to observable.

## Anti-pattern (forbidden)

A pre-resolve placeholder line, which carries only the role-key intent and no resolved attribution. The forbidden shape combines a generic `[STATUS]` work-log line emitted BEFORE the resolver runs (carrying only the role key — for example, `[STATUS] (plan-marshall:plan-marshall) About to dispatch execution-context for role <role-key>`) with a subsequent `target=$(... effort resolve-target --role phase-2-refine)` shell-substitution that captures the resolver result into a Bash variable, and finally a `Task: plan-marshall:{target}` dispatch — three separate forbidden patterns layered together. The `target=$(…)` shape is itself a violation of the no-`$()` Bash hard rule documented in `persona-plan-marshall-agent/standards/tool-usage-patterns.md`; the pre-resolve `[STATUS]` line is a violation of this dispatch-logging contract; together they hide the actual dispatched variant from the audit trail.

Failure mode the post-resolve shape prevents: the audit trail can identify only the role-key the caller intended to dispatch under. The actual `target`, `level`, and `workflow` are absent from the log — so the retrospective audit cannot tell whether the dispatch rode `execution-context-level-3`, `execution-context-level-2`, or (worst case) bypassed the dispatcher entirely via `Task: general-purpose`. The shape also uses the generic `[STATUS]` prefix, which collides with phase-progress lines and breaks deterministic grep.

Two further forbidden shapes, specific to the seam:

- **A separately hand-written `manage-logging work "[DISPATCH]"` step.** Now that the resolver emits the line, a hand-written one double-emits, and — placed once per role in the doc — reintroduces the per-role blind spot the seam exists to close. Pass the dispatch context to the resolve; do not also hand-write the line.
- **A re-fire that reuses the envelope without re-resolving.** Re-dispatching by re-issuing a prior `Task:` block with a cached `target`, skipping the resolve, emits nothing — the re-fire vanishes from the trail exactly as before. Every firing MUST perform its own `effort resolve-target … --workflow …` so the seam emits per firing.

The seam emission specified above is the sole permitted dispatch-emission shape. Callers that today emit no dispatch log MUST pass the dispatch context to their resolve; callers that hand-write the `[DISPATCH]` line (or the pre-resolve placeholder) MUST drop it and let the seam emit.

## Cross-references

- [`../../persona-plan-marshall-agent/standards/agent-behavior-rules.md`](../../persona-plan-marshall-agent/standards/agent-behavior-rules.md) § "Unconstrained generic subagents" and "Quick Reference decision-matrix" — the authoritative rule prohibiting unconstrained generic subagents inside plan-marshall phase work, and the Quick Reference decision-matrix row that directs callers to `plan-marshall:execution-context-{level}` instead. The `[DISPATCH]` emission is the mechanical observable that lets the retrospective audit verify compliance with this rule.
- [`../../plan-retrospective/standards/execution-context-dispatch-audit.md`](../../plan-retrospective/standards/execution-context-dispatch-audit.md) — the rule-set that consumes `[DISPATCH]` work-log lines as evidence and emits per-spawn findings (`shape_violation`, `envelope_violation`, `generic_subagent_violation`).
- [`dispatch-walkthrough.md`](dispatch-walkthrough.md) — the canonical worked-example trace of a dispatch round-trip; shows the `[DISPATCH]` emission as a side-effect of the resolve seam (not a separate step).
- [`agents.md`](agents.md) — the dispatch contract (prompt-body fields, role-key resolution, mandatory rules) that the `workflow` field in this emission references.
- [`../../manage-logging/standards/log-format.md`](../../manage-logging/standards/log-format.md) — the canonical work-log line format (caller-prefix convention, level vocabulary, prefix markers).
