# PLAN-110: Every Test Runs, and the Suite Does Not Get Slower

epic: test-quality
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-110-every-test-runs-and-the-suite-does-not-slow-down.md` and is queued in the
> epic `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

> **Ingested from the standalone cloud lane.** The original brief is preserved verbatim at
> [`archive/110-every-test-runs-and-the-suite-does-not-slow-down.md`](../archive/110-every-test-runs-and-the-suite-does-not-slow-down.md).
> This spec supersedes it. Two things changed on ingestion and both are marked ⛔ below: the plan no
> longer runs in the cloud lane (so the `cloud-plan-lane` first-instruction block does not apply, and
> `.plan/` is available), and **D6's edit target moved** — `doc/plans/test-quality/README.md` no longer
> exists.

## Objective

Two properties of the test suite went unmeasured by every plan in this epic, and one of them is quietly
false: **tests are skipped**, and **nothing measured how long the suite takes**. Every build gate run
across the epic's landed reports ends `… passed, 14 skipped` — a passed count that climbs and a skipped
count that never moves, which is the tell that nothing looked at them. A skipped test is a contract that
stopped being checked while the build kept reporting success: the same false-clean signal this epic
exists to remove, turned on the suite's own reporting. Make the suite report **zero skipped tests** on
the CI runner with a small, named, guarded exception set, and give the epic's run conditions 3 and 4 a
literal, runnable command so a regression is caught by the run that causes it.

## Deliverables

1. **D1 — Derive the live skip set and classify every member.** Capture pytest's own skip report
   (`-rs`), which names each skipped test and its reason. Classify every live skip **and every skip
   site** into exactly one of: *tool the build already requires*, *tree always present in this
   repository*, *genuinely absent dependency*, *genuinely variable platform*, or *inverted guard*.
   **Gating and halting** — a member fitting no class halts the run rather than being assigned to the
   nearest one.
   *Done when:* every live skip and every skip site carries exactly one class, the run's own skipped
   count is recorded with its command, and any unclassifiable member has halted the run with the member
   named.

2. **D2 — Replace per-test tool guards with one preflight that fails.** For every guard on a tool the
   build already requires (`git`, `rsync` — ~30 sites), remove the per-test `skipif` and assert the
   requirement **once**, at session scope, so a missing tool fails the run loudly instead of deleting
   thirty tests quietly.
   *Done when:* no `test_*.py` carries a `skipif` on a tool the preflight requires; the preflight fails
   with a message naming the missing tool, **demonstrated** by making the check see an empty `PATH`
   entry and watching it go red; and the previously gated tests now run.

3. **D3 — Turn "the tree might not be here" into an assertion.** For every guard on `marketplace/bundles`
   or the real marketplace tree (~12 sites), replace the skip with an assertion that the tree is present.
   This repository **is** the marketplace; the condition cannot occur here.
   *Done when:* those tests run unconditionally and the assertion's failure message names the path it
   expected.

4. **D4 — Close the generated-executor gap without generating one.** Several tests skip because
   `.plan/execute-script.py` is absent — it is generated and git-ignored, so it is absent in CI by
   construction. Give those tests a fixture-built executor under `tmp_path`. Where a test genuinely
   requires the real generated executor, it moves to D5's exception list.
   *Done when:* no test skips on executor absence, each converted test asserts the same contract it
   asserted before, and any test moved to D5 is named with why a fixture cannot serve it.
   ⛔ **Re-scoped on ingestion:** the original forbade touching `.plan/` because the cloud lane did. This
   plan now runs under the ordinary plan lifecycle, where `.plan/` **is** present. The deliverable is
   unchanged anyway and the reason is stronger, not weaker: the executor is git-ignored, so it is absent
   in CI regardless of what is present locally, and a test that passes only because a developer machine
   happens to carry one is the defect. **Build the fixture; do not consult the real executor.**

5. **D5 — Bound the exceptions and guard the boundary.** Two kinds legitimately remain: *genuinely
   variable platform* (Windows symlink semantics, `/proc`) and *genuinely absent dependency*. Record them
   as a **named, enumerated exception list** and add a guard test that fails when a skip appears outside
   it. The absent-dependency class has **two** members: `pyright-langserver` (gates a module through a
   `pytestmark` plus two further sites) and `pytest-randomly` (absent, which is why PLAN-060's randomised
   hermeticity arm went unrun across all three of its runs). For each: **record a dependency proposal**
   naming the call sites it would unblock — a third-party dependency is a user-approval step — **and**
   cover the contract another way meanwhile, with a stub for the language server and a **reverse-order**
   run for hermeticity, which needs no plugin and is what PLAN-060 actually used to find a live
   order-dependent failure. Fix the **inverted guard** here too: a test that skips when an MCP server is
   *reachable* must be isolated from the ambient environment, not gated on it.
   *Done when:* the exception list exists and is enumerated; the guard fails when a skip is introduced
   outside it, **demonstrated** by adding one, watching it go red and removing it; a dependency proposal
   is recorded for **each** absent dependency with its call sites; the whole-tree reverse-order arm has
   run and its result is recorded; and the inverted guard no longer consults the ambient environment.

