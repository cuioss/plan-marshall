# Aspect: Execution-context Dispatch Audit

This aspect is **deterministic**: the `check-dispatch-audit` script (`scripts/check-dispatch-audit.py`) reads the plan's evidence and emits fact blocks; this document is the interpretation guide the LLM applies to those facts. The script never judges; this doc never runs code.

The audit consumes the standardized `[DISPATCH]` work-log lines specified in [`../../ref-workflow-architecture/standards/dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) as its primary evidence. It emits three fact blocks, **each publishing the size of the population it evaluated so a zero is legible** — a check that returns zero from an empty population reports `not_evaluated` with its reason, never a bare `0` a reader could mistake for evaluated-clean:

1. **`shape_violation` — did dispatch that RESOLVED get LOGGED?** Pairs the decision-log `effort resolve-target` records (Surface B — the resolve/intent side) against the `[DISPATCH]` work-log lines (Surface A — the observable side). Surface B is the left-hand side of the pairing, so when Surface B is empty the check is `not_evaluated`; a role whose resolve count exceeds its dispatch-line count is a `shape_violation`.
2. **`dispatch_coverage` — did dispatch that SHOULD have happened, happen?** Each terminal finalize step (`status.metadata.phase_steps["6-finalize"]`) is classified by its **token record** — the second, independent evidence source — into `dispatched` (non-zero `execution_log[]` `total_tokens`), `ran_inline` (a RECORDED zero), or `no_evidence` (no token row at all, OR a row whose `total_tokens` could not be read). A step **token-proven to have dispatched** whose `[DISPATCH]` line is nonetheless absent is a `missing_dispatch_emission` — an instrumentation finding against the DISPATCHER, never a "ran inline where dispatch was required" discipline finding against the step. A conditionally-dispatching step that legitimately ran inline carries a recorded-zero token record and lands in `ran_inline`, so the token evidence *is* the population-derived qualifier and no hand-maintained roster annotation is introduced. The block carries its own `status`: when `status.json` is absent, unreadable, not valid JSON, or carries no `metadata` mapping, the population could not be read and the block reports `not_evaluated` with a reason instead of an evaluated population of zero.
3. **`channel_completeness` — how trustworthy is the dispatch channel itself?** Publishes the **finalize-scoped** `[DISPATCH]`-line count against the `[STEP] Completed` count and the token-proven dispatched-step count — all three over the same finalize population — and downgrades the audit's own `confidence` when the channel is sparse. The all-caller line total rides alongside as `all_caller_dispatch_line_count`, each figure labelled with the population it was taken over, so whole-plan volume stays readable without becoming the comparand for a finalize verdict. A detector that consumes voluntarily-emitted evidence can only ever report a lower bound; this makes that shortfall visible rather than letting a sparse channel silently weaken every verdict. When every **finalize-scoped** input is zero the grade is `not_evaluated` with a reason — the fourth grade, added because its absence let a log-less plan grade `nominal`. ⛔ The predicate is taken over the three finalize-scoped figures ONLY; `all_caller_dispatch_line_count` is reported beside the grade and is deliberately not a term in it. It is taken over a SUPERSET population, so ANDing it on could only narrow the guard, never widen it — a plan carrying phase-5 `[DISPATCH]` lines, no `[STEP] Completed` line and no token-proven finalize dispatch has all three finalize inputs at zero and a non-zero all-caller total, and would fall past the guard (and past `none` and both `low`, which each require a completion or a proven dispatch) to `nominal` over an entirely empty finalize evaluation.

Two further deterministic checks preserve the aspect's original surface: `envelope_violation` (a `[DISPATCH]` line whose `target=` is not an execution-context envelope) and `generic_subagent_violation` (a raw `Task: general-purpose` in the work log). Each publishes its own `{status, evaluated_population, violations, findings}` block rather than only a count, so a zero over an empty work log and a zero over a populated clean one are distinguishable in the output — they were byte-identical while the two checks returned bare lists surfaced only as lengths.

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

> **Caller-blindness of the `[DISPATCH]` side — a matched pair does not prove the seam wrote both halves.** The pairing above compares COUNTS per role, and a `[DISPATCH]` line written by hand — by any caller other than the one that resolved the role — is counted on Surface A exactly like a seam-emitted one. So a role with one resolve and one hand-written line reads as matched, and its `shape_violation` delta is `0`: the hand-written line CANCELS the missing seam emission. That is the shape a clean `shape_violation` most often hides. The per-role breakdown therefore publishes `foreign_caller_lines` — `[DISPATCH]` lines for a role whose caller resolved nothing for it — as a FACT beside the signed `delta`. It is not a finding: a hand-written emission is not by itself a discipline failure, and raising one would start failing plans for a legitimate line. It is the discriminator between a corroborated clean verdict and a cancelled one. ⛔ **Re-derive the hand-written site list before quoting one** — an earlier audit counted seven and the tree has moved since; a count carried forward from that audit is a stale figure, not a measurement.

The audit also reads `logs/work.log` for raw `Task: general-purpose` text patterns. A `Task: general-purpose` mention anywhere in the work log (outside markdown documentation or escaped literals) is direct evidence of a generic-subagent spawn and is emitted as a finding regardless of whether a paired `[DISPATCH]` line exists.

Two additional surfaces support the coverage check (`dispatch_coverage`):

- **Surface C — `status.metadata.phase_steps["6-finalize"]` outcome records**: the per-step terminal-outcome map written by `manage-status mark-step-done`. Each step carries an `outcome` (`done` / `skipped` / `failed` / `loop_back`). A step present here reached a terminal outcome and is a member of the coverage population.
- **Surface E — `execution.toon` `execution_log[]` per-step token records**: `record-step` writes one row per finalize step — dispatched OR inline — carrying `step_id`, `phase`, and `total_tokens`. A **non-zero** `total_tokens` is written only when the step ran as a dispatched Task agent; an inline step records a measured `0`. ⛔ An **unreadable** `total_tokens` — no such column on the row, a non-integer value, a non-digit string — is mapped to `no_evidence`, never coerced to `0`: coercing it made an absence indistinguishable from a measurement and filed it under `ran_inline`, the bucket a reader treats as evidence the step ran inline. An EXPLICIT integer `0` still classifies `ran_inline`, which bounds the rule to rows that genuinely carry no reading. This is the **second, independent evidence source** the coverage check consults before ever concluding a step ran inline — the completion line (`[STEP] … Completed step: {step} (outcome={outcome})`) fires for inline steps too and so is a completion witness, never a dispatch discriminator. That line's shape is owned by the shared `_step_completion_marker` module, which this audit's read pattern is bound to rather than re-typing; the pattern leaves the `(outcome=…)` suffix OPTIONAL so completion lines in work logs written before the outcome was carried still count, since a retrospective necessarily reads older corpora and a suffix-requiring pattern would report those runs as having zero completions. The dispatched/inline *classification roster* (`phase-6-finalize/SKILL.md` § "Dispatched workflows vs inline steps") is therefore **not** consulted by the detector: the token record is the population-derived qualifier, which avoids a hand-maintained mirror of a derived set (the archetype the programme forbids). A conditionally-dispatching step that legitimately ran inline shows a measured-zero record and lands in `ran_inline` by construction, closing the false-positive direction.

## Detection Logic

The audit emits findings across the categories below, and **publishes the evaluated population beside every count** so a zero is legible. Each finding is `severity: error` — the underlying rules are hard rules — and `missing_dispatch_emission` is attributed to the dispatcher, not the step.

| Category | Failure mode | Detection signal |
|----------|--------------|------------------|
| `shape_violation` | A resolve happened but no matching `[DISPATCH]` line was emitted | For a given `role`, the count of `effort resolve-target` records (Surface B) exceeds the count of `[DISPATCH]` lines carrying that `role` (Surface A). **When Surface B is empty the check reports `not_evaluated` with its reason — never a bare `0`.** |
| `missing_dispatch_emission` | A step token-PROVEN to have dispatched emitted no `[DISPATCH]` line | The count of finalize steps with a non-zero `execution_log[]` token record (Surface E) exceeds the count of DISTINCT `(role, workflow)` `[DISPATCH]` emissions carrying the finalize dispatcher caller. Deduplicating on the PAIR is what keeps a re-fire from inflating the line side while still counting two different steps that resolve the same role as two emissions. The shortfall is an instrumentation gap in the DISPATCHER, never a discipline finding against any step, and it is a **floor for two independent reasons**: a re-fire adds lines but not steps, and a step whose token record is unreadable lands in `no_evidence` and is not counted as dispatched at all — so the token discriminator under-reports the gap in the same direction. |
| `envelope_violation` | A `[DISPATCH]` line carries a `target` that is NOT an execution-context envelope | Parse `target=`; any value outside `{execution-context, execution-context-level-1 … execution-context-level-7}` is a finding. |
| `generic_subagent_violation` | Direct `Task: general-purpose` invocation in the work log | Literal `Task: general-purpose` substring appears in `logs/work.log`. |

### Three-state coverage (replaces the old `dispatch_coverage_violation`)

The former `dispatch_coverage_violation` — "a DISPATCHED-classified step marked terminal with no `[DISPATCH]` line ran inline where dispatch was required" — is **removed**: it mis-attributed in both directions. A dispatched-but-unlogged step was read as a discipline violation against the *step* when the real fault is an instrumentation gap in the *dispatcher*; and a conditionally-dispatching step that legitimately ran inline was read as a coverage violation on essentially every plan of a common change type. In its place, `dispatch_coverage` classifies each terminal finalize step (Surface C) by its Surface E token record into `dispatched` (non-zero tokens), `ran_inline` (a RECORDED zero — an upper bound on inline execution, never proof of it), or `no_evidence` (no token row at all, or a row whose `total_tokens` could not be read — reported honestly, never as "ran inline"), publishes the population and the step ids each count was taken over, and raises only `missing_dispatch_emission`, attributed to the dispatcher.

### Pairing rule (shape_violation)

Each `role`'s `effort resolve-target` records (Surface B) are paired against the `[DISPATCH]` lines carrying the same `role` (Surface A) as a per-role multiset: a resolve count exceeding the dispatch count for a role is a `shape_violation` naming the shortfall. The population is the total Surface B record count, **derived from the log rather than a literal**; an empty population is `not_evaluated`, never `0`.

## Finding Shape

Each finding carries `severity`, `category`, and `message`. Message text per category:

- `shape_violation` → `"{n} resolve record(s) for role={role} in decision.log have no matching [DISPATCH] emission in work.log (resolved={r}, dispatched={d})"`
- `missing_dispatch_emission` → `"{k} finalize step(s) recorded non-zero token attribution (proof of a dispatched envelope) but only {j} distinct (role, workflow) [DISPATCH] line(s) carry the finalize dispatcher caller — {k−j} dispatch emission(s) missing. This is a FLOOR on the gap, for two independent reasons: a step whose token row is unreadable lands in no_evidence and is not counted as dispatched here at all, and a re-fire adds lines without adding steps. It is an instrumentation gap in the DISPATCHER, not an inline-execution (discipline) violation against any step."`
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
  findings[N]{severity,category,message}:
    …                            # this block's own sub-list, aggregated into the top-level findings
  by_role[N]{role,resolves,dispatch_lines,delta,foreign_caller_lines}:
    …                            # delta is SIGNED; delta<0 is a fact, not a finding
dispatch_coverage:
  status: {evaluated|not_evaluated}   # not_evaluated when the status.json population was unreadable
  evaluated_population: N        # terminal finalize steps (Surface C)
  dispatched: N                  # non-zero token record (Surface E)
  dispatched_steps[N]: […]       # the step ids the dispatched count was taken over
  ran_inline: N                  # RECORDED-zero token record — an upper bound, never proof
  no_evidence: N                 # no token row, OR a row whose total_tokens was unreadable
  no_evidence_steps[N]: […]
  missing_dispatch_emission: N
  reason: "…"                    # present only when not_evaluated
  findings[N]{severity,category,message}:
    …                            # this block's own sub-list, aggregated into the top-level findings
channel_completeness:
  dispatch_line_count: N              # FINALIZE-SCOPED, distinct (role, workflow) emissions
  dispatch_line_population: finalize_dispatcher_caller
  all_caller_dispatch_line_count: N   # every caller in the work log — reported, never the comparand
  all_caller_dispatch_line_population: every_caller_in_work_log
  completion_count: N            # [STEP] … Completed step: {step} (outcome={outcome}) lines
  dispatched_step_count: N
  ratio: N|null                  # dispatch_line_count / completion_count
  confidence: {not_evaluated|none|low|nominal}
  reason: "…"                    # present only when not_evaluated
envelope_violation:
  status: {evaluated|not_evaluated}
  evaluated_population: N        # [DISPATCH] spawn lines walked
  violations: N                  # == len(findings)
  findings[N]{severity,category,message}:
    …                            # this block's own sub-list, aggregated into the top-level findings
generic_subagent_violation:
  status: {evaluated|not_evaluated}
  evaluated_population: N        # work-log lines scanned
  violations: N                  # == len(findings)
  findings[N]{severity,category,message}:
    …
findings[N]{severity,category,message}:
  …                              # every block's sub-list concatenated, in block order
counts:
  total: N
  by_category:                   # every entry is STRUCTURED, never a bare integer
    shape_violation: {count, status, evaluated_population}
    missing_dispatch_emission: {count, status, evaluated_population}
    envelope_violation: {count, status, evaluated_population}
    generic_subagent_violation: {count, status, evaluated_population}
```

⛔ **`counts.by_category` entries carry their own `status`, and a consumer reading the count alone is reading half the value.** A `count: 0` under `status: not_evaluated` and a `count: 0` under `status: evaluated` are opposite statements — the first says the check never ran over anything, the second says it ran and the surface held. The entries were bare integers, which is what let a summary reader mistake the former for the latter.

## LLM Interpretation Rules

- Every finding MUST surface in the final report verbatim — the compiler does not reorder, group, or truncate them.
- **A `shape_violation.status: not_evaluated` is NOT a clean verdict.** It means the check evaluated nothing (Surface B empty), so it neither confirms nor denies dispatch-shape discipline. Report it as `not_evaluated` with its population and reason; do not read it as "clean".
- **A sparse channel downgrades confidence, and the confidence must be surfaced.** When `channel_completeness.confidence` is `not_evaluated`, `none` or `low`, every dispatch-discipline verdict the audit renders is a lower bound — say so. A `none` confidence means the audit saw no finalize `[DISPATCH]` evidence at all despite completions or token-proven dispatches. A **`not_evaluated`** confidence means every input to the grade was empty, so the audit has no channel verdict at all: report it with its reason and do NOT read it as a healthy channel. Act on all three, not only on `none` / `low`.
- **`ran_inline` is an UPPER BOUND on inline execution, never proof of it.** The bucket means *a recorded zero token attribution*. An inline step produces one — and so does a DISPATCHED step whose `<usage>` tag was never captured. Reading the bucket as "these steps ran inline" over-claims by exactly the size of the uncaptured-usage population. What it does rule out is an absent or unreadable record, which lands in `no_evidence`. Never quote `ran_inline` as evidence a step ran inline; quote it as the ceiling on how many could have.
- **A `dispatch_coverage.status: not_evaluated` is NOT an empty finalize phase.** It means the `status.json` population could not be read at all. Report it with its reason; do not read the accompanying zeros as "no finalize step reached a terminal outcome".
- A non-zero `counts.total` produces at least one lessons-proposal entry (see [`../references/lessons-proposal.md`](../references/lessons-proposal.md)).
- `generic_subagent_violation` findings are the highest-priority remediation target — a `Task: general-purpose` spawn slipped past the dispatcher entirely. Propose these as blocking lessons in user-invocable mode.
- `envelope_violation` findings indicate a `[DISPATCH]` line routed through the wrong target. Propose these as `bug` lessons targeting the calling skill.
- `shape_violation` findings indicate a resolve that never emitted its canonical `[DISPATCH]` line — usually a missing instrumentation step. Propose these as `improvement` lessons targeting the calling workflow file.
- **A clean `shape_violation` over a populated population does NOT show that dispatch discipline was verified.** It shows only that the emitter's two writes agree. Both surfaces are written by the SAME seam — the shared emitter in `manage-config/scripts/_cmd_effort.py`, which writes the `effort resolve-target` decision-log record and the `[DISPATCH]` work-log line together per firing — so their agreement is a consistency check on one emitter's output, never a completeness check on the set of dispatches. Read this rule together with the **Corroboration limit** blockquote and the **Caller-blindness** blockquote in § Inputs, four sections above: the first names what the shared emitter cannot witness, and the second names how a hand-written line CANCELS a missing seam emission so the delta reads `0`. Before calling a `violations: 0` clean, check `by_role[].foreign_caller_lines` — a non-zero value means the role's lines are not all seam-corroborated.
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
- [`./manifest-crosscheck.md`](./manifest-crosscheck.md) — neighbouring `standards/`-housed rule-set; structural precedent for housing a retrospective aspect's rule-set doc in `standards/` rather than the `references/` tree.
