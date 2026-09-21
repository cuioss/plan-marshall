# Landing Analysis: PLAN-10 — the unowned layout, executor, host-signal and permission-grammar couplings

epic: multiplattform
workstream: WS-03
pr: #1449 (https://github.com/cuioss/plan-marshall/pull/1449)

> Landing record for one shipped plan. Lives at `landings/PLAN-10.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Drained from `inbox/layout-and-executor-residuals-001.md`, corroborated against the merged diff
(`a7ca9e491`), the CI abstraction, and the change ledger. This is the plan the operator widened
from five deliverables to seven at the 2026-09-08 decision; **five of the seven closed, two split
out**.

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| **D1** — `marketplace_paths.py` fallback stops duplicating the runtime's | **report-only, and the spec permitted it** | Single-sourcing reported structurally impossible (import cycle); circularity documented; lockstep guarded by pre-existing #1405 tests. `marketplace_paths.py` is absent from the diff. The spec's done-condition asked for "either single-source **or** a lockstep test … say which, with the reason" — the reason was given. |
| **D2** — `discover_local_scripts` resolves its root | **shipped-as-specified** | `generate_executor.py` routed through `get_project_skill_roots`; `test_generate_executor_behavior.py` carries the red-first pins. |
| **D3** — executor session-cache write gets a runtime home | **already satisfied; residue was a stale docstring** | The write was found already relocated; the docstring was corrected. The spec's second branch (record why, narrow the row) is what applied. |
| **D4** — `HARNESS_BASH_CEILING_SECONDS` behind the runtime | ⚠️ **shipped WIDENED, on an in-flight operator authorisation** | Became a **new platform-runtime op** (Claude 600 / OpenCode 120) rather than a constant relocation: both runtimes, the router, the base, the contract and `SKILL.md`, plus four consumers. Honours `status: no-op`. A CodeRabbit finding produced a red-first `KeyError` test. |
| **D5** — `manage-files.py` IDE launch leaves core CRUD | **honest decline** | Re-derived as a per-**host** fact, not per-target, so the relocation argument does not carry. `manage-files.py` absent from the diff. ⭐ A decline recorded with its reason is a legitimate outcome under this epic's own §D precedent. |
| **D6** — `permission_fix.py` permission-DSL residue | **split out, no code** | Absent from the diff, as is its test tree. |
| **D7** — `permission_doctor` direct-route false zero | **split out, no code** | Absent from the diff, as is its test tree. |

⭐ **The split guard's escape clause fired exactly as written.** When the widening was recorded I
attached an escape: *"if the outline finds D6+D7 do not share D1–D5's implementation shape, split
them out as one spec rather than forcing the fit — and record that as the second resolution of this
guard."* The plan found precisely that and took the escape. This is a designed-in pressure valve
being used, not a plan quietly dropping scope.

## ⛔ Under-declaration: 19 undeclared paths — the worst in the epic — and the cause is a NEW mechanism

Realized **22** paths against **12** declared entries; **3** covered, **19** undeclared. That beats
PLAN-11's 15. But the causes are not the same, and the difference is the whole finding.

**All 19 are downstream of D4's mid-flight widening.** "Relocate the constant" and "add a new
platform-runtime op" are different *kinds* of change: the first touches one file, the second
necessarily touches both runtime implementations, the router, the base class, the contract, the op
table, and every consumer that reads the value.

| Undeclared cluster | Count |
|---|---|
| `platform-runtime/**` — SKILL.md, contract.md, `platform_runtime.py`, `runtime_base.py`, `claude_runtime.py`, `_claude_runtime_impl.py`, `opencode_runtime.py` | 7 |
| `test/plan-marshall/platform-runtime/**` | 5 |
| consumers — `build-pyproject` (×2), `extension-api`, `manage-architecture` (×2), `phase-6-finalize` | 6 |
| `test/plan-marshall/manage-architecture/test_consumer_ceiling_via_seam.py` | 1 |

### ⛔ The gate consequence, and it is the third instance

`platform-runtime/**` is in **PLAN-06's** declared surface AND **PLAN-07's**. Worse: PLAN-07
declares `marketplace/bundles/plan-marshall/**`, which covers **13 of the 19**. PLAN-10 therefore
landed deep inside a staged sibling's declared surface while declaring none of it. Had PLAN-07 been
running concurrently — which the gate would have permitted — that is a large, unpredicted
collision. PLAN-11 did the same thing to `platform-runtime/**`; this is the second time that exact
surface has been touched undeclared, and the third under-declaration with a gate consequence.

### ⛔ What is genuinely NEW: no rule covered this

The `analyze` workflow carries a same-act obligation — *a fold that adds a file or module surface
updates that spec's `## Expected Surface` in the SAME edit*. That rule binds the **orchestrator**
when it folds a signal into a staged spec. **It does not bind an operator-authorised widening
issued to a plan that is already running.** The plan recorded the widening honestly in its own
`plan.md` WIDENED annotation and disclosed it in the hand-off; what nobody did — and what no rule
required of anybody — was update the orchestrator spec's `## Expected Surface`, which is the
artefact the disjointness gate actually reads.

⛔ **So this is not another instance of the known pattern.** The known pattern is a spec that
under-declares at authoring time. This is a spec that was **accurate when staged** and was
invalidated mid-flight by an authorised scope change, with no obligation attached to the
authorisation. Fixing the authoring discipline would not have prevented it.

### ⭐ The over-declaration, by contrast, is the system working

Nine declared entries went unrealized, and every one is explained: D1 report-only
(`marketplace_paths.py` + its tests), D5 honest decline (`manage-files.py` + its tests), D6/D7 split
out (both permission files + their tests), and `test/plan-marshall/tools-file-ops/**` because D4's
tests landed under `platform-runtime` instead. **A declared-but-unrealized entry following a
recorded decline is not sloppiness** — it is a plan declining work and saying so, which is exactly
what this epic's §D precedent asks for. Only the *undeclared* direction is a defect.

## Metrics and Anomalies

- **Tokens: not reported.** `total_tokens=unknown`; `landing-check` → `complete: false`,
  `missing_keys: [total_tokens]`. **8-for-8 on the OpenCode lane** — folds into the standing entry.
  The hand-off states the routing rule explicitly ("a read failure routes to `unknown`"), which is
  the anti-`n/a` rule stated as lane behaviour rather than rediscovered per plan.
- ⭐ **The test-count drop REVERSED, and a permanent coverage loss is refuted.** Three readings from
  the same `verify` invocation shape: **24773** (PLAN-11, 09-07 07:18) → **20736** (PLAN-21, 09-07
  21:36) → **25254** (PLAN-10, 09-08 11:15). The count is now *above* the pre-drop figure, so the
  −16% was transient. ⚠️ What remains unexplained is the instability itself, and nothing in the
  pipeline compares one gate's count to the last — the watch is narrowed to that, not closed.
- **Build gate: green, and the "merged tree" claim holds — a third consecutive clean case.** Ledger
  row `2026-09-08T11:15:34Z`, `exit_code: 0`, `tests_run: 25254`, worktree `--project-dir`; merge at
  `11:39:41Z`. Merge parent `17906028b` (#1448) landed `06:28:46Z`, five hours earlier, and nothing
  landed in the 24-minute window. Verified tree equals merged tree.

## Routing and Merge Behavior

- **Review — the required arm was obtained.** CodeRabbit reviewed and raised **3** findings, all
  fixed and confirmed in `42751b006`; one of them produced D4's red-first `KeyError` test, so the
  review improved the deliverable rather than only gating it. Sourcery rate-limited — **optional,
  correctly not counted as a shortfall**. `cuioss-review-bot` not named in the hand-off.
- **Independent Step 6 sub-agent: verifier-clear**, all six consumer-kind sweeps clean. One finding
  dismissed as out of scope (`_build_execute_factory.py:843` → PLAN-07 D3). ⭐ That dismissal is
  itself well-formed: it names the owning plan rather than simply declining.
- **CI/merge:** base-advance merged `origin/main` (#1448), re-gated, pushed (`fcfeb0a66`); merged
  via the merge queue as `a7ca9e491`, confirmed an ancestor of `origin/main`. Branch prefix
  `chore/` — canonical.

## Reconciliation Actions

- [x] row `status` → `landed`; `pr` `#1449`; `landing` `landings/PLAN-10.md`; `plan_marshall_plan_id` `n/a`
- [x] epic.md narrative reconciled from status.json
- [x] Open Defect — landing incomplete (`total_tokens`), folded as the 8th instance
- [x] Open Defect opened — **the same-act obligation does not reach an in-flight authorised widening**
- [x] Watch updated — test-count instability narrowed; permanent loss refuted
- [x] Watch updated — under-declaration, third gate consequence, new cause recorded
- [x] resume_anchor updated; START-HERE and Ordered Queue regenerated

## Follow-Ups

- **F1** ⛔ **D6/D7 need a spec or they are lost.** Both are unowned inventory rows that have
  survived several rounds; splitting them out of PLAN-10 removes their only home. Staged as
  **PLAN-22** at this drain — this is completing the guard's recorded second resolution, not new
  scope.
- **F2** ⚠️ **Unresolved discrepancy in the hand-off, flagged rather than guessed.** The report says
  the split leaves "§C 5/6" open, but D6/D7 are **§B** rows 5 and 6 (`permission_fix.py`,
  `permission_doctor.py`); §C 5 and 6 are D4's ceiling constant (closed) and D5's `detect_ide`
  (declined). PLAN-22 is staged against the §B rows, which is what the diff supports. If §C was
  meant, say so and PLAN-22's scope changes.
- **F3** PR **#1445** (PLAN-21's contract-edit follow-up) — check whether it has merged.
- **F4** `_build_execute_factory.py:843` — dismissed here, owned by **PLAN-07 D3**. Carried.