6. **D6 — Give the two run conditions an exact command.** The epic's five run conditions state condition
   3 (skipped count) and condition 4 (wall-clock) but carry no literal command for either, so two runs
   produce figures that are not comparable. Supply a runnable command for both, including the
   `--durations` slowest-tests capture so a regression can be attributed rather than merely detected. Do
   **not** restate the conditions — a second statement is a second thing to drift.
   ⛔ **Re-scoped on ingestion — the edit target moved.** The original named
   `doc/plans/test-quality/README.md`, which no longer exists: the epic is now this ledger and that
   document is the read-only audit record `.plan/orchestrator/test-quality/archive/README.md`. **Write the two commands into
   `test/README.md`** — PLAN-020's navigation-and-ownership document, which is git-tracked, is where a
   run actually looks, and is the tree's own home for how to run it. Then file an inbox message so this
   orchestrator can mirror them into the epic ledger's run-conditions note.
   *Done when:* `test/README.md` carries a literal, runnable command for condition 3 and one for
   condition 4; the report carries this run's own before/after figures for both; the slowest-tests
   capture is recorded; and the inbox message is filed.

7. **D7 — Report the measured deltas.** Skipped count before and after, whole-tree; the classified skip
   inventory, one row per site; the wall-clock before and after **with its population named**; the
   slowest-tests capture; the collected item count before and after; and the D5 exception list.
   *Done when:* the report carries every figure with the command that produced it.

## Claim Labels

