# Aspect: Execution-context Dispatch Audit

This aspect is **deterministic**: the `check-dispatch-audit` script (`scripts/check-dispatch-audit.py`) reads the plan's evidence and emits fact blocks; this document is the interpretation guide the LLM applies to those facts. The script never judges; this doc never runs code.

The audit consumes the standardized `[DISPATCH]` work-log lines specified in [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) as its primary evidence. It emits three fact blocks, **each publishing the size of the population it evaluated so a zero is legible** — a check that returns zero from an empty population reports `not_evaluated` with its reason, never a bare `0` a reader could mistake for evaluated-clean:

1. **`shape_violation` — did dispatch that RESOLVED get LOGGED?** Pairs the decision-log `effort resolve-target` records (Surface B — the resolve/intent side) against the `[DISPATCH]` work-log lines (Surface A — the observable side). Surface B is the left-hand side of the pairing, so when Surface B is empty the check is `not_evaluated`; a role whose resolve count exceeds its dispatch-line count is a `shape_violation`.
2. **`dispatch_coverage` — did dispatch that SHOULD have happened, happen?** Each terminal finalize step (`status.metadata.phase_steps["6-finalize"]`) is classified by its **token record** — the second, independent evidence source — into `dispatched` (non-zero `execution_log[]` `total_tokens`), `ran_inline` (a measured zero), or `no_evidence` (no token row). A step **token-proven to have dispatched** whose `[DISPATCH]` line is nonetheless absent is a `missing_dispatch_emission` — an instrumentation finding against the DISPATCHER, never a "ran inline where dispatch was required" discipline finding against the step. A conditionally-dispatching step that legitimately ran inline carries a measured-zero token record and lands in `ran_inline`, so the token evidence *is* the population-derived qualifier and no hand-maintained roster annotation is introduced.
3. **`channel_completeness` — how trustworthy is the dispatch channel itself?** Publishes the `[DISPATCH]`-line count against the `[STEP] Completed` count and the token-proven dispatched-step count, and downgrades the audit's own `confidence` when the channel is sparse. A detector that consumes voluntarily-emitted evidence can only ever report a lower bound; this makes that shortfall visible rather than letting a sparse channel silently weaken every verdict.

Two further deterministic checks preserve the aspect's original surface: `envelope_violation` (a `[DISPATCH]` line whose `target=` is not an execution-context envelope) and `generic_subagent_violation` (a raw `Task: general-purpose` in the work log).

**Conditional**: always runs. A clean trail emits populated counts with zero findings; an empty evidence surface reports `not_evaluated` / `no_evidence` with its reason.

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

The aspect also owns **coverage** — whether dispatch that should have happened, happened — but it asserts this from **evidence**, never by trusting a hand-maintained roster. Rather than flagging every DISPATCHED-classified step marked terminal with no `[DISPATCH]` line as "ran inline where dispatch was required" (a finding that mis-attributed in both directions), it reads each terminal finalize step's **token record** and classifies it `dispatched` / `ran_inline` / `no_evidence`. A step token-proven to have dispatched whose `[DISPATCH]` line is missing is an instrumentation gap in the dispatcher (`missing_dispatch_emission`); a step that ran inline — whether a rostered-inline step or a conditionally-dispatching one that legitimately did not dispatch — carries a measured-zero record and raises nothing. The token record is the population-derived qualifier, so no dispatched/inline roster is consulted and no hand-maintained mirror is introduced.

## Inputs

Two detection surfaces, read together so every spawn is pinned to both its intent (the resolved target) and its observable (the emitted log line):

- **Surface A — `logs/work.log` `[DISPATCH]` lines**: every line emitted by the canonical contract in `dispatch-logging.md` § "Emission contract" — prefix marker `[DISPATCH]` followed by the five literal field names `target`, `level`, `role`, `workflow`, `plan_id`. The audit grep's for `[DISPATCH] (` to scope the scan to dispatcher emissions (excluding generic `[STATUS]` lines that share the file).
- **Surface B — `logs/decision.log` `effort resolve-target` entries**: every `(plan-marshall:manage-config)` line whose body names a resolved role-key, emitted by the resolver itself when a caller invokes `effort resolve-target` with the dispatch context (`--workflow`). These are the *intent* records — they prove that a resolve happened and which role-key fired — and pair with Surface A's *observable* records.

