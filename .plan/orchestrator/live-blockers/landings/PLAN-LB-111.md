# Landing Analysis: PLAN-LB-111 — `analyze` reads every landing on three layers through one read-only leaf

epic: live-blockers
workstream: WS-03
pr: #1908

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-111.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `8859bc1b0b85f219dd88b4ab539e1d4b730916d5` (merge queue), read through the `ci` abstraction as `state: merged`. Landing message `rb-lb-111-three-layer-landing-analysis-001.md`; the diff `185d41543..8859bc1b0` touches seven files, which matches the message.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — Step 4 three-layer step and the template section | shipped-as-specified | `workflow/analyze.md` Step 4 "The three-layer analysis" (layer definitions, the limit, the `not shown by reading` tag); `templates/landing-analysis.md` `## Three-Layer Analysis`; `test_analyze_three_layer_contract.py` |
| D2 — one always-dispatched read-only leaf per landing, orchestrator re-reads `checked` | shipped-modified | Dispatch, return shape, re-read obligation and write ban are in Step 4. The leaf's `--workflow` doc is a NEW file, `standards/three-layer-analysis.md`, not `analyze.md` (the lane found that loading the whole verb doc handed the leaf ledger-write instructions). The Step 2 index now says six, `orchestration-model.md` says eight, `effort-roles.md` names the surface, and the dispatch pin names the new doc |
| D3 — findings routed by layer, nothing fixed inline | shipped-modified | Routing is in Step 4 and the template carries the verdict line. The spec's stated effect (START HERE shows a layer-3 defect) is NOT delivered; the lane reported it as a gap instead of narrowing it away |

The lane's own account (message) was checked against the diff and the PR body. Two claims differ from the diff: the PR body says the new bullet carries `--workflow …/analyze.md` and `TestThreeLayerAlwaysDispatched` has 7 tests, while the merged state names `…/standards/three-layer-analysis.md` and the class has 10 methods (three were added in review fixes, after the cited failing run).

## Three-Layer Analysis

The landing was read on three layers — the spec, the deliverable trace, and the merged code — by one read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`), and the orchestrator re-read the points recorded as `checked` below before writing them here. The reading is by reading, no build, no test run, no write. This is the first landing read under the contract this plan shipped; the contract was applied from the source tree because the installed plugin cache predates it.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is depth work, and this landing's read must not share context with the LB-113 landing read in the same firing.
- **Verdict:** layer 1 findings; layer 2 findings (minor); layer 3 findings (one major). The layer-3 major is below.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| L1-1 | D3's premise "START HERE's reader sees a layer-3 defect" contradicts main: START HERE is generated from queue rows and the spec itself puts the queue and `landing-check` surface out of scope. The lane delivered "visible without reading the section" and said so. | checked | `plans/PLAN-LB-111-…md:86`; `analyze.md` Step 4 verdict-line sentence |
| L1-2 | The Expected Surface named no leaf workflow doc although D2 requires one (`--workflow`). The added `standards/three-layer-analysis.md` is explained by D2; the declaration was too narrow. | checked | `plans/PLAN-LB-111-…md:136-143` |
| L1-3 | D2's Done-when asks Step 4 to restate the write ban and return shape, which the Dispatch Decision Rule says verb docs do not restate. The lane accepted this (self-review F11). | checked | `plans/PLAN-LB-111-…md:75`; `orchestration-model.md:330` |
| L1-4 | The spec spells one tag two ways, `not shown by reading` (D1) and `not_shown_by_reading` (D2); both carried into the docs. | checked | `plans/PLAN-LB-111-…md:49,66` |

**Layer 1 verdict:** findings — 4 (none blocking). The verify-first clause: the lane could not re-read decision.log `5337c3` (absent from its checkout) and stated the rationale from the rule text; the PR body does not cite it.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `analyze.md` Step 4; `landing-analysis.md` | `test_analyze_three_layer_contract.py` (headings absent at the base, file-exists assertion) | none | checked |
| D2 | `analyze.md` Step 2 index and Step 4; `orchestration-model.md` index; `effort-roles.md` | contract tests, `test_orchestrator_dispatch_workflow_pin.py` pin and count cross-check | `standards/three-layer-analysis.md` (explained by D2); PR-body claims on the `--workflow` doc and the test count differ from the diff | checked |
| D3 | `analyze.md` routing; template verdict line | `TestThreeLayerRouting` (3) | the spec's START HERE effect | checked |

The tests are anchored and non-vacuous overall; two weak points (a bare `correct` substring in the pin; "Six" pinned only as a literal). Whether they were red at `5555baf33` and are green at the merge cannot be shown by reading — `not_shown_by_reading`; the lane's gate results (32594 tests at `52204d016`, verify green on CI) are the lane's account, with CI state read through the `ci` abstraction.

**Layer 2 verdict:** findings — 3 (minor/info).

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `templates/landing-analysis.md:33,47,59` | A layer-1 or layer-2 point only a run could show | Layers 1 and 2 offer only `{clean \| findings}` in their summary and verdict slots while their rows allow `not_shown_by_reading`; only layer 3 got the third option. The template forces the "clean" that Step 4's limit forbids. Re-read by the orchestrator: confirmed. | major |
| L3-2 | `workflow/analyze.md` Step 4 analysis block, item 1 | Any full ship | The analysis block says to write the result into `landings/PLAN-NN.md` under `## Three-Layer Analysis`; item 1 then Writes the whole report from the template. Either item 1 overwrites the section or a second write happens that the Inline-only APPLY list does not name. Re-read: both texts present (`analyze.md` analysis block and item 1). | minor |
| L3-3 | `analyze.md` routing bullet (layer 1/2) | A layer-1 finding to persist | The corpus value is derived "from the layer-1 finding" with no mapping from `checked`/`not_shown_by_reading` plus severity to `corroborated`/`contradicted`/`unverifiable`; two runs can persist different verdicts. | minor |
| L3-4 | template Dispatch line vs the section preamble | A fall-back where the dispatch did not return | The fixed line "one read-only leaf per landing" is false on the inline fall-back the preamble allows. | minor |
| L3-5 | `standards/three-layer-analysis.md:14` | A cross-repo landing | "names that repository's path" has no declared field; the envelope contract wants `WORKTREE` repo-relative. | minor |
| L3-6 | `standards/three-layer-analysis.md:32` | A leaf with Bash and `ci` read | Nothing forbids the leaf from fetching PR text itself; the containment the doc claims comes from no rule in it. Observed in this firing: the leaf fetched PR #1908 directly (bot-generated summary text in the body), and treated it as data. | minor |
| L3-7 | `conformance[N]` vs `conformance[M]` | — | Shape spelled two ways between Step 4 and the leaf doc; the tests pin `[N]`. | minor |