- OBSERVED: the suite skips, and the count is constant across the epic's landed reports (`… passed, 14
  skipped`, four times) — read in the archived run reports under `.plan/orchestrator/test-quality/archive/`
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: archived run reports under archive/ are immutable historical records unaffected by bf1b7ed6; the 14-skipped figure across four landed reports stands as read, not independently re-executed this pass
- HYPOTHESIS: there are **78 skip sites** under `test/` across **26 files** at `bf1b7ed6` (re-scoped from
  ~60), concentrated in `test/sync-plugin-cache/` (**42**, re-scoped from ~32 — `test_staleness_guard.py`
  33 plus `test_sync_engine.py` 9, gated on `git`/`rsync`) and `test/pm-plugin-development/` (**14**,
  re-scoped from ~12 — `plan-marshall-plugin` 3 plus `plugin-doctor` 11) — confirm/refute at the tree
  itself via a `pytest.mark.skipif` / `pytestmark` sweep over `test/**` (verify-at-outline). ⛔ **All three
  original figures were stale on the LOW side**, so D1 sizes ~30% more work than the spec first assumed.
  **The figures remain leads; D1 re-derives them, and D1 is gating.**
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: skip-marker sweep at bf1b7ed6 finds 78 sites across 26 files, not ~60: sync-plugin-cache 42 (test_staleness_guard.py 33 plus test_sync_engine.py 9) and pm-plugin-development 14 (plan-marshall-plugin 3 plus plugin-doctor 11). ALL THREE figures were stale on the LOW side. Re-scoped in place to 78/42/26
- HYPOTHESIS: the live skip set is much **smaller** than the population of skip *sites*, because most
  conditions are false in this environment — confirm/refute at pytest's own `-rs` report
  (verify-at-outline). This is why D1 classifies both populations separately: a guard that does not fire
  here but would fire in CI is the one that must not be missed.
  - verdict: unverifiable | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: confirming requires an actual whole-tree pytest -rs run to see which conditions fire in this environment; not executed in this read-only re-grounding pass
- OBSERVED: the suite did **not** get slower across the epic's executed half — 781 s at `7de3084`,
  786 s at `24271bc`, 788 s at `7cadb98`, read from GitHub Actions' `Run verification` step timings for
  `verify / verify` on `main`. ⚠️ **This is the epic's only non-git-reachable confirm/refute artifact.**
  A run without API access reports the re-derivation **unavailable** rather than substituting a local
  measurement whose population is not comparable. The whole-workflow duration is a far noisier
  instrument than the step (same-day `main` runs range ~9–27 minutes) — compare the **step**.
  - verdict: unverifiable | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: its confirm/refute artifact is the GitHub Actions Run verification step timing for verify/verify on main, the epic's only non-git-reachable artifact; this pass had no CI API access, consistent with the prior unverifiable disposition at 09f92b5e
- OBSERVED: PLAN-080's slice went from ~211 hand-built namespaces and zero `parse_ns` calls to **40**
  `parse_ns` calls across 14 files at `bf1b7ed6` (re-scoped from 39), **every one at module scope** — the
  hoisting `parse_ns`'s own docstring prescribes. So a full-slice **B6** conversion need not pay the
  per-call cost. ⛔ **The "zero hand-built" half is REFUTED**: **6** hand-built `argparse.Namespace(...)`
  sites remain in that slice — `test_epic_report.py` (3), `test_epic_report_reproducibility.py` (2),
  `test_corpus_lsp_honesty.py` (1) — all landed AFTER PLAN-080 closed. ⚠️ This is the conformance-drift
  watch firing inside an already-converted slice, at file-content level. That is one slice's evidence, and
  PLAN-070's outstanding conversion is roughly **2.3×** its size by namespace count.
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: the zero-hand-built half is REFUTED at bf1b7ed6: 6 argparse.Namespace(...) sites remain in PLAN-080's slice across test_epic_report.py (3), test_epic_report_reproducibility.py (2) and test_corpus_lsp_honesty.py (1), all landed after PLAN-080 closed; parse_ns calls are 40 across 14 files, not 39. Re-scoped, and noted as the conformance-drift watch firing inside a converted slice
- OBSERVED: `parse_ns` re-executes the script module on every call — read at `test/conftest.py` §
  `parse_ns` docstring. This is the mechanism by which the epic's remaining work could move the number.
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: verified verbatim at test/conftest.py:785 - Cost: this re-executes the script module on every call, via load_script_module

## Expected Surface

- OBSERVED: `test/conftest.py` — D2's session-scoped preflight and D5's guard. ⚠️ **Shared with
  PLAN-090** (loader mechanics: `load_script_module`, `get_scripts_dir`, registration behaviour) and
  adjacent to PLAN-105 § D4. This plan owns the **preflight and the skip guard** and touches nothing else
  in the file.
- OBSERVED: `test/test_conftest_discipline.py` or a sibling root-level meta-test — D5's exception guard,
  placed per the convention that module already sets
- OBSERVED: `test/sync-plugin-cache/` — D2, the largest concentration of tool guards
- OBSERVED: `test/pm-plugin-development/` — D3, D4
- OBSERVED: `test/marketplace/` — D3
- OBSERVED: `test/plan-marshall/lsp-client/`, `test/pm-plugin-development/plan-marshall-plugin/` — D5's
  absent dependency and its in-process stub
- OBSERVED: `test/plan-marshall/tools-file-ops/`, `test/plan-marshall/build-server/` — D5's platform
  exceptions, **recorded rather than changed**
- OBSERVED: `test/plan-marshall/platform-runtime/`, `test/plan-marshall/workflow-integration-git/`,
  `test/plan-marshall/workflow-integration-github/`, `test/plan-marshall/phase-6-finalize/`,
  `test/marketplace/targets/claude/` — the remaining scattered sites D1's classification assigns
- OBSERVED: `test/README.md` — D6 only ⛔ (re-scoped; see D6)

⚠️ **This surface crosses several reduction slices deliberately** — skip sites do not respect the epic's
partition. Confirm no plan in `## Dependencies and Sequencing` is in flight before starting, and **halt
and report** rather than editing a file a sibling owns.

## Dependencies and Sequencing

- Depends on: PLAN-010 and PLAN-020 (landed). Nothing else blocks it.
- **Run it before the module-budget campaign continues** — the campaign is the change most likely to
  move the wall-clock, and this plan is the instrument that would notice.
- Overlaps with: PLAN-090 (`test/conftest.py`, different halves); PLAN-105 (`test/_shared/` and
  `test/conftest.py` — D4's instruments sit beside D2's preflight); PLAN-140 (whichever slice a campaign
  run is holding — this plan's skip sites cross every slice); PLAN-040 (`phase-6-finalize/`,
  `workflow-integration-git/`, `workflow-integration-github/`); PLAN-060 (`lsp-client/`,
  `platform-runtime/`, `tools-file-ops/`); PLAN-070 (`build-server/` — the weakest overlap: this plan
  *records* that skip as a platform exception rather than writing it, but the file is shared);
  PLAN-080 (`test/sync-plugin-cache/`, `test/pm-plugin-development/`, `test/marketplace/`).
  **All six reduction plans have landed**, so those six overlaps are inert unless a follow-up run
  re-enters one. The live overlaps are PLAN-105 and PLAN-140.
- Adjacent to: `marketplace/bundles/**` — a production defect found here is **recorded**, never fixed.
  PLAN-090 owns that surface.

## Out of Scope

- Making CI **faster**. The subject is *not getting slower*, a different and far cheaper commitment.
- Adding `pyright-langserver`, `pytest-randomly`, `hypothesis` or any third-party dependency. D5 records
  the proposal; it does not take the decision.
- Any `marketplace/bundles/**` file — PLAN-090's.
- Splitting any module over the 400-line budget — WS-04's.
- Deleting a test because making it run is awkward. A deleted test and a skipped test report the same
  thing, and the second at least says so.

## Split-Guard Note

⚠️ **Seven deliverables is above the epic's ~6 presumptive split threshold, and proceeding unsplit is a
recorded decision** (see the epic's `## Decisions`). D2, D3, D4 and D5 each act on **one class of D1's
classification**, so splitting them puts the gating derivation in one plan and its consumers in others —
and every consumer then re-derives it, which is how this epic's partition came to be re-derived four times
with four different dispositions. D7 is a report and D6 is a two-line documentation edit, so the real code
weight is D2–D5.

⛔ **If a run cannot finish, stop after D5 and report.** D1–D5 is a coherent landing point: the skips are
classified, the removable guards are gone, and the exception list plus its guard exist, so the population
cannot silently regrow. **D6 without D5's guard is not** — it would publish a command for a condition
nothing holds.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-110-every-test-runs-and-the-suite-does-not-slow-down.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
