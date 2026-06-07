---
name: audit-archived-plan-retrospectives
description: Audit archived plans across fifteen retrospective checks — execution-manifest correctness, quality-verification findings, metrics anomalies, cross-plan recurring patterns, token-efficiency trend, scope-estimate accuracy, PR-merge velocity, task-count efficiency, global-log analysis, token-economics, quality-chain, sequence-and-build-minimality, input-integrity corpus completeness, task-graph redundancy, and cross-check-synthesis facet-completeness — file lessons through the three-gate policy, and dormate reviewed plans
user-invocable: true
allowed-tools: Bash, Read, Grep, Write, AskUserQuestion
---

# Audit Archived Plan Retrospectives (project-local)

Fifteen-check retrospective auditor over the archived-plan corpus. The skill is
the LLM-driven orchestration narrative; `scripts/audit.py` is the deterministic
computation core. The orchestrator selects which checks to run, surfaces each
check's script-computed TOON verbatim, drives lesson filing through the
three-gate `lesson-creation-policy.md` sequence, and runs the interactive
dormation step that relocates reviewed plans to `.plan/temp/dormated-plans/`.

The skill is **project-local** because it operates on
`.plan/local/archived-plans/` — a directory that only exists in this
meta-project. Consumer projects of plan-marshall have no equivalent corpus.

## Hybrid design: script computes, LLM orchestrates

`scripts/audit.py` performs all deterministic per-plan and cross-plan
computation and emits each check's rows as bespoke TOON. `SKILL.md` (this body)
is the LLM half: it chooses the checks, reads the emitted rows, decides whether
a surfaced signal warrants a lesson, and confirms the destructive dormation
move via `AskUserQuestion`. The boundary is strict — the script computes and
emits; the LLM interprets, files lessons, and confirms destructive moves. The
script never mutates a plan artifact except the explicitly-confirmed dormation
move.

Per `extension-api/standards/dispatch-granularity.md` Heuristic 1, every check's
core computation is a deterministic predicate over file-derived inputs, so it
stays inside the script rather than spawning a subagent. The slash command is the
LLM-friendly invocation of that script plus the orchestration this body
describes — no subagent is spawned.

## Enforcement

**Execution mode**: Select the checks to run, invoke the audit script for each
selected check, and surface its TOON report verbatim; do not paraphrase rule
names, anomaly classes, or verdicts that the script did not emit.

**Prohibited actions**:
- Do NOT mutate any plan artifact other than the explicitly-confirmed dormation
  move. Every check is read-only against `.plan/local/archived-plans/` and
  `.plan/local/plans/`.
- Do NOT re-derive any check's computation inline in the chat; if a check's
  logic changes, edit `scripts/audit.py` and re-run.
- Do NOT fall back to interpreting `solution_outline.md` prose when the
  structured inputs (`references.json`, `status.json::metadata`,
  `metrics.toon`, `execution.toon`, `tasks/TASK-*.json`,
  `artifacts/findings/*.jsonl`) are present — prose interpretation is
  non-deterministic and was the source of contradictory verdicts in earlier
  ad-hoc audits.
- Do NOT run the dormation move without an explicit user confirmation obtained
  via `AskUserQuestion`; the script's move function refuses to run unless the
  orchestrator passes the confirmed flag.
- Do NOT file a lesson without first running the three-gate policy
  (`lesson-creation-policy.md`) — dedup, active-plan check, then create.
- Do NOT spot-check, skim, or sample a subset of check blocks and generalize a
  verdict to the rest. EVERY emitted check block MUST be processed against its
  `checks/{name}.md` sub-document.
- Do NOT conclude "all healthy" / "no findings" / "all sensible" unless that
  conclusion is backed by a per-check, per-row adjudication with cited evidence.
  A blanket dismissal not grounded in per-row evidence is a contract violation.
- Do NOT drop a candidate signal as "already covered" / "already filed" without
  first VERIFYING that claim against the lessons corpus and the archived-plan
  corpus (the matching lesson ID or covering active-plan ID must be named).
  Assumption is not verification.

