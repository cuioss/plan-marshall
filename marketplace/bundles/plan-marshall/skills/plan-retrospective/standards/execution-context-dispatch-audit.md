# Aspect: Execution-context Dispatch Audit

Verify that every execution-context spawn observed in a completed plan's `logs/work.log` rode the canonical `plan-marshall:execution-context-{level}` envelope — never `Task: general-purpose`, never an inline ad-hoc subagent dispatched outside the dispatcher. The audit consumes the standardized `[DISPATCH]` work-log lines specified in [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) as its primary evidence and pairs them with the matching `effort resolve-target` decision-log entries so every spawn is traceable from intent (role-key) through resolution (target/level) to invocation.

**Conditional**: always runs; emits zero findings when the plan's dispatch trail is clean.

## Purpose

The plan-marshall workflow forbids unconstrained generic subagents inside phase work because subagent enforcement rules propagate through the agent definition rather than through the caller's prompt. A `Task: general-purpose` spawn loses the plan-marshall hard rules — `.plan/`-via-scripts-only, one-command-per-Bash, no-direct-`gh`/`glab`, structured-queries-first, build-via-architecture-resolve — that the canonical `execution-context-{level}` envelope carries by construction.

This rule has two authoritative anchors in [`../../dev-general-practices/standards/general-development-rules.md`](../../dev-general-practices/standards/general-development-rules.md), quoted verbatim here so report consumers see the rule provenance:

> **Line 196** (Workflow Discipline → Hard Rules):
>
> > **No unconstrained generic subagents inside plan-marshall phase work** — Never spawn an unconstrained generic subagent (e.g. `Task: general-purpose`) for any work inside a phase (1-init through 6-finalize). Use `plan-marshall:execution-context-{level}` with a `workflow:` notation pointing at the workflow doc, or inline main-context execution. A generic subagent has no plan-marshall enforcement context, inherits broad tool access, and will violate workflow hard rules. Subagent rules propagate through the agent definition, not through the caller's prompt. (Lesson: `2026-04-24-12-001`.)

> **Line 241** (Quick Reference → Decision Matrix):
>
> > | About to spawn an unconstrained generic subagent for phase work | Use `plan-marshall:execution-context-{level}` with a `workflow:` notation, or inline main-context execution |

The audit is the mechanical observable for both rules: it consumes the standardized `[DISPATCH]` emissions and emits one finding per spawn that fails to ride the canonical envelope.

## Inputs

Two detection surfaces, read together so every spawn is pinned to both its intent (the resolved target) and its observable (the emitted log line):

- **Surface A — `logs/work.log` `[DISPATCH]` lines**: every line emitted by the canonical contract in `dispatch-logging.md` § "Emission contract" — prefix marker `[DISPATCH]` followed by the five literal field names `target`, `level`, `role`, `workflow`, `plan_id`. The audit grep's for `[DISPATCH] (` to scope the scan to dispatcher emissions (excluding generic `[STATUS]` lines that share the file).
- **Surface B — `logs/decision.log` `effort resolve-target` entries**: every `(plan-marshall:manage-config)` line whose body names a resolved role-key, captured by the resolver script when callers invoke `effort resolve-target --phase ... --role ...`. These are the *intent* records — they prove that a resolve happened and which role-key fired — and pair with Surface A's *observable* records to detect the missing-emission case (resolve happened, no `[DISPATCH]` line followed).

The audit also reads `logs/work.log` for raw `Task: general-purpose` text patterns. A `Task: general-purpose` mention anywhere in the work log (outside markdown documentation or escaped literals) is direct evidence of a generic-subagent spawn and is emitted as a finding regardless of whether a paired `[DISPATCH]` line exists.

## Detection Logic

The audit emits **one finding per spawn** that fails one of three checks. Each finding is `severity: error` — there is no warning tier because the underlying rule is a hard rule.

| Category | Failure mode | Detection signal |
|----------|--------------|------------------|
| `shape_violation` | A spawn happened but no matching `[DISPATCH]` line was emitted | A `(plan-marshall:manage-config)` `effort resolve-target` entry exists in `decision.log` for a given `role` value but no subsequent `[DISPATCH]` line carrying the same `role` appears in `work.log` within the same plan run |
| `envelope_violation` | A `[DISPATCH]` line carries a `target` value that is NOT `execution-context` or `execution-context-{level}` | Parse the `target=` field; any value outside the set `{execution-context, execution-context-low, execution-context-medium, execution-context-high, execution-context-xhigh, execution-context-xxhigh, execution-context-max}` is a finding |
| `generic_subagent_violation` | Direct `Task: general-purpose` invocation observed in the work log | Literal `Task: general-purpose` substring appears in `logs/work.log` outside fenced code blocks and outside `[ANTI-PATTERN]` annotations |

### Pairing rule

A `decision.log` `effort resolve-target` entry and a `work.log` `[DISPATCH]` line pair when:

1. The `role` value matches verbatim (e.g., both name `phase-2-refine` or both name `verification-feedback`).
2. The decision-log entry's timestamp precedes the dispatch-log entry's timestamp (same plan run).

When more than one resolve happens for the same role in a single run (legitimate — e.g., retries, multiple per-iteration dispatches), each resolve is paired with the next chronologically-following `[DISPATCH]` line carrying the same role. An unmatched resolve at end of pairing is a `shape_violation`.

