# Landing Analysis: PLAN-050 — Plan State and Records Test Reduction

epic: test-quality
workstream: WS-02
pr: #1258 (run 01), #1266 (run 02)

> Landing record for one shipped plan. Lives at `landings/PLAN-050.md`. Written after verifying claims
> against ground truth — a report claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis contract.

**Ground-truth check run at HEAD `2cd1a19c`** by a dispatched read-only `execution-context-level-3` leaf,
against the archived `plan.md`, `report-01.md` and `report-02.md`.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — decompose `test_audit_checks.py` (~8,700 lines / 92 classes) into per-check modules plus `_audit_fixtures.py` | **shipped-as-specified** | Both `test_audit_checks.py` and `test_audit.py` are **gone**; 59 `test_audit_check_*.py` modules plus `_audit_fixtures.py` are present. All **24** of the skill's inventory checks map to a filename by prefix |
| D2 — retire per-subcommand `Namespace` builders via `parse_ns` (**B6**) | **shipped-partial** | `manage-metrics` fully converted (0 `_ns_` builders). The reported residue of 15 builders in `manage-lessons`/`manage-status`/`manage-tasks` has shrunk to **5**, all in `manage-status` fixture modules — and the shrinkage is **unattributed to any tracked run**, most likely incidental to PLAN-100's hoisting |
| D3 — one `_{domain}_fixtures.py` per directory (**B4** + **B10**); rename `manage-tasks/_helpers.py` | ⛔ **REFUTED at HEAD** | The rename shipped. But D3's own done-when — *"each directory has at most one fixture module"* — is **false in the tree today**: every one of the ten directories now carries multiple `_*_fixtures.py` (`manage-metrics` 9, `plan-retrospective` 15, `manage-status` 10). **This is not a PLAN-050 regression**: PLAN-100 deliberately hoisted per-**source-module** rather than per-directory and disclosed the deviation in its own report — but **nothing reconciled that deviation against D3's criterion** |
| D4 — split every module over the 400-line budget | **shipped-by-another-plan** | Reported NOT DONE at both runs (59, then 58 over budget). At HEAD only **3** modules in the slice exceed 400 lines — closed by PLAN-100's campaign run 1, not by PLAN-050. PLAN-100's own exit is **non-converging**: the 3 survivors are single-class modules its D2 forbids splitting |
| D5 — parametrize tabular families (**B5**) and strip historical prose (**B3**) to zero findings | ⛔ **REFUTED at HEAD** | The prose half reported 24 → 0. Re-running the doctor over `audit-archived-plan-retrospectives/` **alone** returns **22** `test-docstring-historical-prose` findings, all bare `#NNN` PR citations restored into module docstrings by PLAN-100's later split and now caught because PLAN-090 widened `_PR_REFERENCE_RE`. The parametrization half was **never started** and remains so |
| D6 — report the measured deltas | **unverifiable** | Point-in-time collected-count and coverage figures need a build, which is outside the orchestrator's boundary. Line-count claims are superseded by PLAN-100's rewrite of the slice layout |

## Metrics and Anomalies

- Slice size: 79,763 lines at run-01 baseline; **84,093 at HEAD** — inflated by PLAN-100's per-source
  fixture hoisting, which the budget rule does not count but `wc -l` does.
- **Anomaly — run 02 found and fixed a live blocking regression** in `finalize-step-era-stamp-fill`,
  outside its own subject. Correctly reported.
- The retired percentage line floor: −0.52% achieved against a −20% floor. The floor is retired epic-wide.

## Routing and Merge Behavior

- Review: run 02 closed seven named findings including a rule backtick-exemption fix on the marketplace
  side and two rule false-negative classes. Three CodeRabbit items were **rejected as new scope with
  reasons recorded** — a correct disposition.
- CI/merge: both runs landed.

## Reconciliation Actions

- [x] row `status` → `landed`
- [x] row `pr` stamped → `#1258, #1266`
- [x] row `landing` stamped → `landings/PLAN-050.md`
- [x] Open Defect opened — the **B3 prose-regression class** (shared with PLAN-060)
- [x] Open Defect opened — D3's per-directory criterion contradicted by PLAN-100's deviation

## Follow-Ups

- ⛔ **The prose-regression class is systemic, not local.** PLAN-090's matcher widening was correct and
  exposed citations both PLAN-050 and PLAN-060 recorded and declined to fix on the ground that the rule
  could not yet see them. **No plan in the epic owns re-sweeping an already-landed reduction slice
  against a later harness or rule change** — PLAN-090's surface is `marketplace/bundles/**` only and
  cannot touch `test/`. Staged as **PLAN-130**.
- ⛔ **D3's criterion is retired in fact but not on paper.** PLAN-100 chose per-source hoisting and said
  so; nothing amended D3. This is the same shape as the retired line floors, and it needs the same
  explicit retirement. Folded into **PLAN-140**'s brief.
- **D4's three survivors need a class-split authorization PLAN-100 as written forbids.** Owned by
  **PLAN-105** § D2, which decides to *keep* them and make the rule express the decision.
- **D2's 5 remaining `manage-status` builders and D5's parametrization half** stay open in this slice
  with no owner. Recorded in the epic's `## Open Defects`.