**Constraints**:
- The script is invoked exactly as written in the workflow steps — no
  PYTHONPATH override, no inlined Python, no `find`/`grep` substitutes for the
  script's own filesystem walk.
- When `--plan-id` narrows the scan, the same TOON shape is emitted (single
  row per check) so downstream tooling can consume both forms uniformly.
- When `--check {name}` narrows to one check, only that check's TOON block is
  emitted.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--plan-dir PATH` | optional | Override the default `.plan/local/archived-plans` root. Useful when auditing a vendored snapshot. |
| `--plan-id ID` | optional | Restrict the scan to one archived plan (its directory basename). |
| `--include-active` | optional | Additionally scan `.plan/local/plans/` so in-flight plans are reported alongside archived ones. Active plans without a manifest are reported as `incomplete`, not `drift`. |
| `--check NAME` | optional | Run a single check instead of all. Valid names: `execution-context-manifest`, `quality-verification-report`, `metrics`, `recurring-pattern-detector`, `token-efficiency-trend`, `scope-estimate-accuracy`, `pr-merge-velocity`, `task-count-efficiency`, `global-log-analysis`, `token-economics`, `quality-chain`, `sequence-and-build-minimality`, `input-integrity`, `task-graph-redundancy`, `cross-check-synthesis`. Default: run every check. When `--check cross-check-synthesis` is selected, the script still computes the upstream checks it consumes (without emitting their blocks) so the synthesis can fire. |
| `--dormate ID [ID ...] --confirmed` | optional | Relocate one or more archived plans to `.plan/temp/dormated-plans/{plan_id}/`. Accepts an explicit list of plan IDs; duplicate IDs are deduplicated silently. The whole batch is all-or-nothing — a single grammar violation, missing source, or pre-existing destination refuses the entire batch with nothing moved. Inert (refused, exit 0) without `--confirmed`. The interactive confirmation is owned by the LLM body (Step 5), never delegated to the script. |
| `--dormate-all --confirmed` | optional | Relocate EVERY archived plan under `.plan/local/archived-plans/` to `.plan/temp/dormated-plans/` in one call. Same all-or-nothing posture as `--dormate`. Inert (refused, exit 0) without `--confirmed`. The body MUST surface the full would-move plan list before confirming (Step 5). |
| `--dormate-global-logs --confirmed` | optional | Relocate COMPLETE past-date global logs (`{prefix}-YYYY-MM-DD.log`) from `.plan/local/logs/` to `.plan/temp/dormated-plans/global-logs/`. Today's still-active log is never moved. Inert (refused, exit 0) without `--confirmed`; on a destination-name clash the whole move refuses (`status: error`) rather than overwriting. The interactive confirmation is owned by the LLM body (Step 5), never delegated to the script. |

## Available checks

Each check is documented in a self-contained sub-document under `checks/`. The
sub-document records what `scripts/audit.py` computes for that check, the inputs
it reads, the emitted columns, and how the orchestrator interprets and acts on
the rows.

| Check | Sub-document | Surfaces |
|-------|--------------|----------|
| Execution-manifest correctness | [`checks/execution-context-manifest.md`](checks/execution-context-manifest.md) | Persisted `execution.toon` vs the re-derived seven-row rule; the `name_drift` signal. |
| Quality-verification report | [`checks/quality-verification-report.md`](checks/quality-verification-report.md) | Findings present, proposed lessons, and whether each was already filed. |
| Metrics anomalies | [`checks/metrics.md`](checks/metrics.md) | Disproportionate token usage, incomplete recordings, impossible values, optimization signals. |
| Recurring-pattern detector | [`checks/recurring-pattern-detector.md`](checks/recurring-pattern-detector.md) | Cross-plan finding signatures appearing in N≥3 plans as systemic signals. |
| Token-efficiency trend | [`checks/token-efficiency-trend.md`](checks/token-efficiency-trend.md) | Chronological tokens-per-phase regression across the corpus. |
| Scope-estimate accuracy | [`checks/scope-estimate-accuracy.md`](checks/scope-estimate-accuracy.md) | Declared `scope_estimate` vs actual affected/modified file count. |
| PR-merge velocity | [`checks/pr-merge-velocity.md`](checks/pr-merge-velocity.md) | PR open-to-merge duration; long-review-cycle flagging. |
| Task-count efficiency | [`checks/task-count-efficiency.md`](checks/task-count-efficiency.md) | Under-decomposed / over-decomposed task-count outliers. |
| Global-log analysis | [`checks/global-log-analysis.md`](checks/global-log-analysis.md) | Cross-plan `.plan/local/logs/` parse: error/warning lines, slow calls, high-frequency callers, impossible/hang durations, and test-fixture leaks — correlated to plan execution windows. |
| Token economics | [`checks/token-economics.md`](checks/token-economics.md) | Cross-plan per-phase token shares + efficiency ratios joined to scope/change_type, with corpus-derived (never hard-coded) anti-pattern flags: fixed-overhead floor, planning≫execute, outline/refine/finalize-heavy, big-spend-tiny-footprint, long sessions, execute-metrics blindness. |
| Quality chain | [`checks/quality-chain.md`](checks/quality-chain.md) | Cross-plan findings classified by mechanism (build / self-review / auto-review / human-review) × resolution (direct_fix / loop_back / rerun_flake / accepted / suppressed / pending / lesson); per-plan matrix + corpus totals, chain anti-pattern flags (build_pending_pile, auto_review_only, review_body_duplicate, no_qgate6), and shift-left tiering (Tier 1-4) of auto-review findings against the ext-self-review surfacer remit. Per-finding rows, walked step-by-step. |
| Sequence and build minimality | [`checks/sequence-and-build-minimality.md`](checks/sequence-and-build-minimality.md) | Cross-plan call-sequence reconstruction from `logs/script-execution.log`, bucketed into phases by the `logs/work.log` `[DISPATCH] role=phase-N` timeline; per-build duration classification (minimal `<120s` / scoped / heavy `>400s`) and work.log build-verb mining (verify / scoped-vs-all module-tests / quality-gate / coverage / compile), with redundancy / non-minimality flags (build_churn, non_minimal_build, docs_only_build, ci_rerun, phase_reentry, arch_over_resolution, consecutive_dup). Carries three structural caveats (finalize-fold conflation, verify-count-upper-bound vs heavy-duration-floor, consecutive_dup over-count) documented in the sub-doc. |
| Input integrity | [`checks/input-integrity.md`](checks/input-integrity.md) | Per-plan input presence/health (execution.toon / metrics.toon / references.json / tasks/ / artifacts/findings/ / logs/script-execution.log) plus three input-health flags (metrics_blind, incomplete_lifecycle, missing_dispatch_markers) and a corpus data_confidence summary (fully-recorded / partial / blind). The **no-false-healthy foundation**: every other check MUST annotate rows derived from a metrics_blind plan as "floor, not truth", and no check may claim "all healthy" over blind-input plans. |
| Task-graph redundancy | [`checks/task-graph-redundancy.md`](checks/task-graph-redundancy.md) | Per-plan task-graph adjacency over `tasks/TASK-*.json`: `multi_task_file` (a file edited by ≥2 tasks — the primary duplicate-task signal), `dup_substep` (same `(target, intent)` in >1 task), `in_task_build` (a heavy build/verify baked into a task's verification that phase-5/6 already runs), `verif_task_fanout` (>1 module_testing/verification task), and `deliverable_fanout` (a deliverable whose task count exceeds the per-run corpus outlier threshold `max(3, median*2)`). All five sub-checks emit `genuine`. |
| Cross-check synthesis | [`checks/cross-check-synthesis.md`](checks/cross-check-synthesis.md) | The **facet-completeness critic** (runs LAST). Joins the OTHER checks' retained structured results into six cross-check couplings single rows miss: `trend_empty_untrustworthy` (empty token-trend regression over blind-execute plans), `churn_explains_cost` (non_minimal_build/build_churn explaining token-economics finalize/big-spend cost or a metrics disproportionate_token), `qgate_gap_chain` (no_qgate6/auto_review_only correlating with ci_rerun / finalize_heavy), `argparse_signature_cluster` (recurring-pattern argparse signatures correlating with global-log errors and unfiled quality-verification signatures — collapsed to ONE candidate), `scope_underestimate_cost` (scope under-estimation correlating with high tokens/file or a task-count outlier), and `redundant_build_churn` (task-graph-redundancy `in_task_build` correlating with sequence `build_churn`/`phase_reentry`). Each coupling carries its qualifying caveat and the D1 severity column; the block operationalizes the Step-4b completeness gate. |

## Usage Examples

```bash
/audit-archived-plan-retrospectives
```

Runs every check over every archived plan and emits one TOON block per check.

```bash
/audit-archived-plan-retrospectives --plan-id 2026-05-26-fix-1-init-phase-boundary-bootstrap-bug
```

Single-plan audit across all checks; useful when a retrospective wants a focused
read-out.

```bash
/audit-archived-plan-retrospectives --check metrics
```

Runs only the metrics-anomaly check across the corpus.

```bash
/audit-archived-plan-retrospectives --include-active
```

Adds in-flight plans to the scan. In-flight plans that have not yet reached
`phase-4-plan` Step 8b show up under the `incomplete` bucket for checks that
depend on `execution.toon`.

## Workflow

### Step 0: Gather + expand the coverage cell

This skill implements the [coverage-gathering contract](../../../marketplace/bundles/plan-marshall/skills/dev-agent-behavior-rules/standards/coverage-gathering-contract.md). At invocation, gather the `(thoroughness, scope)` cell from the user via the contract's canonical `AskUserQuestion` shape — a `scope` question (`change-set`/`artifact`/`component`/`module`/`overall` + an explicit `inherit (default — behave exactly as today)`) and a `thoroughness` question (`T1`…`T5` + `inherit`). The coupling constraint (`reject thoroughness ≥ T4 ∧ scope < component`) constrains the offered scope options when the user picks `T4`/`T5`.

Validate + expand the gathered pair in one call — `coverage expand` validates the literal pair (re-prompt on `coverage_coupling_violation`; do NOT re-implement the coupling math) AND returns the operational instruction block:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config coverage expand --thoroughness {T} --scope {S}
```

