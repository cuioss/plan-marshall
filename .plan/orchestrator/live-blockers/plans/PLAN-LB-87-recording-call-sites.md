# PLAN-LB-87: The recording call sites say what they know — a step id on every boundary row, an unmeasured spend instead of a zero, a duration on every build row

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-87-recording-call-sites.md` and is queued as one row file, `queue/PLAN-LB-87.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the landing analysis of PLAN-LB-49 (#1833, `3baf825e4`), `landings/PLAN-LB-49.md`, and its
> candidate-lessons `-003` and `-004`. Priority is **medium**: it is the dropped fourth deliverable of PLAN-LB-49
> (dropped 2026-10-15 for the high-and-critical-only instruction) with firmer evidence than it had then, and it
> closes the Open Defect "Dispatch-boundary rows carry no step id", now on its ninth landing. **Each deliverable
> is its own outline deliverable, and each Done-when is its own success criterion. Do not merge them.** A
> Done-when says "fails at `3baf825e4`" only where the behaviour is new at that sha; a clause that already holds
> says "holds at `3baf825e4`". A Done-when is never labelled "holds at" while a claim it rests on is still a
> HYPOTHESIS below.

## Objective

Every cost decision in this epic is made from rows the plan lifecycle writes about itself, and the rows are
written by call sites that know more than they pass. The boundary recorder accepts a step id and no call site
forwards one; the execute loop's exit path writes `--total-tokens 0 --tool-uses 0 --duration-ms 0` as literals;
the gate route of a build appends its ledger row with no duration while the daemon route stamps one; and the
retrospective runs before the metrics it is meant to score are recorded. This plan makes each row carry what its
call site holds, or say it is unmeasured, and puts the retrospective after the metrics.

## Deliverables

1. **Boundary rows carry the step id and the spend the dispatcher returned, or say it is unmeasured.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-documentation
   - Persona: plan-marshall:persona-implementer
   - The call-site templates forward `--step-id` on every `record-dispatch-boundary`: the finalize dispatcher
     (`phase-6-finalize/SKILL.md` L1196-1198), the execute loop (`plan-marshall/workflow/execution.md`
     L220-222, L265-267) and any other the outline finds with a content search. `record-dispatch-boundary`
     already accepts the flag (`manage-metrics.py` L4602).
   - The literal `--total-tokens 0 --tool-uses 0 --duration-ms 0` of the clean-exit template
     (`execution.md` L265-267) and the `accumulate-agent-usage --total-tokens 0 …` calls are gone: a spend the
     dispatcher did not return is left unmeasured, so the ledger distinguishes "no spend" from "not measured".
     On OpenCode the sub-agent return carries no `<usage>`; PLAN-LB-86 D1 and the runtime's own measured figure
     are the source there, so decide at outline whether the boundary recorder reads that figure itself.
   - The boundary recorder or the phase-exit check makes the omission visible instead of silent: a boundary row
     written without a step id inside a phase that dispatched is reported (decide at outline whether as a
     refusal or a finding, and record why). The flag is optional today, so the omission is silent.

   *Done when:* each of these fails at `3baf825e4`:
   - the documented call-site templates carry `--step-id`, checked by a test over the templates the finalize
     dispatcher and the execute loop actually render, not a keyword search of the document;
   - no documented template passes a literal `0` for tokens, tool uses or duration;
   - a boundary row written without a step id in a dispatching phase is reported;
   - `reconcile-ledgers` pairs a fixture row with its execution-log row on the step key, not on a timestamp window.

2. **Every build row carries the wall time of its build.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The gate route appends its `kind=build` row with `duration_seconds=None`
     (`_build_execute_factory.py` L536-541) where the daemon route stamps the measured value (L677, L715): the
     gate route stamps the wall time it already measured, and its `status`.
   - A build that failed before it ran (`status: error`, `exit_code: -1`) does not record `duration_seconds: 0`
     as if it had run for no time: the PLAN-LB-49 run's two failed `generate-claude` calls did.
   - The in-process route appends a row or the outline records that it cannot and what the retrospective reports
     instead; decide at outline after reading where the in-process path returns (HYPOTHESIS below).

   *Done when:* each of these fails at `3baf825e4`: a gate-route build appends a row whose `duration_seconds`
   is the measured wall time; a build that fails to start records no `0` duration; and a plan with one gate-route
   and one daemon-route build sums both in `total_build_seconds`, which today reads `unavailable`.

3. **The retrospective runs after the metrics it scores.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - In the PLAN-LB-49 run `plan-marshall:plan-retrospective` ran at 11:17 and `record-metrics` at 11:23, so the
     retrospective reported its token half as unscorable and its dispatch audit at `confidence: low`. The
     composed finalize order puts `record-metrics` before the retrospective, or the retrospective reads the
     figure from the runtime when `record-metrics` has not run; decide at outline and record why. The order
     is composed by the manifest composer, so the change is made there and not in a document.

   *Done when:* a composed finalize manifest for a plan with both steps lists `record-metrics` before the
   retrospective, and fails at `3baf825e4`.

4. **A generate canonical resolves to a command that exists.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The build wrapper ran `pwx generate-claude` and failed twice with `execution_failed`, `exit_code: -1`
     (`work.log` L6790, L6792 of the PLAN-LB-49 run); the main agent then ran `./pw generate --target …`
     directly for three targets and marked `deploy-target` done. A finalize step never needs a hard-coded
     build command. The resolution of the `generate-*` canonicals is corrected (`build-pyproject`
     `_pyproject_execute.py`, which names `pwx`), and the failure is reported as a failure to resolve rather than
     as an execution failure with a zero duration.

   *Done when:* a fixture project whose wrapper is `./pw` resolves `generate-claude` to a command that begins
   with it and not `pwx`, and a wrapper that cannot be found fails with a named resolution reason; each fails
   at `3baf825e4`.

Split guard: four deliverables across the recording call sites, the gate-route build row, the manifest order and
one canonical's resolution. Proceeding unsplit: each is a small, independent correction in the same
finalize-recording family and none needs the others. D2 and D4 touch the same build path (D4's failed-to-start
build is D2's second bullet).

## Claim Labels

- OBSERVED: `phase-6-finalize/SKILL.md` L1196-1198 renders `record-dispatch-boundary --plan-id … --phase 6-finalize --termination-cause … --total-tokens … --tool-uses … --duration-ms …` with no `--step-id`; `execution.md` L220-222 the same for `5-execute`; `execution.md` L265-267 passes `--total-tokens 0 --tool-uses 0 --duration-ms 0` — read by the orchestrator at `3baf825e4`.
- OBSERVED: `record-dispatch-boundary` declares `--step-id` with `default=None` — `manage-metrics.py` L4602-4604 (read by the orchestrator).
- OBSERVED: the gate route appends its build row with `duration_seconds=None` — `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` L536-541 (read by the orchestrator); the daemon route stamps it at L677, L715 (by the corroboration of the PLAN-LB-49 landing, not re-read).
- OBSERVED: the PLAN-LB-49 run recorded 17 boundary rows (1 in `4-plan`, 3 in `5-execute`, 13 in `6-finalize`), every one keyless and with `total_tokens 0`, `tool_uses 0`, `duration_ms 0`; `firing_comparison` paired 0 firings against 63 unpaired execution rows; `channel_completeness` ratio 0.256 — lesson `lb-49-opencode-measurement-004`, corroborated by the landing analysis.
- OBSERVED: the same run's ledger held 4 `kind=build` rows against 211 logged build calls, all four without a duration, and `total_build_seconds` read `unavailable`; the script cost rollup attributed 62.6% of the plan's script time to `pyproject_build` — lesson `lb-49-opencode-measurement-003`, corroborated in kind by the landing analysis.
- OBSERVED: the run's two `generate-claude` builds failed with `command: pwx generate-claude`, `exit_code: -1`, `duration_seconds: 0`, `error: execution_failed` — `archived-plans/2026-10-22-lb-49-opencode-measurement/logs/work.log` L6790, L6792 (read by the orchestrator).
- OBSERVED: `plan-marshall:plan-retrospective` ran at 11:17 and `record-metrics` at 11:23, per the manifest order at `decision.log:73`; the retrospective reported "token half unscorable" — by the corroboration.
- OBSERVED: an OpenCode sub-agent's return carries no `<usage>` block, so the figures a call site passes are zero for want of a source, not because nothing was spent — by the corroboration; the lesson's reading ("genuinely zero") is contradicted.
- HYPOTHESIS: `_pyproject_execute.py` is where the `pwx` command is composed — it is one of six files naming `pwx`; confirm which composes the failing command (verify-at-outline).
- HYPOTHESIS: the in-process build route appends no ledger row — confirm by reading where the in-process path returns in `_build_execute_factory.py` (verify-at-outline).
- HYPOTHESIS: `manage-execution-manifest` composes the finalize order from `marshal.json` `phase_6` steps and a default order table — confirm which one puts the retrospective first (verify-at-outline).
- Verify-first clause (deliverable 1): decide whether the boundary recorder reads the runtime's measured figure on a harness whose sub-agent return carries none, before scoping; PLAN-LB-86 D1 and D2 own the reader and the population, and a decision made in one plan is read, not remade, in the other.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the boundary call site (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — the execute loop's boundary templates (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` — `record-dispatch-boundary`, `reconcile-ledgers`, `accumulate-agent-usage` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — the gate-route row (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_execute.py` — the `generate-*` resolution (verify-at-outline) (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/` — the finalize order (verify-at-outline) (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/record-metrics.md` (verify-at-outline) (D1)
- HYPOTHESIS: `test/plan-marshall/manage-metrics/` (verify-at-outline) (D1)
- HYPOTHESIS: `test/plan-marshall/script-shared/` — the build row (verify-at-outline) (D2)
- HYPOTHESIS: `test/plan-marshall/build-pyproject/` (verify-at-outline) (D4)
- HYPOTHESIS: `test/plan-marshall/manage-execution-manifest/` (verify-at-outline) (D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-49 (shipped, `3baf825e4`).
- Overlaps with: PLAN-LB-86 on `manage-metrics.py` (this plan owns the call sites and the boundary recorder; PLAN-LB-86 the reader-to-landing chain and the window lookup — different functions); PLAN-LB-58 D3 on `build-maven` only if D2 changes shared build-row code both read. The gate will ask.
- Adjacent to: the Open Defect "A routed build leaves no change-ledger row for its plan" (not owned; D2 closes the duration half of it, not the daemon-working-tree half), and the PLAN-LB-44 red-CI triage route, neither edited here.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-87-recording-call-sites.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
