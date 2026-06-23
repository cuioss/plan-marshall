# Aspect: Execution-context Dispatch Audit

This aspect audits dispatch discipline in **both directions**:

1. **Dispatch that happened rode the canonical envelope** — every execution-context spawn observed in a completed plan's `logs/work.log` rode the canonical `plan-marshall:execution-context-{level}` envelope — never `Task: general-purpose`, never an inline ad-hoc subagent dispatched outside the dispatcher.
2. **Dispatch that should have happened did** — every finalize/execute step the SKILL classifies as DISPATCHED that was marked terminal (`outcome=done`) carries matching `[DISPATCH]` work-log evidence; a step marked done with zero dispatch evidence is the inverse-coverage failure (inline execution where dispatch was required).

The audit consumes the standardized `[DISPATCH]` work-log lines specified in [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) as its primary evidence, pairs them with the matching `effort resolve-target` decision-log entries so every spawn is traceable from intent (role-key) through resolution (target/level) to invocation, and cross-references the SKILL's own dispatched/inline classification against the `phase_steps["6-finalize"]` outcome records to assert coverage. The inverse-coverage check is the deterministic structural guard the originating request asked for, anchored on the deterministic `[DISPATCH]` line shape so the pairing is mechanical.

**Conditional**: always runs; emits zero findings when the plan's dispatch trail is clean.

## Purpose

The plan-marshall workflow forbids unconstrained generic subagents inside phase work because subagent enforcement rules propagate through the agent definition rather than through the caller's prompt. A `Task: general-purpose` spawn loses the plan-marshall hard rules — `.plan/`-via-scripts-only, one-command-per-Bash, no-direct-`gh`/`glab`, structured-queries-first, build-via-architecture-resolve — that the canonical `execution-context-{level}` envelope carries by construction.

This rule has two authoritative anchors in [`../../persona-plan-marshall-agent/standards/agent-behavior-rules.md`](../../persona-plan-marshall-agent/standards/agent-behavior-rules.md), quoted verbatim here so report consumers see the rule provenance:

> § "Workflow Discipline → Hard Rules" (Unconstrained generic subagents):
>
> > **No unconstrained generic subagents inside plan-marshall phase work** — Never spawn an unconstrained generic subagent (e.g. `Task: general-purpose`) for any work inside a phase (1-init through 6-finalize). Use `plan-marshall:execution-context-{level}` with a `workflow:` notation pointing at the workflow doc, or inline main-context execution. A generic subagent has no plan-marshall enforcement context, inherits broad tool access, and will violate workflow hard rules. Subagent rules propagate through the agent definition, not through the caller's prompt. (Lesson: `2026-04-24-12-001`.)

> § "Quick Reference → Decision Matrix":
>
> > | About to spawn an unconstrained generic subagent for phase work | Use `plan-marshall:execution-context-{level}` with a `workflow:` notation, or inline main-context execution |

The audit is the mechanical observable for both rules: it consumes the standardized `[DISPATCH]` emissions and emits one finding per spawn that fails to ride the canonical envelope.

The aspect also owns the **inverse** of this discipline: a step the SKILL classifies as DISPATCHED that was nevertheless executed inline (marked `outcome=done` with no `[DISPATCH]` emission) is the recurring "ran phase-5/6 inline instead of dispatching execution-context subagents" defect. Keeping both directions in one aspect — rather than splitting the inverse-coverage check into a separate finalize completion-boundary assertion — is the deliberate design choice: the inverse check consumes the same two evidence surfaces (`work.log` + `decision.log`) this aspect already reads, plus the `phase_steps["6-finalize"]` outcome records, so one owner holds all of dispatch discipline. The design rationale (aspect-11 category vs finalize completion-boundary assertion) is resolved in favour of the retrospective aspect for exactly this reason.

## Inputs

Two detection surfaces, read together so every spawn is pinned to both its intent (the resolved target) and its observable (the emitted log line):

- **Surface A — `logs/work.log` `[DISPATCH]` lines**: every line emitted by the canonical contract in `dispatch-logging.md` § "Emission contract" — prefix marker `[DISPATCH]` followed by the five literal field names `target`, `level`, `role`, `workflow`, `plan_id`. The audit grep's for `[DISPATCH] (` to scope the scan to dispatcher emissions (excluding generic `[STATUS]` lines that share the file).
- **Surface B — `logs/decision.log` `effort resolve-target` entries**: every `(plan-marshall:manage-config)` line whose body names a resolved role-key, captured by the resolver script when callers invoke `effort resolve-target --phase ... --role ...`. These are the *intent* records — they prove that a resolve happened and which role-key fired — and pair with Surface A's *observable* records to detect the missing-emission case (resolve happened, no `[DISPATCH]` line followed).