This is a **single-invocation** audit skill that runs outside a plan, so hold the gathered identifier + expanded instruction **in-context** for the invocation (the in-context path of the contract's persistence mechanism — no `status.json` write). Consume the **expanded instruction** (NOT the raw cell) in Steps 1 and 4b below. When the user selects `inherit/inherit` (the default), the expanded instruction is behavior-preserving and Steps 1–4b run exactly as before (all 15 checks, full corpus, today's Step-4b gate).

See `dev-agent-behavior-rules/standards/thoroughness.md` for the ladders and `coverage-gathering-contract.md` for the gather shape and the cell→instruction table — restate neither here.

### Step 1: Select the checks to run, governed by the coverage cell

The expanded instruction's **scope rung** sets the corpus radius: `change-set`/`artifact` → a single plan (`--plan-id`); `component`/`module` → a domain/scope-filtered subset of the corpus; `overall` → the full archived-plan corpus (today's default). Its **thoroughness rung** gates check breadth: `T1` → cheap deterministic checks across a representative sample; `T2` → all 15 checks once; `T3` → all 15 plus the `cross-check-synthesis` coupling join; `T4`/`T5` → all 15 plus the Step-4b loop-until-dry / what-did-I-miss adversarial completeness pass.

When the user supplies an explicit `--check {name}`, that narrows to one check regardless of the thoroughness rung. The check names are listed in the **Available checks** table above; each maps to a `checks/{name}.md` sub-document and a `--check {name}` value the script accepts. The `inherit/inherit` expanded instruction reproduces today's behavior: all checks, the full corpus.