**Layer 3 not shown by reading:** whether the new tests were red at the base and green at the merge.

**Layer 3 verdict:** findings — 7 (one major, six minor).

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | No duplication — cross-reference instead | deviates | layer definitions twice (`analyze.md` Step 4 and the leaf doc), return shape three times, write ban three times |
| CLAUDE.md § Documentation Standards | No timestamps, current state only | conforms | no dates or changelog text in the added docs |
| `orchestration-model.md` Dispatch Decision Rule | Verb docs do not restate the safety constraints | deviates | `analyze.md` Step 4 restates the ledger-write ban; required by the spec's D2, accepted by the lane |
| `orchestration-model.md` Dispatch Decision Rule | Resolve carries all four facts with a concrete `--workflow` | conforms | pinned in the dispatch pin test |
| PLAN-LB-111 Standing Constraints | `landing-check` unchanged, no Sonar | conforms | seven files, no script change |

## Metrics and Anomalies

- Tokens: `unknown` — the lane wrote `unknown` for `total_tokens`; recorded as an unobserved fact, not zero. `landing-check`: `complete: false`, `missing_keys: [total_tokens]`.
- Duration: not supplied.
- Anomalies: the lane hit the explicit 1778 s `verify` bound and ran the split form (`quality-gate` plus whole-tree `module-tests`, both green). The build daemon was unreachable, so all 22 builds ran in process. The run's own rule breaks (`wc -l`, two `grep -n`, one chained `ls`) were disclosed in its message.

## Routing and Merge Behavior

- Review: coderabbit (required) reviewed `4da820441` and `40c99aeaf`; the last two re-triggers were quota-refused and the standing authorization applied. Sourcery (optional) reviewed `4da820441`. Every thread was answered and resolved.
- CI/merge: merge queue, merge-group run success, `merged`. `origin/main` moved once during the run (a workflows-only change) and was merged in cleanly.
- Sonar: `n/a` — Sonar is not enabled for this project and is ignored.
- Collision: none observed. The `uv.lock` re-resolution that the build produced was already on main through PR #1909, so no follow-up PR was needed.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped — `1908`
- [x] row `landing` stamped — `landings/PLAN-LB-111.md`
- [x] row `plan_marshall_plan_id` stamped — `lb-111-three-layer-landing-analysis` (the lane name the sender `rb-lb-111-three-layer-landing-analysis` carries)
- [x] epic.md narrative reconciled — the Open Defect for the incomplete landing message, a Watch for the layer-3 findings, and the START HERE gap recorded
- [x] resume anchor updated and `queue-view.md` regenerated

## Follow-Ups

- L3-1 (major) and L3-2 to L3-7 are reported to the operator; a fix-plan spec is staged only on the operator's word.
- The START HERE verdict propagation (L1-1) is not delivered and is recorded as a Watch, not staged.
- The leaf's `execution-context-{level}` vehicle versus the Bash-free reader variant is the lane's own injection-hardening follow-up; it is a plan-level decision and is recorded with L3-6.
- Parked PLAN-LB-69 shares `analyze.md` Step 4 and the template: its re-grounding must reconcile its D1 against the leaf and return shape that landed here.