The audit also reads `logs/work.log` for raw `Task: general-purpose` text patterns. A `Task: general-purpose` mention anywhere in the work log (outside markdown documentation or escaped literals) is direct evidence of a generic-subagent spawn and is emitted as a finding regardless of whether a paired `[DISPATCH]` line exists.

Two additional surfaces support the inverse-coverage check (`dispatch_coverage_violation`):

- **Surface C — `status.metadata.phase_steps["6-finalize"]` outcome records**: the per-step terminal-outcome map written by `manage-status mark-step-done`. Each step carries an `outcome` (`done` / `skipped` / `failed` / `loop_back`). Read via `manage-status read --plan-id {plan_id}`. A step marked `outcome=done` (or otherwise terminal) is the assertion target for the inverse-coverage check.
- **Surface D — the SKILL's dispatched/inline classification (the dispatched-step roster)**: the authoritative dispatched-vs-inline classification in [`../../phase-6-finalize/SKILL.md`](../../phase-6-finalize/SKILL.md) § "Dispatched workflows vs inline steps" (finalize steps) and the execute-phase dispatch in [`../../plan-marshall/workflow/execution.md`](../../plan-marshall/workflow/execution.md) § "Execute Phase" (the phase-5-execute envelope). This classification is the roster of steps that MUST carry a `[DISPATCH]` line when marked terminal.

## Detection Logic

The audit emits **one finding per violation** across four checks. Each finding is `severity: error` — there is no warning tier because the underlying rule is a hard rule. The first three categories check that dispatch that DID happen rode the canonical envelope; the fourth (`dispatch_coverage_violation`) checks the inverse — that dispatch that SHOULD have happened did.

| Category | Failure mode | Detection signal |
|----------|--------------|------------------|
| `shape_violation` | A spawn happened but no matching `[DISPATCH]` line was emitted | A `(plan-marshall:manage-config)` `effort resolve-target` entry exists in `decision.log` for a given `role` value but no subsequent `[DISPATCH]` line carrying the same `role` appears in `work.log` within the same plan run |
| `envelope_violation` | A `[DISPATCH]` line carries a `target` value that is NOT `execution-context` or `execution-context-{level}` | Parse the `target=` field; any value outside the set `{execution-context, execution-context-level-1, execution-context-level-2, execution-context-level-3, execution-context-level-4, execution-context-level-5, execution-context-level-6, execution-context-level-7}` is a finding |
| `generic_subagent_violation` | Direct `Task: general-purpose` invocation observed in the work log | Literal `Task: general-purpose` substring appears in `logs/work.log` outside fenced code blocks and outside `[ANTI-PATTERN]` annotations |
| `dispatch_coverage_violation` | A finalize/execute step the SKILL classifies as DISPATCHED was marked `outcome=done` (or otherwise terminal) on `status.metadata.phase_steps["6-finalize"]` with zero matching `[DISPATCH]` work-log evidence | For each step the dispatched/inline classification (Surface D — `phase-6-finalize/SKILL.md` § "Dispatched workflows vs inline steps" and the execute-phase dispatch in `execution.md`) marks DISPATCHED, confirm at least one `[DISPATCH]` line in `work.log` (Surface A) carries the step's role/workflow within the same plan run. A step whose `phase_steps["6-finalize"]` record (Surface C) shows a terminal `outcome` with no such `[DISPATCH]` line is a finding — the step ran inline where dispatch was required |

### Pairing rule

A `decision.log` `effort resolve-target` entry and a `work.log` `[DISPATCH]` line pair when:

1. The `role` value matches verbatim (e.g., both name `phase-2-refine` or both name `verification-feedback`).
2. The decision-log entry's timestamp precedes the dispatch-log entry's timestamp (same plan run).

When more than one resolve happens for the same role in a single run (legitimate — e.g., retries, multiple per-iteration dispatches), each resolve is paired with the next chronologically-following `[DISPATCH]` line carrying the same role. An unmatched resolve at end of pairing is a `shape_violation`.

## Finding Shape

```toon
aspect: execution-context-dispatch-audit
severity: error
category: {shape_violation|envelope_violation|generic_subagent_violation|dispatch_coverage_violation}
file: {relative path — "logs/work.log", "logs/decision.log", or "status.json"}
line: {1-based line number}
snippet: "{trimmed line content, max 200 chars}"
message: "{Concrete description of the violation}"
```