### Step 2: Run the audit script for the selected checks

```bash
python3 .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py [--plan-dir PATH] [--plan-id ID] [--include-active] [--check NAME]
```

The script walks `.plan/local/archived-plans/{plan_id}/` (and optionally
`.plan/local/plans/`), reads the structured inputs each check requires, computes
the per-plan and cross-plan signals, and emits one bespoke-TOON block per check.
Surface each emitted block verbatim and interpret its rows using the
corresponding `checks/{name}.md` sub-document.

### Step 3: Interpret each check's rows

The orchestrator MUST process EVERY emitted check block against its matching
`checks/{name}.md` sub-document — no block may be skipped, sampled, or
generalized from a peer. The sub-documents are the single source of truth for
what each column means and which row states warrant action; this body does not
restate them.

For EVERY row that is a potential signal — `drift`, a populated `name_drift`,
`impossible_value`, a scope mismatch, unfiled proposed lessons, a systemic
recurring pattern, a PR-velocity flag, a task-count outlier, a global-log
signal (error/non-INFO line, slow call, impossible-duration call, high-frequency
caller, or fixture leak), a token-economics anti-pattern flag
(`fixed_overhead_floor`, `planning_gt_exec`, `outline_heavy` / `refine_heavy` /
`finalize_heavy`, `big_spend_tiny_footprint`, `long_session`,
`exec_metrics_blind`), a quality-chain signal (a chain anti-pattern flag —
`build_pending_pile`, `auto_review_only`, `review_body_duplicate`, `no_qgate6` —
or a `genuine` per-finding row, especially a Tier-1 `auto-review` finding), or a
sequence-and-build-minimality flag (`build_churn`, `non_minimal_build`,
`docs_only_build`, `ci_rerun`, `phase_reentry`, `arch_over_resolution`,
`consecutive_dup` — read each against the three structural caveats in
`checks/sequence-and-build-minimality.md`), an input-integrity flag
(`metrics_blind`, `incomplete_lifecycle`, `missing_dispatch_markers`, or a
`data_confidence: blind` plan), a task-graph-redundancy flag (`multi_task_file`,
`dup_substep`, `in_task_build`, `verif_task_fanout`, `deliverable_fanout` — read
each against `checks/task-graph-redundancy.md`), or a cross-check-synthesis
coupling that FIRED (`trend_empty_untrustworthy`, `churn_explains_cost`,
`qgate_gap_chain`, `argparse_signature_cluster`, `scope_underestimate_cost`,
`redundant_build_churn` — read each against its qualifying caveat in
`checks/cross-check-synthesis.md`) —
explicitly state BOTH:

