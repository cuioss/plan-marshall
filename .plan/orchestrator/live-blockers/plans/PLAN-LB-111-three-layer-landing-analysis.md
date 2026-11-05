# PLAN-LB-111: `analyze` reads every landing on three layers — specified, implemented, correct — through one read-only leaf, so the epics stop carrying it as a custom rule

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-111-three-layer-landing-analysis.md` and is queued as one row file, `queue/PLAN-LB-111.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged in the 2026-11-04 inbox drain from the finding `pm-mcp-core-m2-m4-v2-001`, written by the orchestrator session of the
> consumer epic `pm-mcp-core-m2-m4-v2`. Severity: **highest** — the operator's words in that finding are "add it as highest issue
> … in order not to have this custom rules anymore". The epic carries the practice as its own standing rule R21 (revisions r5 and
> r6) only because `analyze` lacks it. Five landings were analysed on the three layers (PLAN-V2-05, 01, 12, 11, 08). The finding
> checked the installed plugin cache 0.1.2041; this draft re-read `analyze.md` Step 2 and `templates/landing-analysis.md` in the
> source tree at HEAD, and both read as the finding describes.

## Objective

`analyze` corroborates a full-ship landing against the merge diff, the PR state and the plan's artifacts, and writes
`landings/PLAN-NN.md` with a fidelity table, metrics and routing. It never reads the merged code. A landing whose lane report
passed the fidelity check can therefore carry a wrong spec premise, a file no deliverable explains, or a defect in the merged
code, and the orchestrator does not see it. The consumer epic found four such cases in five landings (a real defect in
`GitLabCiProvider.java`, swapped format arguments in `LessonFrontMatter.java`, and two spec contradictions the lane had to
resolve), and its lane report passed the fidelity check in every one.

This plan makes the three-layer analysis part of the verb. For every full-ship landing a read-only sub-agent reads three layers
by reading alone, never by building: **specified** (is the spec sound), **implemented** (does each deliverable trace to code and
to a test that can fail), and **correct** (is the merged code free of defects). The orchestrator re-reads each point the leaf
marks `checked` before recording it, writes a `## Three-Layer Analysis` section into the landing report, and keeps every verdict,
the report and every ledger write. A layer-3 defect goes to the operator at once and becomes a staged fix-plan spec only on the
operator's word.

## Deliverables

1. **`analyze.md` Step 4 carries the three-layer analysis, and the landing template has its section.**
   - Step 4 (full ship) gains a step that runs the three layers and writes the result into the landing report. It sits before the
     report is written, after the corroboration, and applies to a full ship only. A mid-flight observation (Step 5) is unchanged.
   - The layer definitions:
     - **Layer 1, specified.** The spec is sound; its premises and Done-when conditions are consistent with each other and with
       `main`.
     - **Layer 2, implemented.** Each deliverable traces to code and to a test that can fail. A file the diff touched that no
       deliverable explains is named, and so is a claim of the lane's report that the diff does not bear out.
     - **Layer 3, correct.** The merged code is read for defects: invariants, boundaries, error paths, concurrency, resource
       handling and the project's code rules. Each defect is given with the line, the triggering input and the effect.
   - The limit is stated in the step: **by reading, no build, no test run, no write.** What only a run could show is reported as
     `not shown by reading`, never as clean.
   - `templates/landing-analysis.md` gains `## Three-Layer Analysis` with a block per layer, a conformance list for the
     project's own rules (`CLAUDE.md` and the code rules it names), and one verdict per layer.

   *Done when:* doc tests assert that `analyze.md` Step 4 names the three layers with the definitions above, the "by reading, no
   build, no test, no write" limit and the `not shown by reading` tag, and that the template carries the section, the per-layer
   blocks, the conformance list and the verdict line. Each fails against HEAD, where neither file names the section.