`message` text per category:

- `shape_violation` → `"Resolve for role={role} at decision.log:{line} has no matching [DISPATCH] emission in work.log"`
- `envelope_violation` → `"[DISPATCH] line carries target={target} — not an execution-context envelope"`
- `generic_subagent_violation` → `"Direct Task: general-purpose invocation at work.log:{line}"`
- `dispatch_coverage_violation` → `"Step {step} classified DISPATCHED reached a terminal outcome ({outcome}) at phase_steps with no matching [DISPATCH] emission in work.log"`

For a `dispatch_coverage_violation`, `file` is `status.json` (the `phase_steps` record source) and `snippet` is the trimmed `phase_steps["6-finalize"][{step}]` outcome record.

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
    dispatch_coverage_violation: N
findings[N]{category,file,line,snippet,severity,message}:
  shape_violation,logs/decision.log,42,"(plan-marshall:manage-config) effort resolve-target --role phase-2-refine","error","Resolve for role=phase-2-refine at decision.log:42 has no matching [DISPATCH] emission in work.log"
  envelope_violation,logs/work.log,87,"[DISPATCH] (plan-marshall:plan-marshall) target=general-purpose level=... role=phase-3-outline ...","error","[DISPATCH] line carries target=general-purpose — not an execution-context envelope"
  generic_subagent_violation,logs/work.log,103,"Task: general-purpose","error","Direct Task: general-purpose invocation at work.log:103"
  dispatch_coverage_violation,status.json,0,"phase_steps[6-finalize][plugin-doctor]: outcome=done","error","Step plugin-doctor classified DISPATCHED reached a terminal outcome (done) at phase_steps with no matching [DISPATCH] emission in work.log"
```

The structural shape mirrors the neighbouring `direct-gh-glab-usage` aspect's output schema so downstream consumers (`compile-report`, lessons-proposal LLM pass) parse both with the same grammar.

## LLM Interpretation Rules

- Every finding MUST surface in the final report verbatim — the compiler does not reorder, group, or truncate them.
- A non-zero `counts.total` always produces at least one lessons-proposal entry (see [`../references/lessons-proposal.md`](../references/lessons-proposal.md)) categorized as `bug`, since each finding represents a hard-rule violation.
- `generic_subagent_violation` findings are the highest-priority remediation target — they indicate a `Task: general-purpose` spawn slipped past the dispatcher entirely. Propose these as blocking lessons (require fix before plan close) in user-invocable mode.
- `envelope_violation` findings indicate the caller emitted a `[DISPATCH]` line but routed it through the wrong target — typically a copy-paste mistake or a hand-rolled subagent that bypassed `effort resolve-target`. Propose these as `bug` lessons targeting the calling skill.
- `shape_violation` findings indicate the caller resolved a target but never emitted the canonical `[DISPATCH]` line — usually a missing instrumentation step in a workflow doc. Propose these as `improvement` lessons targeting the calling workflow file.
- `dispatch_coverage_violation` findings indicate a step classified DISPATCHED was executed inline (reached a terminal outcome — `done`, `skipped`, `failed`, or `loop_back` — with no `[DISPATCH]` evidence) — the "ran the work inline instead of dispatching the execution-context subagent" defect. Propose these as `bug` lessons targeting the inlining caller (the orchestrator/skill that drove the step), since the inline execution bypassed the canonical envelope's enforcement contract.

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

- [`../../persona-plan-marshall-agent/standards/agent-behavior-rules.md`](../../persona-plan-marshall-agent/standards/agent-behavior-rules.md) § "Unconstrained generic subagents" and "Quick Reference decision-matrix" — the authoritative rule prohibiting unconstrained generic subagents inside plan-marshall phase work, and the Quick Reference decision-matrix row that directs callers to `plan-marshall:execution-context-{level}` instead.
- [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) — the standardized `[DISPATCH]` emission contract this audit consumes as evidence. See § "Emission contract" for the literal log-line shape (prefix marker, field order, field semantics, placement contract) — do NOT inline-copy the literal log shape here; enforcement-critical content lives in the central standard only.
- [`../SKILL.md`](../SKILL.md) — the orchestrator that dispatches this aspect at position 11 in the aspect order table.
- [`../references/lessons-proposal.md`](../references/lessons-proposal.md) — the lessons-proposal contract that consumes non-zero `counts.total` to seed bug-category lessons.
- [`./manifest-crosscheck.md`](./manifest-crosscheck.md) — neighbouring `standards/`-housed rule-set; structural precedent for housing an LLM-driven retrospective aspect outside the `references/` tree.