1. **the verdict** — action (file a lesson / fold into an active plan / surface
   for human review) or no-action; and
2. **the cited evidence or cross-check** that justifies the verdict — the
   specific sub-doc rule, the `severity` column value, the corpus match, or the
   structured input that grounds the decision.

A row may be dismissed as informational/expected ONLY with a cited reason (e.g.
"informational per `checks/metrics.md` § How the orchestrator interprets the
rows" or "`severity: informational` per the manifest check"). A bare "looks
fine", a silent skip, or a generalized "the rest are the same" is a contract
violation. The `execution-context-manifest` check's `severity` column and
`genuine_signal_count` summary are the precision aids for this adjudication:
`informational` rows still require a one-line cited dismissal; `genuine` rows
require a full verdict-plus-evidence treatment.

#### Standing rule: the input-integrity verdict is the no-false-healthy floor

The `input-integrity` check is the **deterministic foundation** every other
check's adjudication is built on. Process it FIRST among the per-plan reads, and
honour its verdict for the rest of the audit:

- **A check may not claim "all healthy" over blind-input plans.** Whenever the
  `input-integrity` block reports `data_confidence_blind > 0`, NO check — and no
  corpus-level summary — may conclude "all healthy" / "no findings" for the
  corpus. The blind plans' downstream rows are floors: absence of a signal there
  is absence of *recorded data*, not absence of a problem. The honest conclusion
  reads "no findings among fully-recorded plans; the N blind plans
  (`blind_plan_ids`) are floored and cannot be cleared".
- **Annotate floored rows "floor, not truth".** Any row another check derives
  from a plan `input-integrity` marks `metrics_blind` (especially a `blind`-bucket
  plan) MUST be annotated **"floor, not truth"** in the adjudication — a
  token-economics, token-trend, or metrics number computed over a blind execute
  is an under-count, not a measurement.
- **Name the blind plans when dismissing.** When dismissing a blind plan's peer
  row as "no signal", cite `input-integrity`'s `blind_plan_ids` as the reason the
  row cannot be cleared; never generalize it into a healthy verdict.

See [`checks/input-integrity.md`](checks/input-integrity.md) §
"The cross-check obligation" for the full statement of this rule.

### Step 4: File lessons through the three-gate policy

Two check classes emit candidate lesson signatures: the quality-verification
report's unfiled proposed lessons and the recurring-pattern detector's systemic
signals at the 3+ threshold. For each candidate signature, run the canonical
three-gate sequence from `plan-marshall:manage-lessons`'s
`lesson-creation-policy.md`:

1. **Gate 1 — dedup**: search the lessons corpus for an existing lesson covering
   the same signature. On `merge_into` / `already_closed`, extend the existing
   lesson instead of filing a new one.
2. **Gate 2 — active-plan check**: if an active plan already covers the fix, fold
   the signal into that plan rather than filing a lesson.
3. **Gate 3 — create**: only when Gates 1 and 2 both clear, allocate a lesson
   file via `manage-lessons add` and write the body to the returned `path`.

Any candidate signature the orchestrator is about to drop on a Gate-1 (dedup) or
Gate-2 (active-plan / "already covered") basis MUST have that basis VERIFIED
against the corpus before the signal is dropped: name the actual matching lesson
ID (Gate 1) or the active plan ID that covers it (Gate 2), and record that
verification in the adjudication. A dismissal without a named, verified
reference is a contract violation.

The quality-verification check already cross-checks each proposed lesson against
the lessons corpus and the archived-plan corpus, so a candidate it marks as
"already filed" or "covered by archived plan {id}" MUST NOT be re-filed — that
marking is itself a cited verification and satisfies the obligation above.

**Source-keyed argparse-rejection lessons**: the per-plan retrospective's
`script-failure-analysis` aspect (see `plan-marshall:plan-retrospective` aspect 8)
classifies each non-zero-exit script call by stderr signature
(`invalid choice:` → invented subcommand, `the following arguments are required:`
→ missing required flag, `unrecognized arguments:` → invented flag) and keys its
proposed lessons to the **source notation** that argparse rejected — the
`{bundle}:{skill}:{script} {subcommand}` whose surface drifted — not to the
consuming plan that happened to trip it. For archived-plan audits this changes
how the recurring-pattern detector's signals are filed: when the same source
notation surfaces across N≥3 archived plans' argparse-rejection findings, file (or,
on Gate-1 dedup, extend) a **single source-keyed lesson** naming the exact
subcommand/flag drift, rather than one lesson per consuming plan. A source-keyed
lesson already covering that notation satisfies Gate 1 for every later plan that
trips the same rejection — so the dedup check MUST search the corpus by the source
notation, not by the consuming plan ID.

