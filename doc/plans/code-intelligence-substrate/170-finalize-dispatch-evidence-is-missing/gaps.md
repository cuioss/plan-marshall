# Gaps — 170-finalize-dispatch-evidence-is-missing

The plan landed: a deterministic, testable, fail-able dispatch audit exists
(`check-dispatch-audit.py`), it is registered as aspect 11, and its `not_evaluated` guard is proven
load-bearing by mutation. Fifteen gaps remain.

The one that matters most is **G13**: D2's whole mechanism rests on a token record whose two branches
are not distinguishable. `dispatched` requires a positive integer; **everything else** — an explicit
measured zero, a dispatched step whose `<usage>` tag never arrived, a row with no `total_tokens`
column at all — falls through to `ran_inline`, which the detector's docstring and the shipped
standard both describe as *proof* that the step ran inline. The producer says the opposite in so many
words (`manage-execution-manifest.py:2613-2614`: *"a step dispatched without a `<usage>` tag reports
zeros rather than a missing column"*). Because `dispatched` under-counts, `missing_dispatch_emission`
— D2's own headline finding — cannot fire for exactly the steps whose instrumentation failed, and
D3's shortfall branch is suppressed with it.

Next are the two D3 defects. `channel_completeness`'s numerator counts `[DISPATCH]` lines from
**every** caller while both its denominators are **finalize-only**, so a plan with an entirely empty
finalize dispatch channel is graded `confidence: nominal` — the exact reading D3 was built to
prevent (G1); and the same block has no "did not evaluate" state, so a plan with no logs at all is
also graded `nominal`, contradicting the module's own docstring (G2). Beyond those: the aggregate
`counts` block publishes four bare zeros and so re-introduces the exact ambiguity D1 exists to kill —
including in the *same output* where the nested block correctly says `not_evaluated` (G3); D4's
`N == 0` case is silent because the floor it defers to provably cannot fire (G7); one production
branch has no test at all (G6, proved by mutation); and the run left two plan-mandated cross-notes
unwritten plus two stale doc claims (G11, G12, G14).

## G1 — Scope `channel_completeness`'s dispatch-line count to the finalize caller

- **Kind:** bug
- **Severity:** high
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py:535-537`
  (`cmd_run`, the `evaluate_channel_completeness(len(dispatch_lines), …)` call) and `:416-451`
  (`evaluate_channel_completeness`)
- **Evidence:** `cmd_run` already computes the correctly-scoped count at `:522-524`
  (`finalize_dispatch_line_count = sum(1 for record in dispatch_lines if record['caller'] ==
  FINALIZE_DISPATCH_CALLER)`) and hands it to `evaluate_dispatch_coverage` — but hands
  `len(dispatch_lines)`, the **all-caller** total, to `evaluate_channel_completeness`. The other two
  figures are finalize-only: `completion_count` (`:521`) counts `[STEP] … Completed step:` lines,
  whose emitter is phase-scoped (`manage-status/scripts/_cmd_mark_step.py:195-198` — *"Scoped to the
  finalize phase … a phase-5 `mark-step-done` writes no such line"*), and `dispatched_step_count` is
  `coverage['dispatched']`, computed only over `status.metadata.phase_steps["6-finalize"]`.
  Reproduced against a fixture with 6 phase-5 `[DISPATCH]` lines, 3 finalize completions, 3
  token-proven dispatched finalize steps and **zero** finalize `[DISPATCH]` lines:

  ```
  dispatch_coverage:   dispatched: 3   missing_dispatch_emission: 3
  channel_completeness: dispatch_line_count: 6  completion_count: 3
                        dispatched_step_count: 3  ratio: 2.0  confidence: nominal
  ```

- **Why it matters:** the audit reports three missing dispatch emissions *and* declares nominal
  confidence in its own dispatch-discipline verdicts, in the same output. Since #1232 every phase-5
  task dispatch emits a `[DISPATCH]` line, so a real plan always carries a large phase-5 numerator —
  the ratio is inflated on every plan and the `dispatch_line_count < dispatched_step_count` shortfall
  branch is masked whenever phase-5 dispatches outnumber finalize dispatched steps. D3's entire
  purpose ("a sparse channel downgrades the audit's confidence") fails on the population it covers.
- **Action:** pass `finalize_dispatch_line_count` to `evaluate_channel_completeness` instead of
  `len(dispatch_lines)`. Publish both figures in the block (`dispatch_line_count` scoped to finalize,
  plus a separate `all_caller_dispatch_line_count`) so the scoping is legible rather than implicit,
  and state the scope in `standards/execution-context-dispatch-audit.md:9` and its § "Output TOON
  Schema" comment at `:98-101`.
- **Done when:** a test fixture carrying N phase-5 `[DISPATCH]` lines, zero finalize `[DISPATCH]`
  lines, and ≥1 token-proven dispatched finalize step reports `confidence: none` (not `nominal`), and
  the existing three confidence tests still pass.
- **Effort:** S
- **Risk if fixed:** any consumer keying on today's inflated `ratio` sees it drop; the shipped
  interpretation rules do not pin a numeric ratio, so the exposure is limited to unreleased tooling.

## G2 — Give `channel_completeness` a `not_evaluated` state

- **Kind:** bug
- **Severity:** high
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py:436-451`
  (`evaluate_channel_completeness`); test pinning the wrong behaviour at
  `test/plan-marshall/plan-retrospective/test_check_dispatch_audit.py:396`
- **Evidence:** running the shipped script against a plan directory containing only an empty `logs/`
  (no `work.log`, no `decision.log`, no `execution.toon`, no `status.json`) yields
  `dispatch_line_count: 0, completion_count: 0, dispatched_step_count: 0, ratio: null,
  confidence: nominal`. The module docstring at `:58-59` promises the opposite: *"all read
  defensively; a missing input degrades the affected block to `not_evaluated` / `no_evidence` with a
  reason, never a false clean."* `test_absent_inputs_degrade_cleanly` asserts
  `data['channel_completeness']['confidence'] == 'nominal'`, so the defect is pinned as correct.
- **Why it matters:** this is the plan's own headline archetype ("a check that can return zero from
  an empty population") surviving at the D3 site. `confidence: nominal` is the audit's statement that
  its dispatch-discipline verdicts can be trusted; emitting it when the audit read nothing is a
  false clean, and the LLM interpretation rule at
  `standards/execution-context-dispatch-audit.md:118` only tells the reader to act on `none` / `low`
   — so a `nominal` over an empty channel passes through the report unremarked.
- **Action:** add a fourth grade — `confidence: not_evaluated` with a `reason` — for the case
  `dispatch_line_count == 0 and completion_count == 0 and dispatched_step_count == 0`. Update
  `test_absent_inputs_degrade_cleanly` to assert the new value, extend the schema block at
  `standards/execution-context-dispatch-audit.md:97-102`, and add the new grade to the interpretation
  rule at `:118`.
- **Done when:** the log-less fixture reports `confidence: not_evaluated` carrying a reason, and no
  input combination that evaluated nothing can report `nominal`.
- **Effort:** S
- **Risk if fixed:** any consumer branching on the three-value `confidence` enum must learn a fourth
  value; the only in-tree consumer is the LLM interpretation rule, which is prose.

## G3 — Publish the population beside `counts.by_category.shape_violation`

- **Kind:** bug
- **Severity:** high
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py:542-550`
  (the `counts` block in `cmd_run`)
- **Evidence:** on the log-less fixture the output carries `shape_violation: {status: not_evaluated,
  evaluated_population: 0, …}` correctly, and simultaneously
  `counts: {total: 0, by_category: {shape_violation: 0, …}}`. `counts.by_category.shape_violation`
  is `shape['violations']`, which is `0` in *both* the never-evaluated and the evaluated-clean case,
  with nothing beside it. `test_check_dispatch_audit.py:124` asserts exactly this bare `0` for the
  not-evaluated case. Re-derived at adversarial-review time by running the shipped script against a
  plan directory holding only an empty `logs/`.
- **Why it matters:** this violates D1's *Done when* verbatim — *"never a bare `0`"* — and `plan.md`'s
  ⭐ rule (*"Every check that can return zero from an empty population MUST publish the
  evaluated-population size next to the count"*), in the one block a summarising consumer reads
  first. The plan's own § Verification states the acceptance test: *"Hand the audit output to the
  pre-PR verification sub-agent cold and ask, for each zero, whether the check evaluated anything.
  If it cannot tell, D1 has not been met."* A reader given only `counts` cannot tell.
  **The in-tree consumer makes this worse rather than catching it.** `compile-report.py`'s
  `_names_checked_set` (`:213-250`) is the ambiguity probe for exactly this failure — and `counts` is
  a member of `ZERO_ATTRIBUTION_FIELDS` (`retro_sections.py:148-154`), so a non-empty `counts` dict
  *by itself* satisfies the probe. The log-less fragment therefore passes the "this fragment names
  what it checked" test on the strength of the very block that names nothing.
- **Action:** either omit `shape_violation` from `counts.by_category` when
  `shape['status'] == 'not_evaluated'`, or emit it as a structured value carrying its population
  (e.g. `shape_violation: {count: 0, evaluated_population: 0, status: not_evaluated}`). Mirror the
  choice in `standards/execution-context-dispatch-audit.md:105-111`.
- **Done when:** no consumer can read `counts.by_category` alone and mistake a `not_evaluated`
  shape check for an evaluated-clean one; a test asserts the distinguishing field; and
  `test_check_dispatch_audit.py:124`'s assertion of the bare `0` is replaced by an assertion of the
  new shape.
- **Effort:** S
- **Risk if fixed:** `compile-report`'s `_names_checked_set` (`compile-report.py:213-250`) reads
  `counts` as an attribution field; a shape change there must keep that probe working — and the
  probe should be tightened in the same change, since today it is satisfied by any non-empty
  `counts` dict regardless of what the counts attribute to.

## G4 — Publish an evaluated population for `envelope_violation` and `generic_subagent_violation`

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py:454-472`
  (`evaluate_envelope_violations`) and `:475-490` (`evaluate_generic_subagent`)
- **Evidence:** both return a bare `list[dict]`; `cmd_run:542-550` publishes only their lengths.
  On the log-less fixture the output reads `envelope_violation: 0` and
  `generic_subagent_violation: 0` with no statement anywhere of how many `[DISPATCH]` lines were
  inspected for the first or how many work-log lines were scanned for the second. Nothing in the
  output distinguishes "scanned 400 log lines, found no generic subagent" from "work.log was absent".
- **Why it matters:** `generic_subagent_violation` is described in the shipped standard
  (`standards/execution-context-dispatch-audit.md:120`) as *"the highest-priority remediation
  target"*. A zero on the highest-priority hard-rule check that cannot be distinguished from an
  unread log is precisely the trained-to-discount-the-category failure `plan.md` warns about. These
  two checks were converted to deterministic code **by this run**, so the plan's ⛔
  "publish the evaluated-population size beside every count" applies to them.
- **Why it is separate from G3:** G3 is about a count whose population *is* published one level down;
  here the population is published nowhere in the output at all.
- **Action:** return `{evaluated_population: N, violations: M, findings: [...]}` from both
  functions — `N = len(dispatches)` for the envelope check, `N = len(work_lines)` for the generic
  check — and surface both blocks in the payload alongside `shape_violation` / `dispatch_coverage`.
  Extend the schema in `standards/execution-context-dispatch-audit.md:77-112`.
- **Done when:** a run against a plan with no `work.log` and a run against a populated clean
  `work.log` produce visibly different output for both checks.
- **Effort:** S
- **Risk if fixed:** fragment schema grows two keys; `compile-report` renders unknown keys generically,
  so the blast radius is the aspect's own section.

## G5 — Give `dispatch_coverage` an explicit not-evaluated status

- **Kind:** incomplete
- **Severity:** low
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py:405-413`
  (`evaluate_dispatch_coverage` return) and `:195-205` (`load_status_metadata`)
- **Evidence:** `load_status_metadata` swallows a missing file, an `OSError` and a
  `json.JSONDecodeError` into `{}`, so `finalize_terminal_steps` returns `[]` and the coverage block
  reports `evaluated_population: 0, dispatched: 0, ran_inline: 0, no_evidence: 0,
  missing_dispatch_emission: 0` with no `status` and no `reason` — indistinguishable from a plan that
  genuinely completed zero finalize steps, and from a plan whose `status.json` is corrupt.
- **Why it matters:** the population *is* published, so this is milder than G2 — but the sibling
  block in the same script models the correct shape (`status` + `reason`) and this one does not,
  which makes the inconsistency itself a trap for the next reader.
- **Action:** return `status: 'not_evaluated'` with a reason naming which surface was missing
  (status.json absent / unparseable / `phase_steps["6-finalize"]` absent) when `terminal_steps` is
  empty, matching `evaluate_shape_violation`'s shape.
- **Done when:** a fixture with an absent `status.json` and a fixture with a valid `status.json`
  carrying an empty `6-finalize` map are distinguishable in the output, each with a test.
- **Effort:** S
- **Risk if fixed:** none identified; the field is additive.

## G6 — Test the `ratio < _SPARSE_RATIO` confidence branch

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** production branch at
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py:441`
  (`elif ratio is not None and ratio < _SPARSE_RATIO and completion_count > 0:`) and the constant at
  `:132`; test file `test/plan-marshall/plan-retrospective/test_check_dispatch_audit.py`
- **Evidence:** mutation. Replacing `:441` with `elif False and ratio is not None and ratio <
  _SPARSE_RATIO and completion_count > 0:` and running
  `uv run python -m pytest test/plan-marshall/plan-retrospective/test_check_dispatch_audit.py -o addopts=""`
  gave **`13 passed`** (twice: `13 passed in 7.83s`, `13 passed in 3.79s`). The three confidence
  tests reach `none` via the `dispatch_line_count == 0` branch (`:271`), `low` via the
  `dispatch_line_count < dispatched_step_count` branch (`:320`, ratio exactly `0.5` — *not* below the
  threshold), and `nominal` via the fall-through (`:296`). Nothing exercises the ratio branch or the
  `_SPARSE_RATIO` constant.
- **Why it matters:** D5 required tests "each verified to FAIL pre-fix"; an entire grading path
  shipped with no guard, so the threshold could be deleted or inverted silently. It is also the one
  branch G1's fix will change the behaviour of, so it must be pinned before that fix lands.
- **Action:** add a test with a sparse-but-nonzero channel — e.g. 1 finalize `[DISPATCH]` line, 4
  `[STEP] Completed` lines, and **no** token-proven dispatched step (so the shortfall branch cannot
  fire) — asserting `ratio == 0.25` and `confidence == 'low'`. Add the boundary case at
  `ratio == 0.5` asserting `nominal`, so the strict `<` is pinned.
- **Done when:** mutating `:441` to `elif False and …`, or changing `_SPARSE_RATIO` from `0.5`, turns
  at least one test red.
- **Effort:** S
- **Risk if fixed:** none; test-only.

## G7 — Make the total per-task ARTIFACT emission failure (`N == 0`) reportable

- **Kind:** bug
- **Severity:** high
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:1559-1571`
  (the comment's `N == 0` deferral and the `0 < N < M` guard), against the floor it defers to at
  `:1551` and the count it uses at `:1519`
- **Evidence:** the comment at `:1566-1567` reads *"`N == 0` is left to the plan-level floor and the
  published population (a plan may simply not use per-task emission)"*. The floor is
  `elif footprint and artifact_entries == 0`, and `artifact_entries = tag_counter.get('ARTIFACT', 0)`
  (`:1519`) counts `[ARTIFACT]` lines from **every** caller. `phase-1-init/SKILL.md:454` and `:1027`
  emit `[ARTIFACT]` unconditionally on every plan, so `artifact_entries >= 2` always and the floor
  cannot fire. Proved with a probe run (temporary test, since removed): 3 completed tasks, 0 per-task
  `[ARTIFACT]` lines, 2 phase-1 `[ARTIFACT]` lines →
  `artifact_emission: {completed_tasks: 3, tasks_with_artifacts: 0, tasks_without_artifacts:
  ['TASK-001','TASK-002','TASK-003']}`, `artifact_entries: 2`, and **zero findings**.
- **Why it matters:** `N == 0, M > 0` is the *worst* instance of the defect D4 exists for — per-task
  emission entirely bypassed — and it is the only instance that raises nothing. Severity is **high**
  under the "a guard cannot fire" clause: the plan-level floor the comment defers to is not merely
  unlikely to fire, it is provably dead for any plan that ran `phase-1-init`. The published
  population still makes the state readable, so this is not a silent-wrong-number defect; it is the
  vacuous-guard archetype `plan.md` names, surviving inside a fix for it.
- **Independently re-derived** at adversarial-review time against a pristine copy of
  `analyze-logs.py` (`git show HEAD:…`, so a concurrent agent's in-tree mutation could not influence
  the reading), archived mode, `references.modified_files` supplying a non-empty footprint so the
  floor's own precondition was satisfied: `completed_tasks: 3`, `tasks_with_artifacts: 0`,
  `tasks_without_artifacts: [TASK-001, TASK-002, TASK-003]`, `artifact_entries: 2`, `findings[0]:`
  — zero findings, matching the original probe exactly.
- **Action:** either (a) widen the partiality guard to `N < M` and give the `N == 0` case its own
  message distinguishing "this plan uses no per-task emission" from "emission was bypassed" — the
  discriminator is whether the plan's footprint is non-empty, already resolved at `:1532`; or (b)
  scope the plan-level floor to per-task artifacts (`_ARTIFACT_TASK_RE` at `:757-759`) so the
  deferral the comment claims actually exists. Correct the comment either way.
- **Done when:** a fixture with M ≥ 1 completed tasks, zero per-task `[ARTIFACT]` lines, a non-empty
  footprint and at least one non-task `[ARTIFACT]` line produces a finding, and a plan that
  legitimately has no completed tasks does not.
- **Effort:** S
- **Risk if fixed:** archived plans predating per-task emission would start reporting the new
  finding; scope the guard on the footprint (option a) or restrict it to plans whose work log shows
  the phase-5 task loop ran.

## G8 — Pair `missing_dispatch_emission` per step rather than by count

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py:388`
  (`missing = max(0, len(dispatched) - finalize_dispatch_line_count)`) and the finding message at
  `:393-403`
- **Evidence:** the shortfall is a scalar subtraction over two counts. `phase-6-finalize/SKILL.md:629`
  states *"Every firing re-resolves, so every firing re-emits"*, so a step that re-fires contributes
  multiple `[DISPATCH]` lines but one `dispatched` entry. Five dispatched steps with one re-firing
  three times yields 7 lines vs 5 dispatched → `missing = 0`, masking a sixth step that dispatched
  with no line. The emitted message names counts only — no step id — so even when it fires the
  consumer cannot locate the offending dispatch. The code documents the direction of the error at
  `:373-375` ("a floor"), so this is a known limitation, not a surprise.
- **Why it matters:** D2's stated outcome is *"a step with envelope evidence but no dispatch line is
  reported as `missing_dispatch_emission`"* — a per-step statement. The shipped detector reports an
  aggregate that both under-counts under re-fires and cannot name the step, so a consumer acting on
  the finding has nowhere to look.
- **Action:** the `[DISPATCH]` line carries `role=`, not `step_id`, so exact per-step pairing needs
  either the step id in the dispatch line (an emission change, out of this plan's lane) or a
  role→step map. Interim: deduplicate the finalize `[DISPATCH]` lines by `(role, target, level)`
  before the comparison so re-fires stop inflating the numerator, and list the `dispatched` step ids
  in the block (alongside the existing `no_evidence_steps`) so the finding's population is nameable.
- **Done when:** a fixture with 2 dispatched steps, 3 finalize `[DISPATCH]` lines all carrying the
  same role, and one step lacking any line reports `missing_dispatch_emission >= 1`, and the coverage
  block lists the dispatched step ids.
- **Effort:** M
- **Risk if fixed:** de-duplication could hide a genuine multi-step same-role case; pair on
  `(role, workflow)` rather than role alone to keep distinct steps distinct.

## G9 — Correct the stale reviewer-registry line citations in the run report

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/170-finalize-dispatch-evidence-is-missing/report-01.md:201-202`
- **Evidence:** the report cites *"`coderabbitai` (coderabbit.md:27), `cuioss-review-bot`
  (pr-agent.md:55), `sourcery-ai` (sourcery.md:25)"*. At HEAD the `author_login` keys sit at
  `automatic-review/standards/coderabbit.md:36`, `pr-agent.md:58` and `sourcery.md:29`. The three
  login values and the derived `M = 3` are correct.
- **Why it matters:** the citations are the report's evidence for the reviewer-population derivation;
  a reader following them lands on the wrong line. Confined to the run report, which is a dated
  record, so the cost is a wasted lookup rather than a wrong decision.
- **Action:** re-anchor the three citations to the `author_login` keys, or drop the line numbers and
  cite the files plus the key name (which does not drift).
- **Done when:** every line citation in `report-01.md` § "Reviewer participation" resolves to the
  claimed content at HEAD, or carries no line number.
- **Effort:** S
- **Risk if fixed:** none.

## G10 — Cross-reference the corroboration limit from the `shape_violation` interpretation rule

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/standards/execution-context-dispatch-audit.md:122`
  (the LLM interpretation rule for `shape_violation`), against the corroboration-limit paragraph at
  `:40` and the emitter at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py:503-518`
- **Evidence:** `_emit_dispatch_records` writes the Surface B decision-log record and the Surface A
  `[DISPATCH]` line back to back in one call, with the same `role_display` value, both best-effort.
  Since #1232 finalize passes `--workflow` (`phase-6-finalize/SKILL.md:618`), so Surface B is now
  populated for finalize and `shape_violation` reports `evaluated` with a real population. But the
  pairing can only diverge if `log_entry('work', …)` fails while `log_entry('decision', …)` succeeds.
  The interpretation rule at `:122` nonetheless reads: *"`shape_violation` findings indicate a
  resolve that never emitted its canonical `[DISPATCH]` line — usually a missing instrumentation
  step."*
- **Why it matters, and how far this actually goes.** The plan was written to abolish a check whose
  `0` means nothing. D1 replaced a never-evaluated `0` with an honest `not_evaluated` — correct at
  the time — but at HEAD the check reports `evaluated, violations: 0` over a populated population,
  which reads as a strong clean verdict for a check that is structurally almost unable to fail.
  **The substantive warning is nevertheless already shipped**, in a prominent blockquote at `:40`:
  *"BOTH Surface A … and Surface B … are written by the SAME call … Their agreement proves only that
  the seam ran; it does NOT prove that a dispatch actually rode the canonical envelope or completed
  … pairing Surface A against Surface B is a **consistency** check on the emitter's own output,
  never a **completeness** check."* That is the disclosure this gap once claimed was missing, so the
  gap reduces to a navigation defect: the reader who acts on the count reads `:122`, four sections
  away from `:40`, and `:122` carries no pointer back. Severity is **low** accordingly — a reader who
  reads the whole standard is correctly informed today.
- **Action:** extend the `:122` interpretation rule to state that both surfaces are emitted from one
  call (`_cmd_effort.py::_emit_dispatch_records`), so a `shape_violation: 0` over a populated
  population confirms only that the seam's two writes agree — a partial-logging-failure detector, not
  a dispatch-discipline detector. Add an explicit cross-reference to the corroboration-limit
  blockquote at `:40` in the same rule.
- **Done when:** the interpretation rule at `:122` names `_cmd_effort.py::_emit_dispatch_records` as
  the single writer of both surfaces and links the `:40` blockquote, so a reader who lands on `:122`
  alone cannot conclude from a clean `shape_violation` that dispatch discipline was verified.
- **Effort:** S
- **Risk if fixed:** documentation only; no behaviour change.

## G11 — Record the two defects the plan told the run to cross-note

- **Kind:** omission
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/170-finalize-dispatch-evidence-is-missing/report-01.md`
  § "Residue" (`:272-284`), against `plan.md:113-118` § "Out of scope". (Topic is
  `documentation-surface`, not `plan-lane-contract`: the fix edits `report-01.md`, the same file G9
  edits, and asks for no change to the lane contract.)
- **Evidence:** `plan.md` excludes the execute-phase re-entry-marker defect with the instruction
  *"Record it rather than absorbing it"*, and the aspect-naming defect as *"a different surface,
  cross-noted only"*. `report-01.md` mentions neither — the Residue section lists only the
  `--workflow` migration, the ARTIFACT-emission limitation and the three relabelled docs, and the
  Findings section covers only the sub-agent's four items.
- **Why it matters:** both defects were identified during authoring and deliberately deferred. With
  no written trace in the only artefact that survives the run, the deferral becomes a loss: a later
  plan has to rediscover them. The instruction was explicit and unambiguous.
- **Action:** append a "Cross-noted, not owned" subsection to `report-01.md` § Residue restating both
  defects in enough detail for a later plan to pick them up: (a) the execute-phase re-entry marker —
  a first entry logging a re-entry marker, and a coverage rule whose precondition is satisfied by the
  *presence* of a line rather than by the line being *correct*; (b) the aspect-naming defect — one
  aspect known by three names, with the documented label rejected by the registry (see
  `plan-retrospective/SKILL.md:178`, which names `invariant-summary`, `manifest-decisions` and
  `routing-decisions` as the rows whose key differs from their reference basename).
- **Done when:** both excluded defects are recoverable from `report-01.md` alone, without re-reading
  `plan.md`.
- **Effort:** S
- **Risk if fixed:** none; report text only.

## G12 — Relabel the fourth "LLM aspects" site the run missed

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md:30`
- **Evidence:** the line reads *"`plan-marshall:plan-retrospective` — opt-in … its **LLM aspects**
  iterate inside one envelope."* This run relabelled exactly this phrase at three other sites
  (`plan-marshall/standards/effort-roles.md:65`, `ref-workflow-architecture/standards/call-graph.md:323`
  and `:462`) because after aspect 11 became a script the label is imprecise. `report-01.md:284`
  closes the item with *"No further known stale sites"* — false. A repo-wide grep for `LLM aspects`
  returns this site plus `plan-retrospective/SKILL.md:240` and `:251`, and those two are correct
  (they name the genuinely-LLM aspects 4-7, 9, 14).
- **Why it matters:** small, but it is the same misleading-signal defect the run's beyond-diff sweep
  was run to catch, and the report asserts the sweep was exhaustive when it was not — so a later
  reader trusts a claim that does not hold.
- **Action:** change "its LLM aspects" to "its analytical aspects" at `dispatch-inline-split.md:30`,
  matching the wording used at the three fixed sites.
- **Done when:** a repo-wide grep for `LLM aspects` outside `doc/plans/` returns only sites that
  genuinely enumerate LLM-only aspects.
- **Effort:** S
- **Risk if fixed:** none.

## G13 — `ran_inline` is a fall-through default, not a measurement: the D2 discriminator's two branches are not distinguishable

- **Kind:** bug
- **Severity:** high
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py:380-386`
  (the three-state classifier), `:271-281` (the token coercion that manufactures the "measured zero"),
  and the premise stated in the module docstring at `:31-46`; mirrored in the shipped standard at
  `plan-retrospective/standards/execution-context-dispatch-audit.md:62` and in
  `plan-retrospective/SKILL.md:198`
- **Evidence:** the classifier is
  `if step not in tokens_by_step: no_evidence / elif tokens_by_step[step] > 0: dispatched / else:
  ran_inline`. Only the *first* branch is a positive measurement. `ran_inline` is everything else,
  and three materially different inputs land in it:

  1. **A genuine inline step** — a real measured `0`. This is the only case the docstring describes.
  2. **A dispatched step whose `<usage>` tag never arrived** — the producer states this outcome in so
     many words: `manage-execution-manifest.py:2611-2614` — *"Token-attribution fields
     (`total_tokens` / `tool_uses` / `duration_ms`) default to `0` when the caller omits them — a
     skipped step legitimately consumes no tokens, and a step dispatched without a `<usage>` tag
     reports zeros rather than a missing column."* The write is `max(0, int(args.total_tokens or 0))`
     (`:2650`), so an omitted flag is indistinguishable from a measured zero on disk. The same file
     says it again for its own consumer at `:2799-2803`: *"`record-step` receives the `<usage>`
     triple only for steps dispatched as Task agents; every inline step records a row with zeros by
     contract. So `total_tokens` is a FLOOR."* `phase-6-finalize/SKILL.md:1081` names the skip
     conditions on the producing side (`5b`): *"Inline steps and timed-out steps skip this call."*
  3. **A row with no `total_tokens` column at all, or a non-numeric one** — the detector's own
     `else: value = 0` fail-open coercion (`check-dispatch-audit.py:278-279`) converts "not measured"
     into "measured zero" before the classifier ever sees it.

  Reproduced against the shipped script (`--mode live`, hand-built plan fixtures). A terminal step
  with `execution_log` row `{outcome: error, total_tokens: 0}` and no `[DISPATCH]` line:
  `dispatched: 0, ran_inline: 1, missing_dispatch_emission: 0`. The same fixture with the
  `total_tokens` column **absent entirely**: identical output — `ran_inline: 1`, not `no_evidence`.
- **Why it matters:** `ran_inline` is not a neutral bucket — the code presents it as *proof*.
  `evaluate_dispatch_coverage`'s own docstring at `:366-369`: *"The token record is the second,
  independent evidence source the coverage check consults before ever concluding 'ran inline': a
  non-zero `total_tokens` proves a dispatched envelope ran, a measured `0` proves the step ran
  inline, and an absent row is honest `no_evidence`."* The shipped standard repeats the contrast at
  `:62`: `ran_inline` is *"a measured zero"* while `no_evidence` is *"no token row at all — reported
  honestly, never as 'ran inline'"*. Both rest on a field that may never have been written, and the
  detector's own coercion is what converts "never written" into "measured". Two consequences follow mechanically:
  - `missing_dispatch_emission` — **D2's own headline finding** — is computed as
    `max(0, len(dispatched) - finalize_dispatch_line_count)` (`:388`). A dispatched step that lands
    in `ran_inline` is subtracted from the numerator, so the finding cannot fire for exactly the
    class of step whose instrumentation failed. That is the same failure mode the plan set out to
    abolish, relocated one surface upstream.
  - `dispatched_step_count` feeds D3, so the `low`-confidence shortfall branch (`:439`) is suppressed
    by the same under-count.

  This also revises the audit's acceptance of the D2 **mechanism deviation**. The run substituted the
  token record for `plan.md`'s literal *roster qualifier* and `verification.md` accepted it as
  "outcome-equivalent for the two cases the plan enumerates". It is equivalent for the conditional-
  inline case; it is *not* equivalent for the dispatched-but-unmeasured case, where a roster
  qualifier ("this row dispatches") would still have classified the step as dispatching and surfaced
  the missing emission. The deviation therefore traded one blind spot for another, and the trade was
  never stated.
- **Action:**
  1. Make `finalize_token_records` distinguish *unmeasured* from *measured zero*: return
     `dict[str, int | None]`, mapping an absent / non-integer / non-digit-string `total_tokens` to
     `None` instead of `0` (replacing the `else: value = 0` fall-through at `:278-279`), and route a
     `None` to `no_evidence` in `evaluate_dispatch_coverage`.
  2. Re-document the surviving `ran_inline` bucket in the module docstring (`:36-44`), the standard
     (`:62`) and `SKILL.md:198` as *"a recorded zero token attribution — an inline step, or a
     dispatched step whose `<usage>` tag was not captured"*, i.e. an upper bound on inline execution,
     never proof of it.
  3. Extend the `missing_dispatch_emission` floor note (`:373-375`) to name this second reason the
     count under-reports, alongside the re-fire reason G8 covers.
- **Done when:** a fixture whose `execution_log` row carries no `total_tokens` column is classified
  `no_evidence` (not `ran_inline`), a fixture with an explicit `total_tokens: 0` is still classified
  `ran_inline`, both are pinned by tests, and mutating the coercion default at `:278-279` turns at
  least one test red.
- **Effort:** M
- **Risk if fixed:** `no_evidence` grows on plans with legacy or hand-edited `execution.toon` rows,
  and `no_evidence_steps[]` gets noisier; keeping an explicit integer `0` in `ran_inline` (step 1
  above) bounds that to rows that genuinely never recorded the column. The `dispatched` count is
  unchanged by this fix — it already required a positive integer — so no currently-clean plan starts
  reporting `missing_dispatch_emission` because of it.

## G14 — Re-derive or drop the "eight aspects" count in the three relabelled docs

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-roles.md:65`,
  `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/call-graph.md:323`
  and `:462`
- **Evidence:** all three now read *"eight analytical aspects"* / *"8 analytical aspects"*. The run
  changed only the adjective and `report-01.md:150-155` records the change as *"Relabelled to
  'analytical aspects' (count unchanged)"* — the count was carried over, not re-derived. It does not
  hold: `plan-retrospective/SKILL.md:180-196` lists **15** aspects (orders 1-15), and the SKILL's own
  LLM enumeration at `:251` names **six** (*"LLM aspects (4-7, 9, and 14)"*). `git log -L 65,65` on
  `effort-roles.md` shows "eight" arrived with `59b716d` (#1035) and has never been re-derived since,
  so this is a pre-existing staleness that plan 170 inherited rather than introduced — but it edited
  all three lines and asserted the count still held.
- **Why it matters:** the relabel was performed precisely to stop a doc asserting something the code
  no longer supports. Leaving a wrong count in the same sentence keeps the misleading-signal defect
  alive under a new adjective, and `report-01.md` records the count as verified when it was only
  preserved.
- **Action:** replace "eight" / "8" with the count derived from the aspect table in
  `plan-retrospective/SKILL.md` (the registry `retro_sections.py::SECTION_SPEC` is the source of
  truth the table restates), or drop the number entirely and read "the retrospective's analytical
  aspects", which cannot drift.
- **Done when:** no doc outside `doc/plans/` states an aspect count that disagrees with the
  `plan-retrospective` aspect table, checked by grepping the three cited lines and comparing against
  the table's row count.
- **Effort:** S
- **Risk if fixed:** none; a dropped number cannot go stale again.

## G15 — `shape_violation` pairs by per-role count, and a hand-written `[DISPATCH]` line from any caller cancels a real shortfall

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py:333-350`
  (`evaluate_shape_violation`'s `Counter`-vs-`Counter` comparison), against the Surface B record shape
  at `manage-config/scripts/_cmd_effort.py:504-510`
- **Evidence:** the pairing is
  `unmatched = resolve_roles[role] - dispatch_roles.get(role, 0)`, and only a **positive** `unmatched`
  produces a finding. `dispatch_roles` is built from every `[DISPATCH]` line in the work log
  regardless of caller, while Surface B's decision-log record carries **no caller at all** — the seam
  writes `(plan-marshall:manage-config) effort resolve-target role=X -> target=Y level=Z`
  (`_cmd_effort.py:504-510`), so the caller a resolve was made on behalf of is not recoverable from
  Surface B and the pairing is caller-blind by construction.

  This is live at HEAD, not theoretical: `role=verification-feedback` has **two** producers with
  different callers — a seam-emitting resolve in
  `plan-marshall/workflow/execution.md:287-292` (passes `--workflow`, `--caller
  plan-marshall:phase-5-execute`, so it writes both surfaces) and a **hand-written** line in
  `workflow-pr-doctor/SKILL.md:30-38` (resolves *without* `--workflow`, then logs the line by hand,
  so it writes Surface A only). Six further hand-written sites exist for other roles
  (`plan-marshall/workflow/planning-outline.md:112`, `:146`, `:431`, `:484`;
  `planning.md:286`, `:326`). Any plan that runs both `verification-feedback` producers therefore
  carries one Surface-A line with no Surface-B partner, which silently offsets a seam resolve whose
  `log_entry('work', …)` failed: `resolve_roles == dispatch_roles` and the check reports
  `violations: 0` over a populated population.
- **Why it matters:** G10 establishes that the only divergence `shape_violation` can still detect at
  HEAD is a partial logging failure inside the seam — one `log_entry` succeeding while its twin
  fails. This gap removes the check's ability to see even that, for any role with a hand-written
  producer. The negative direction is discarded entirely (`if unmatched > 0`), so the asymmetry that
  would reveal the offset is never reported either.
- **Action:**
  1. Publish a per-role breakdown in the block — `role_pairing[]` rows carrying `role`, `resolves`,
     `dispatch_lines` and a **signed** `delta` — so both directions are visible instead of only the
     positive one. Keep the finding on `delta > 0`; report `delta < 0` as a fact, not a finding, so
     plans with hand-written lines do not start failing.
  2. State the caller-blindness in
     `standards/execution-context-dispatch-audit.md` alongside the corroboration limit at `:40`,
     naming the seven hand-written `[DISPATCH]` sites above as the reason a role's Surface-A count
     can exceed its Surface-B count without any dispatch being unrecorded.
- **Done when:** a fixture carrying one `effort resolve-target role=verification-feedback` record, no
  seam `[DISPATCH]` line for that role, and one hand-written
  `[DISPATCH] (plan-marshall:workflow-pr-doctor) … role=verification-feedback` line reports a
  non-zero signal (a `delta` row, or a finding) instead of `violations: 0`, pinned by a test.
- **Effort:** S
- **Risk if fixed:** the per-role rows grow the fragment for plans with many roles; cap the report to
  roles whose `delta != 0` if that proves noisy. No existing finding changes, so no plan that is
  clean today starts failing.
