# Landing Analysis: PLAN-090 — Harness and Rule Gaps

epic: test-quality
workstream: WS-03
pr: #1294 (commit `94fd91c7`), two runs

> Landing record for one shipped plan. Written after verifying claims against ground truth at HEAD
> `2cd1a19c` by a dispatched read-only `execution-context-level-3` leaf.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — publish a `build_parser()` seam on the `script-shared` build CLI and on `credentials.py` | **shipped-as-specified** | `script-shared/scripts/build/_build_cli.py:588` and `_build_execute_factory.py:114` both `def build_parser()`; `manage-providers/scripts/credentials.py:29` `def build_parser()` and `:153` `def main()` |
| D2 — add `load_skill_module` / `get_skill_dir` addressing a skill-root `extension.py` | **shipped-as-specified** | `test/conftest.py:368` `def get_skill_dir`, `:484` `def load_skill_module`. **15** test modules already consume it |
| D3 — a `register=False` escape plus a growth-check guard for `sys.modules` collisions | **shipped-as-specified** | `script-shared/test_conftest_loader_contract.py:47` `UNRESOLVED_CALL_SITE_BOUND = 90`; `:61-85` a 23-name `KNOWN_REGISTRATION_COLLISIONS` frozenset matching the report verbatim; `register: bool = True` on all three loaders |
| D4 — widen `_PLAN_DELIVERABLE_ID_RE` and `_PR_REFERENCE_RE` to the live spellings | **shipped-as-specified** | `_analyze_test_conventions.py:117` and `:128` — both the `pull request` alternative and the **D-optional** deliverable form are present |
| D5 — measure the `no-lesson-id-in-skill-prose` false-positive rate and decide on importing the sibling's exemption | **shipped-as-specified** | `_analyze_lesson_id_in_skill_prose.py:69-76` records the measurement (159 lesson-ID tokens, **0** reachable only by the exemption) and the decision **not** to import it. The rule is correctly left unchanged |
| D6 — name the helper by role, not by path, in `conftest.py`'s `_routing_namespaces` docstring | **shipped-as-specified** | `grep build_test_helpers test/conftest.py` → no match |
| D7 — report per-rule deltas and the severity ladder | **shipped-as-specified; figures now stale** | The 317 / 183 / 286 / 802 figures were accurate at landing. Re-derived at HEAD: **267 / 106 / 201 / 589 total, 15 errors**. The drop is legitimate — 070, 080 and campaign run 1 landed afterwards. No rule is newly at zero, so **no severity flip is licensed**, exactly as D7 concluded |

**Six of seven code deliverables confirmed present on disk with the exact mechanism described. This is
the most strongly-verified half of the whole ingestion.**

## Metrics and Anomalies

- Whole-tree rule counts at HEAD, re-derived through the documented five-directory `PYTHONPATH`
  invocation: `test-module-line-budget` **267**, `test-module-preamble-boilerplate` **106**,
  `test-docstring-historical-prose` **201**, `subprocess-pythonpath` **15**; `unique-fixture-basenames`,
  `test-helper-module-misnamed` and `identifier-validator-corpus` all **0**.
- **Anomaly — run 02 did not touch run 01's residue at all.** Nine named items carried straight through.

## Routing and Merge Behavior

- Review: `coderabbitai` found both R3 and R4. Two of the three open classes were reviewer-discovered.
- CI/merge: landed at `94fd91c7`, after PLAN-070's `6514cf24` on the same day.

## Reconciliation Actions

- [x] row `status` → `landed`
- [x] row `pr` stamped → `#1294`
- [x] row `landing` stamped → `landings/PLAN-090.md`
- [x] Open Defect opened — R1 / R3 / R4 each rest on one instance, with no sweep
- [x] Open Defect opened — the **circular ownership contradiction** with PLAN-070
- [x] Open Defect opened — `credentials.py` coverage, genuinely unowned

## Follow-Ups

- ⛔ **R1, R3 and R4 are defect *classes* fixed at one instance each.** The epic's own residue says
  plainly there is "no sweep establishing it was the only one" — and a two-minute check confirms the
  worry: `grep -rln "monkeypatch.delitem(.*raising=False" test` returns **2 further sites**, neither
  examined for R4's shape. This is the clearest genuinely-unowned residue in the whole ingestion.
  Staged as **PLAN-160**.
  - **R1** — a guard pinning a file by *path literal* that a sibling slice renamed mid-run, breaking the
    control **invisibly** (`mergeable_state` stayed `clean`). Sweep: every guard/control naming a file
    owned by a different slice, re-expressed by role.
  - **R3** — hand-kept constant populations mirroring a live source. Sweep: every such mirror, converted
    to a derivation plus an equality assertion.
  - **R4** — `monkeypatch.delitem(..., raising=False)` whose teardown restores nothing when the key was
    absent at test start, leaking into `sys.modules` for the session.

- ⛔ **A live circular-ownership contradiction with PLAN-070.** Three unconverted `extension.py`
  preambles — `build-gradle/test_gradle_discover_modules.py`, `build-npm/test_npm_discover_modules.py`,
  `build-operations/test_extension_implementations.py` — are assigned by **070's report to `090 § D2`**
  and by **090's report to `070`**. Both plans are closed; the sites are still raw `spec_from_file_location`
  at HEAD. Neither has an open run. Assigned to **PLAN-135**.

- ⛔ **D1's scope was narrower than what PLAN-070 and PLAN-080 routed to it.** This plan's own brief
  called for a tree-wide `ParserSeamNotFound` re-derivation; its report **explicitly declined** it as
  *"not something this sweep replaces"* and scoped D1 to the 27 sites PLAN-060 had named. So
  `effort_presets.py` and `manage_terminal_title.py` — routed here by 070 — appear nowhere in D1, and
  `effort_presets.py` still has no seam at HEAD. Assigned to **PLAN-145**.

- **`credentials.py` at 52.6% coverage** is the stated cause of this plan's own condition-2 shortfall
  (83.40% → 83.34%). It **could not be re-derived** — no coverage artifact exists in the clone and
  running a build is outside the orchestrator's boundary. Reported **unavailable**, not assumed.
  Unowned; assigned to **PLAN-145**.

- **Standing pinned residue, correctly pinned:** 23 live `sys.modules` registration collisions and 90
  statically-unresolvable loader call sites, both still at their guard's baseline. These are **bounded by
  a guard that fails on growth**, which is the right posture — they are not silently accumulating.
  Recorded in the epic's `## Watches`, not as defects.