> **Corroboration limit — the two surfaces share one emitter, so their agreement is a consistency check and never a completeness one.** Since the [`dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) seam emission landed, BOTH Surface A (the `[DISPATCH]` work-log line) and Surface B (the `effort resolve-target` decision-log record) are written by the SAME call — `effort resolve-target` emits them together, per firing, from the one resolution seam. That is what closes the retry-blindness that a per-role hand-written step left open — but it also means the two surfaces are not independent witnesses. Their agreement proves only that the seam ran; it does NOT prove that a dispatch actually rode the canonical envelope or completed. A dispatch that bypassed the seam entirely (a raw `Task: general-purpose`, or any spawn that never resolved a target) is absent from BOTH surfaces at once, and their matching absence reads as "clean." So pairing Surface A against Surface B is a **consistency** check on the emitter's own output, never a **completeness** check on the set of dispatches. A completeness verdict needs a third source with an emitter INDEPENDENT of the seam; no such source exists in the `logs/` this audit reads, and this audit therefore never treats A↔B agreement as evidence that every dispatch was recorded. (This paragraph states what the emitter guarantees; it changes no check's logic.)

The audit also reads `logs/work.log` for raw `Task: general-purpose` text patterns. A `Task: general-purpose` mention anywhere in the work log (outside markdown documentation or escaped literals) is direct evidence of a generic-subagent spawn and is emitted as a finding regardless of whether a paired `[DISPATCH]` line exists.

Two additional surfaces support the coverage check (`dispatch_coverage`):

- **Surface C — `status.metadata.phase_steps["6-finalize"]` outcome records**: the per-step terminal-outcome map written by `manage-status mark-step-done`. Each step carries an `outcome` (`done` / `skipped` / `failed` / `loop_back`). A step present here reached a terminal outcome and is a member of the coverage population.
- **Surface E — `execution.toon` `execution_log[]` per-step token records**: `record-step` writes one row per finalize step — dispatched OR inline — carrying `step_id`, `phase`, and `total_tokens`. A **non-zero** `total_tokens` is written only when the step ran as a dispatched Task agent; an inline step records a measured `0`. This is the **second, independent evidence source** the coverage check consults before ever concluding a step ran inline — the completion line (`[STEP] … Completed step:`) fires for inline steps too and so is a completion witness, never a dispatch discriminator. The dispatched/inline *classification roster* (`phase-6-finalize/SKILL.md` § "Dispatched workflows vs inline steps") is therefore **not** consulted by the detector: the token record is the population-derived qualifier, which avoids a hand-maintained mirror of a derived set (the archetype the programme forbids). A conditionally-dispatching step that legitimately ran inline shows a measured-zero record and lands in `ran_inline` by construction, closing the false-positive direction.

## Detection Logic

The audit emits findings across the categories below, and **publishes the evaluated population beside every count** so a zero is legible. Each finding is `severity: error` — the underlying rules are hard rules — and `missing_dispatch_emission` is attributed to the dispatcher, not the step.

| Category | Failure mode | Detection signal |
|----------|--------------|------------------|
| `shape_violation` | A resolve happened but no matching `[DISPATCH]` line was emitted | For a given `role`, the count of `effort resolve-target` records (Surface B) exceeds the count of `[DISPATCH]` lines carrying that `role` (Surface A). **When Surface B is empty the check reports `not_evaluated` with its reason — never a bare `0`.** |
| `missing_dispatch_emission` | A step token-PROVEN to have dispatched emitted no `[DISPATCH]` line | The count of finalize steps with a non-zero `execution_log[]` token record (Surface E) exceeds the count of `[DISPATCH]` lines carrying the finalize dispatcher caller. The shortfall is an instrumentation gap in the DISPATCHER, never a discipline finding against any step (a floor — a re-fire adds lines but not steps). |
| `envelope_violation` | A `[DISPATCH]` line carries a `target` that is NOT an execution-context envelope | Parse `target=`; any value outside `{execution-context, execution-context-level-1 … execution-context-level-7}` is a finding. |
| `generic_subagent_violation` | Direct `Task: general-purpose` invocation in the work log | Literal `Task: general-purpose` substring appears in `logs/work.log`. |

### Three-state coverage (replaces the old `dispatch_coverage_violation`)

The former `dispatch_coverage_violation` — "a DISPATCHED-classified step marked terminal with no `[DISPATCH]` line ran inline where dispatch was required" — is **removed**: it mis-attributed in both directions. A dispatched-but-unlogged step was read as a discipline violation against the *step* when the real fault is an instrumentation gap in the *dispatcher*; and a conditionally-dispatching step that legitimately ran inline was read as a coverage violation on essentially every plan of a common change type. In its place, `dispatch_coverage` classifies each terminal finalize step (Surface C) by its Surface E token record into `dispatched` (non-zero tokens), `ran_inline` (a measured zero), or `no_evidence` (no token row at all — reported honestly, never as "ran inline"), publishes the population, and raises only `missing_dispatch_emission`, attributed to the dispatcher.

### Pairing rule (shape_violation)

Each `role`'s `effort resolve-target` records (Surface B) are paired against the `[DISPATCH]` lines carrying the same `role` (Surface A) as a per-role multiset: a resolve count exceeding the dispatch count for a role is a `shape_violation` naming the shortfall. The population is the total Surface B record count, **derived from the log rather than a literal**; an empty population is `not_evaluated`, never `0`.

## Finding Shape

Each finding carries `severity`, `category`, and `message`. Message text per category:

- `shape_violation` → `"{n} resolve record(s) for role={role} in decision.log have no matching [DISPATCH] emission in work.log (resolved={r}, dispatched={d})"`
- `missing_dispatch_emission` → `"{k} finalize step(s) recorded non-zero token attribution (proof of a dispatched envelope) but only {j} [DISPATCH] line(s) carry the finalize dispatcher caller — {k−j} dispatch emission(s) missing. Instrumentation gap in the DISPATCHER, not an inline-execution (discipline) violation against any step."`
- `envelope_violation` → `"[DISPATCH] line carries target={target} — not an execution-context envelope"`
- `generic_subagent_violation` → `"Direct Task: general-purpose invocation in work.log: {line}"`

## Output TOON Schema

The `check-dispatch-audit` script emits this shape. Every count sits beside the population it was computed over.

```toon
status: success
aspect: execution-context-dispatch-audit
plan_id: {plan_id}
summary: "{one-line human summary}"
shape_violation:
  status: {evaluated|not_evaluated}
  evaluated_population: N        # Surface B resolve-record count (the left-hand side)
  violations: N
  reason: "…"                    # present only when not_evaluated
dispatch_coverage:
  evaluated_population: N        # terminal finalize steps (Surface C)
  dispatched: N                  # non-zero token record (Surface E)
  ran_inline: N                  # measured-zero token record
  no_evidence: N                 # no token row at all
  missing_dispatch_emission: N
channel_completeness:
  dispatch_line_count: N
  completion_count: N            # [STEP] … Completed step: lines
  dispatched_step_count: N
  ratio: N|null                  # dispatch_line_count / completion_count
  confidence: {none|low|nominal}
findings[N]{severity,category,message}:
  …
counts:
  total: N
  by_category:
    shape_violation: N
    missing_dispatch_emission: N
    envelope_violation: N
    generic_subagent_violation: N
```

## LLM Interpretation Rules

- Every finding MUST surface in the final report verbatim — the compiler does not reorder, group, or truncate them.
- **A `shape_violation.status: not_evaluated` is NOT a clean verdict.** It means the check evaluated nothing (Surface B empty), so it neither confirms nor denies dispatch-shape discipline. Report it as `not_evaluated` with its population and reason; do not read it as "clean".
- **A sparse channel downgrades confidence, and the confidence must be surfaced.** When `channel_completeness.confidence` is `none` or `low`, every dispatch-discipline verdict the audit renders is a lower bound — say so. A `none` confidence means the audit saw no `[DISPATCH]` evidence at all despite completions or token-proven dispatches.
- A non-zero `counts.total` produces at least one lessons-proposal entry (see [`../references/lessons-proposal.md`](../references/lessons-proposal.md)).
- `generic_subagent_violation` findings are the highest-priority remediation target — a `Task: general-purpose` spawn slipped past the dispatcher entirely. Propose these as blocking lessons in user-invocable mode.
- `envelope_violation` findings indicate a `[DISPATCH]` line routed through the wrong target. Propose these as `bug` lessons targeting the calling skill.
- `shape_violation` findings indicate a resolve that never emitted its canonical `[DISPATCH]` line — usually a missing instrumentation step. Propose these as `improvement` lessons targeting the calling workflow file.
- `missing_dispatch_emission` findings indicate a step **token-proven to have dispatched** whose `[DISPATCH]` line is absent — an instrumentation gap in the **dispatcher**, not an inline-execution violation against the step. Propose these as `bug` lessons targeting the dispatch seam / dispatcher, never the step. Do NOT re-derive "ran inline where dispatch was required" from a `ran_inline` or `no_evidence` classification: those are the mis-attribution this detector was corrected to stop making.

## Persistence

The aspect is script-backed: run `check-dispatch-audit` and pipe its stdout to the fragment file, then register it. The orchestrator does not hand-synthesize this fragment.

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:check-dispatch-audit \
  run --plan-id {plan_id} --mode {live|archived} > work/fragment-execution-context-dispatch-audit.toon
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