## Finding Shape

```toon
aspect: execution-context-dispatch-audit
severity: error
category: {shape_violation|envelope_violation|generic_subagent_violation}
file: {relative path — "logs/work.log" or "logs/decision.log"}
line: {1-based line number}
snippet: "{trimmed line content, max 200 chars}"
message: "{Concrete description of the violation}"
```

`message` text per category:

- `shape_violation` → `"Resolve for role={role} at decision.log:{line} has no matching [DISPATCH] emission in work.log"`
- `envelope_violation` → `"[DISPATCH] line carries target={target} — not an execution-context envelope"`
- `generic_subagent_violation` → `"Direct Task: general-purpose invocation at work.log:{line}"`

## Output TOON Schema

```toon
aspect: execution-context-dispatch-audit
status: success
plan_id: {plan_id}
counts:
  total: N
  by_category:
    shape_violation: N
    envelope_violation: N
    generic_subagent_violation: N
findings[N]{category,file,line,snippet,severity,message}:
  shape_violation,logs/decision.log,42,"(plan-marshall:manage-config) effort resolve-target --role phase-2-refine","error","Resolve for role=phase-2-refine at decision.log:42 has no matching [DISPATCH] emission in work.log"
  envelope_violation,logs/work.log,87,"[DISPATCH] (plan-marshall:plan-marshall) target=general-purpose level=... role=phase-3-outline ...","error","[DISPATCH] line carries target=general-purpose — not an execution-context envelope"
  generic_subagent_violation,logs/work.log,103,"Task: general-purpose","error","Direct Task: general-purpose invocation at work.log:103"
```

The structural shape mirrors the neighbouring `direct-gh-glab-usage` aspect's output schema so downstream consumers (`compile-report`, lessons-proposal LLM pass) parse both with the same grammar.

## LLM Interpretation Rules

- Every finding MUST surface in the final report verbatim — the compiler does not reorder, group, or truncate them.
- A non-zero `counts.total` always produces at least one lessons-proposal entry (see [`../references/lessons-proposal.md`](../references/lessons-proposal.md)) categorized as `bug`, since each finding represents a hard-rule violation.
- `generic_subagent_violation` findings are the highest-priority remediation target — they indicate a `Task: general-purpose` spawn slipped past the dispatcher entirely. Propose these as blocking lessons (require fix before plan close) in user-invocable mode.
- `envelope_violation` findings indicate the caller emitted a `[DISPATCH]` line but routed it through the wrong target — typically a copy-paste mistake or a hand-rolled subagent that bypassed `effort resolve-target`. Propose these as `bug` lessons targeting the calling skill.
- `shape_violation` findings indicate the caller resolved a target but never emitted the canonical `[DISPATCH]` line — usually a missing instrumentation step in a workflow doc. Propose these as `improvement` lessons targeting the calling workflow file.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-execution-context-dispatch-audit.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect execution-context-dispatch-audit --fragment-file work/fragment-execution-context-dispatch-audit.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of [`../SKILL.md`](../SKILL.md). The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.

## Out of Scope

- **Markdown documentation outside `logs/`** — `dispatch-logging.md`, `dispatch-walkthrough.md`, this rule-set, and other standards docs reference `Task: general-purpose` and the canonical `[DISPATCH]` shape inside fenced code blocks and prose for instructional purposes. Those mentions are not dispatch evidence and are excluded by scoping the audit to `logs/work.log` and `logs/decision.log` only.
- **Archived plans** (`.plan/archived-plans/**`) — the audit reads only the active plan's `logs/` directory. Archived plans are inspected by the archived-mode invocation of the retrospective skill against their own scoped paths, never by a live plan's audit run.
- **Sonar / PR-review / external-tool finding loops** — those dispatches use their own envelope (`workflow-integration-sonar`, `workflow-integration-github`, etc.) and are audited by separate aspects (`direct-gh-glab-usage`, `script-failure-analysis`). The execution-context dispatch audit narrowly covers the `plan-marshall:execution-context-{level}` envelope only.
- **Automated remediation** — this aspect reports only; fixes are proposed as lessons in the report and applied in a separate plan.

## Cross-references

- [`../../dev-general-practices/standards/general-development-rules.md`](../../dev-general-practices/standards/general-development-rules.md) **lines 196 and 241** — the authoritative rule prohibiting unconstrained generic subagents inside plan-marshall phase work, and the Quick Reference decision-matrix row that directs callers to `plan-marshall:execution-context-{level}` instead.
- [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) — the standardized `[DISPATCH]` emission contract this audit consumes as evidence. See § "Emission contract" for the literal log-line shape (prefix marker, field order, field semantics, placement contract) — do NOT inline-copy the literal log shape here; enforcement-critical content lives in the central standard only.
- [`../SKILL.md`](../SKILL.md) — the orchestrator that dispatches this aspect at position 11 in the aspect order table.
- [`../references/lessons-proposal.md`](../references/lessons-proposal.md) — the lessons-proposal contract that consumes non-zero `counts.total` to seed bug-category lessons.
- [`./manifest-crosscheck.md`](./manifest-crosscheck.md) — neighbouring `standards/`-housed rule-set; structural precedent for housing an LLM-driven retrospective aspect outside the `references/` tree.