2. **The reading is always done by one read-only leaf per landing, and the orchestrator re-reads what it records as checked.**
   - The leaf is dispatched on every full-ship landing, not "when the read burden is large". The vehicle is `execution-context-{level}`
     on the `orchestrator.analyze` surface, resolved with the same `manage-config effort resolve-target` form Step 2 already uses
     (all four facts, so the `[DISPATCH]` record is written). The prompt body carries the S1 read-only instruction and names the
     merge commit, the spec path, the three layers, the project's code rules and the limits.
   - One leaf per landing. When an inbox scan holds several landings, the existing rule that one drafting envelope iterates
     over all the drain's messages does not apply: reading merged code is the depth the dispatch rule exists for, and one landing's
     read must not share context with another's. State this in the step and record the reason.
   - Return shape `findings[N]{layer,severity,file,line,claim,verdict}` with `verdict` one of `checked` / `not_shown_by_reading`,
     plus the conformance list. The leaf writes nothing: no `Write` or `Edit` inside the epic tree, no `manage-status`,
     `manage-logging --store orchestrator`, `orchestrator queue` or `corpus set-verdict` call. The draft crosses the dispatch edge as
     data, which is the write-freedom test the Dispatch Decision Rule already states.
   - The orchestrator re-reads every `checked` point at its `file:line` before it records one, and records which it re-read. A point
     it cannot re-read is recorded as an unverified lead, as Step 2 already requires for any claim.
   - Step 2's index of dispatchable sub-steps ("Five … a complete index") is updated to name this sub-step, and the Dispatch
     Decision Rule's own list is updated wherever it names the analyze sub-steps.

   *Done when:* doc tests assert that Step 4 states the always-dispatch rule with no "when large" qualifier, names the one-leaf-per-landing
   shape and its reason, gives the return shape and both `verdict` values, states the re-read obligation, and forbids every ledger
   write from the leaf. The dispatch-workflow pin test names the new `--workflow` doc and the surface. Each fails at HEAD.