**Token-economics flags are already covered by lesson `2026-06-01-12-001`**: the
`token-economics` check's anti-pattern taxonomy is derived directly from that
filed, `active` lesson (its remediation direction #5 proposed this very check). A
flagged token-economics row is therefore COVERED on a Gate-1 dedup basis — name
`2026-06-01-12-001` as the covering reference and do NOT re-file. The file-worthy
signal from this check is a corpus *drift* (e.g. the execute-share falling
further, a fresh fixed-overhead recurrence on a plan created after a remediation
shipped, or a previously-unflagged anti-pattern becoming systemic), which extends
`2026-06-01-12-001` via Gate-1 `merge_into` rather than opening a parallel lesson.
See `checks/token-economics.md` § "Adjudication against lesson 2026-06-01-12-001".

### Step 4b: Review-completeness gate

Before reaching Step 5 (Interactive dormation), the orchestrator MUST satisfy
this completeness gate. Dormation is BLOCKED until every item below is true and
demonstrable from the adjudication produced in Steps 3–4.

**Coverage-cell depth (from Step 0's expanded instruction)**: the gate's rigor is
indexed by the gathered thoroughness rung. `inherit`/`T1`/`T2`/`T3` run the gate
exactly as the checkboxes below describe (today's behavior). `T4`/`T5` add an
adversarial completeness pass on top: after the checkboxes pass once, run a
what-did-I-miss critic and a loop-until-dry sweep — re-examine the surfaced rows
asking which facet, plan, or coupling was assumed-not-examined, and repeat until a
pass surfaces no further gap. This is the contract's depth dimension applied to
the audit's completeness gate; it widens nothing the surfacer did not surface.

The `cross-check-synthesis` check is the deterministic surface that
**operationalizes this gate**: it joins the other checks' results into the six
cross-check couplings (see [`checks/cross-check-synthesis.md`](checks/cross-check-synthesis.md))
and stamps each fired coupling `severity: genuine`. A fired coupling is therefore
a genuine-signal row this gate's first checkbox accounts for, and its
`trend_empty_untrustworthy` coupling is the structural enforcement of the
blind-plan checkbox across the trend facet — a premature "no findings" conclusion
cannot pass the gate while any coupling fired unresolved.

- [ ] Every emitted check block was examined against its `checks/{name}.md`
      sub-document — none skipped or sampled.
- [ ] Every genuine-signal row (`severity: genuine`, `impossible_value`, real
      `drift`, unresolved-role `name_drift`, scope mismatch, unfiled lesson,
      systemic pattern, PR-velocity flag, task-count outlier, global-log
      error/slow/impossible/high-frequency/fixture-leak signal, token-economics
      anti-pattern flag, quality-chain anti-pattern flag, `genuine`
      quality-chain per-finding row, or sequence-and-build-minimality flag —
      `build_churn`, `non_minimal_build`, `docs_only_build`, `ci_rerun`,
      `phase_reentry`, `arch_over_resolution`, `consecutive_dup`, or an
      input-integrity flag — `metrics_blind`, `incomplete_lifecycle`,
      `missing_dispatch_markers`, a task-graph-redundancy flag —
      `multi_task_file`, `dup_substep`, `in_task_build`, `verif_task_fanout`,
      `deliverable_fanout`, or a FIRED cross-check-synthesis coupling —
      `trend_empty_untrustworthy`, `churn_explains_cost`, `qgate_gap_chain`,
      `argparse_signature_cluster`, `scope_underestimate_cost`,
      `redundant_build_churn`) was adjudicated
      with a stated verdict AND cited evidence.
- [ ] Every cross-check-synthesis coupling that `fired` (`severity: genuine`) was
      resolved by adjudicating its COUPLED rows together — not in isolation —
      against the coupling's qualifying caveat in
      `checks/cross-check-synthesis.md`; in particular,
      `trend_empty_untrustworthy` was honoured as a floor (no "no regression"
      healthy claim over blind-execute plans) and `argparse_signature_cluster`
      was collapsed to ONE source-keyed candidate.
- [ ] If `input-integrity` reported `data_confidence_blind > 0`, no check and no
      corpus summary claimed "all healthy" / "no findings" over the corpus; every
      blind plan's peer rows were annotated "floor, not truth" and the blind
      plans were named (`blind_plan_ids`) rather than cleared.
- [ ] For the quality-chain check specifically, EVERY per-finding row was walked
      step-by-step — never sampled — per `checks/quality-chain.md` §
      "Methodology constraint: walk every finding, never sample" (adjudicated
      against lesson `2026-06-01-13-001`).
- [ ] Every dismissal of a potential-signal row carries a cited justification —
      no bare "looks fine" and no silent skip.
- [ ] Every "already covered" / dedup / active-plan drop was corpus-verified with
      the matching lesson ID or covering active-plan ID named.

The gate is framed so a reviewer CANNOT truthfully reach "no findings" via a
quick look: the per-row adjudication and the named corpus verifications are the
evidence the gate checks for. If any item is unmet, return to Step 3/Step 4 and
complete the adjudication before proceeding.

### Step 5: Interactive dormation

After the audit has been reviewed, offer to dormate each reviewed plan —
relocating its directory from `.plan/local/archived-plans/{plan_id}/` to
`.plan/temp/dormated-plans/{plan_id}/`. The move is destructive, so confirmation
is mandatory:

1. For the plans the user wants to dormate, raise an `AskUserQuestion`
   confirming the move (the confirmation is owned here, in the LLM body — never
   delegated to the script).
2. Only on explicit confirmation, invoke the script's confirmed dormation move.
   The body MAY pass multiple plan IDs to a single `--dormate ... --confirmed`
   call — the batch is deduplicated silently and moved all-or-nothing (a single
   clash refuses the whole batch with nothing moved):

   ```bash
   python3 .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py --dormate {plan_id} [{plan_id} ...] --confirmed
   ```

   To relocate the entire reviewed corpus in one call, use `--dormate-all`. The
   body MUST surface the full would-move plan list in the `AskUserQuestion`
   before confirming, so the user sees exactly which plans the whole-corpus move
   relocates:

   ```bash
   python3 .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py --dormate-all --confirmed
   ```

   Without `--confirmed`, the script's move function is inert and refuses to
   relocate anything.

After offering per-plan dormation, also offer to dormate the COMPLETE past-date
global logs — relocating each `{prefix}-YYYY-MM-DD.log` from `.plan/local/logs/`
to `.plan/temp/dormated-plans/global-logs/`. This move is destructive in the same
way, so confirmation is mandatory and owned here:

3. Determine the complete date-files that would move. Today's still-active log
   (the `{prefix}-YYYY-MM-DD.log` whose date equals today) is NEVER moved, so it
   MUST be excluded from the set surfaced to the user. Raise an `AskUserQuestion`
   that lists exactly the past-date `{prefix}-YYYY-MM-DD.log` files (today's
   active log excluded) and confirms the move (the confirmation is owned here, in
   the LLM body — never delegated to the script).
4. Only on explicit confirmation, invoke the script's confirmed global-log
   dormation move:

   ```bash
   python3 .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py --dormate-global-logs --confirmed
   ```

   The script re-applies the same past-date-only / never-move-today's-active-log
   rule, refuses on any destination-name clash (`status: error`), and emits a
   `moved[N]{date_file}` TOON listing the relocated date files. Without
   `--confirmed`, the move function is inert and refuses to relocate anything.

## Critical Rules

- The script is the single source of truth for every check's computed rows. Do
  not paraphrase or re-implement any check in chat.
- `execution.toon`, `metrics.toon`, and the other structured inputs are parsed
  by small inline readers inside `scripts/audit.py` (the project's
  `toon_parser` lives behind the executor PYTHONPATH which this skill does not
  load). If a manifest or metrics schema changes, update the reader in
  `scripts/audit.py` rather than calling out to a `manage-*` script — that would
  be a dispatch-shaped solution for deterministic work.
- The audit is **read-only** against all plan artifacts except the
  explicitly-confirmed dormation move.
- Lesson filing always passes through the three-gate policy — never file
  directly from a surfaced signal.

## Related

- `plan-marshall:manage-execution-manifest` — the composer audited by the
  execution-context-manifest check.
- `plan-marshall:manage-lessons` — the lessons corpus and the three-gate
  `lesson-creation-policy.md` that Step 4 follows.
- `plan-marshall:plan-retrospective` — consumes `execution.toon`, `metrics.toon`,
  and the compose decision-log lines; audit failures here predict stale
  retrospective signals.
- `extension-api/standards/dispatch-granularity.md` — the heuristic basis for
  keeping this skill script-shaped rather than dispatch-shaped.