3. **Findings are routed by layer and nothing is fixed inline.**
   - A layer-3 finding is reported to the operator in the same turn it is recorded, never fixed inline, and becomes a staged
     fix-plan spec only on the operator's word. This is the existing rule that anything beyond the small-ops carve-out becomes a
     plan, applied to defects the analysis found.
   - A layer-1 or layer-2 finding names the spec or the part of the specification to correct. When it names a staged spec in this
     epic's corpus, the correction follows the same-act rule the Step 5b fold disposition carries, and a corroborated claim persists
     through Step 2b's `corpus set-verdict`.
   - The landing report's `## Three-Layer Analysis` verdict line says which layers had findings, so START HERE's reader sees a
     layer-3 defect without reading the report.

   *Done when:* doc tests assert the layer-3 rule (operator at once, no inline fix, spec only on the operator's word), the
   layer-1/2 rule with its pointer to the fold rule and Step 2b, and the verdict line in the template. Each fails at HEAD.

Split guard: three deliverables, one capability. D1 defines the analysis, D2 runs it, D3 routes what it finds.

## Standing Constraints

- **By reading, never by building.** Neither the leaf nor the orchestrator runs a build, a test or a verify as part of this
  analysis. A reading that needs a run says `not shown by reading`.
- **A leaf report is a lead.** Step 2's contract holds unchanged: the orchestrator corroborates, and a claim it cannot corroborate is
  an unverified lead and never a finding.
- **The orchestrator keeps every write.** Verdicts, the landing report, the queue stamps, the Open Defect and Watch entries and the
  logging all stay inline (see the write-freedom test in the Dispatch Decision Rule).
- **Who decides is unchanged.** The operator owns every fix-plan decision, and this plan changes no lane, no disjointness gate
  and no merge rule.
- **Do not change `landing-check`.** The completeness check and its required keys are out of scope (see Dependencies and
  Sequencing).
- **No Sonar.** Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none.
- **Tests state their purpose.** Every new or changed test states what it protects and is shown red at HEAD where its Done-when says so.

## Claim Labels

- OBSERVED: `analyze.md` Step 2 makes corroboration dispatchable "when the read burden is large", on the `orchestrator.analyze`
  surface, with the return shape `corroborations[N]{claim,verdict,evidence}` and `verdict` in `corroborated` / `contradicted` /
  `unverifiable` — read at `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` L47-49, in the source tree.
  The same paragraph says "Five sub-steps … a complete index".
- OBSERVED: the return shape has no field for a layer, a severity or a `not shown by reading` tag — same lines.
- OBSERVED: `templates/landing-analysis.md` has five sections (Deliverable Fidelity vs Spec, Metrics and Anomalies, Routing and Merge
  Behavior, Reconciliation Actions, Follow-Ups) and none reads merged code — read at
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md`, whole file.
- OBSERVED: `analyze.md` Step 4 corroborates "the PR number, the merge state, and the deliverable set" against git and the CI
  abstraction, and nothing in it reads the merged code — read in the installed cache 0.1.2051 copy of Step 4; the source-tree copy is
  not re-read for Step 4 (verify-at-outline).
- OBSERVED (the source finding's own account, a lead): five landings analysed on three layers found a defect or a spec contradiction
  in four (PLAN-V2-12, 11, 05, 08), and the lane report passed the fidelity check in every one. Third-party, consumer-repo text:
  corroborated only in that the practice exists as the epic's rule R21; its findings are not re-verified here.
- HYPOTHESIS: the Dispatch Decision Rule in `orchestration-model.md` enumerates the analyze sub-steps somewhere beyond L317 (the
  first part of the file ends at the canonical-form block, and the rest was not read for this draft). Find every list that names
  them and update each (verify-at-outline).
- HYPOTHESIS: `test_orchestrator_dispatch_workflow_pin.py` pins the `--workflow` doc and surface of each dispatch in `analyze.md`
  and is where D2's pin belongs (verify-at-outline).
- HYPOTHESIS: `effort-roles.md` § Orchestrator role group describes the `orchestrator.analyze` surface by what it covers, so a new
  always-dispatched use needs a sentence there (verify-at-outline).
- Verify-first clause (D2): before choosing the one-envelope-per-landing shape, re-read decision.log `5337c3` (the
  one-envelope-not-per-message ruling for the drafting sub-steps) and state in the PR why a heavy per-landing read differs from
  cheap drafting. If the outline finds the ruling is meant to cover this case, loop back and re-scope rather than override it.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — Step 2 dispatchable index, Step 4 three-layer step, finding routing (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md` — `## Three-Layer Analysis` section (D1, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md` — Dispatch Decision Rule, wherever it names the analyze sub-steps (D2; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-roles.md` — `orchestrator.analyze` surface description (D2; verify-at-outline)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py` — the new dispatch's `--workflow` doc and surface (D2)
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/test_analyze_three_layer_contract.py` — a new doc-contract test file for D1 and D3 (new file; the existing `test_inbox_drain_contract.py` is the nearest precedent)

## Dependencies and Sequencing

- **Depends on:** none.
- **Overlaps with PLAN-LB-69 (parked).** It shares `analyze.md` and `templates/landing-analysis.md`, and its D1 adds a two-leaf audit
  (a fidelity leaf and a process leaf, runbook-lane landings only) to the same Step 4. In substance the two are different — LB-69
  audits the run's conduct and this plan reads the merged code — but both change the leaf shape of one step. **Sequence this plan
  BEFORE LB-69**, and when LB-69 is re-grounded, reconcile its D1 against the leaf and return shape this plan lands. LB-69 is parked
  and not high; this plan carries the operator's highest grade.
- **Overlaps with PLAN-LB-75 and PLAN-LB-84 (parked)** on `landing-analysis.md` only if their deliverables edit it; read their
  Expected Surface at their re-grounding.
- **Not carried, and why.** The finding names three smaller gaps in the same verb. None is staged under the epic's focus rule
  (high and blocking only; token usage and measurement out of scope), and each is recorded as a Watch on `epic.md`:
  - `landing-check` reports `complete: false` on every runbook-lane landing because the lane writes `unknown` for `total_tokens`
    and `plugin_version`. That is measurement, which the focus rule excludes; the epic already folds `total_tokens` into the landing
    defects it records.
  - A partial landing (`merge_state=open`, `deliverables_done` below `deliverables_total`) has no named path in `analyze`. The
    orchestrator observes it, keeps the row `running` and writes no ship semantics today. A documented "observe, do not ship" branch
    is a judgement-call removal, not a blocker.
  - A downstream spec has no field for "read this landing's findings at your outline", and a `corpus` verb that lists the staged
    specs whose Expected Surface a finding names would make the hand-added Standing Constraints bullet mechanical. A convenience.
- **Cross-repo follow-through.** When this lands and is installed, the consumer epic can drop R21 from its `standing-rules.md`. That
  is the consumer's own edit and no deliverable here.
- **Running plans:** checked at emit by the disjointness gate; none were checked in this draft.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-111-three-layer-landing-analysis.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
