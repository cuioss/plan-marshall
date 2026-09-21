# Landing Analysis: PLAN-06 — the pm-plugin-development authoring surface is target-aware

epic: multiplattform
workstream: WS-03
pr: #1456 (https://github.com/cuioss/plan-marshall/pull/1456)

> Landing record for one shipped plan. Lives at `landings/PLAN-06.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact.

Drained from `inbox/authoring-surface-target-awareness-001.md`, corroborated against the merged
diff (`8fc353b6e`), the CI abstraction, and the change ledger. **45 files — the largest single
landing in this epic.**

## Deliverable Fidelity vs Spec

The hand-off did not enumerate deliverables, so fidelity is read from the merged diff against the
spec's five:

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| Generator emits target-resolved frontmatter | **shipped** | `plugin-create/scripts/cmd_generate.py`, `cmd_validate.py`; `test_validate_generate.py`. |
| Validators / fix payloads stop carrying undeclared Claude enums | **shipped** | `plugin-doctor/assets/fix-templates.json`, `_cmd_apply.py`, `_cmd_verify.py`, `_doctor_analysis.py`; `test_fix.py`, `test_cmd_verify.py`. |
| The frontmatter standard stops stating Claude rules as *the* standard | **shipped** | `plugin-architecture/references/frontmatter-standards.md` — ✅ **this absorbs PLAN-11 residue F1** (`frontmatter-standards.md:445`). |
| Layout/settings literals route through the layout helpers | **shipped** | Nine `_analyze_*.py` analyzers plus `_dep_index.py`, `doctor-marketplace.py`, `_plugin_pin_trap.py`. |
| Rule-pack declaration for what stays Claude-specific | **shipped** | `plugin-doctor/references/rule-provenance.md`, `rule-catalog.md`, `fix-catalog.md`, `safe-fixes-guide.md`, `verification-guide.md`, `commands-guide.md`. |

✅ **PLAN-11 residue F2's `plugin-doctor` / `plugin-architecture` half is absorbed** — both surfaces
are in the diff. ⛔ Its `plan-retrospective` half is **not**, and remains in no staged spec's
declared surface. That half is still unowned.

## ⭐ Zero undeclared paths across 45 realized — but read the mechanism, not just the number

Realized **45**, declared **11** entries, **0 undeclared**, 1 declared-but-unrealized. The series
now reads: PLAN-11 **15** → PLAN-10 **19** → PLAN-21 **0** → PLAN-22 **2** → PLAN-06 **0**.

⚠️ **PLAN-06's zero and PLAN-21's zero are not the same achievement, and conflating them would draw
the wrong lesson.** PLAN-21 declared three exact files and touched exactly those three — precision.
PLAN-06 declared two **bundle-wide recursive globs** (`pm-plugin-development/**`,
`test/pm-plugin-development/**`) and touched 45 files inside them — coverage. A glob that broad
*cannot* under-declare within its bundle, so its zero is structurally guaranteed rather than earned
by sweeping.

That is a legitimate declaration for a bundle-wide sweep, and it is the right shape for this plan.
But it buys the zero with **over-serialization**: while PLAN-06 was live, any sibling touching
anything anywhere in `pm-plugin-development` was blocked, whether or not the two would truly have
collided. The trade is coverage against precision, and both plans made the correct choice for their
own shape. ⛔ The open under-declaration class — a spec declaring a **split** or a **prose
consumer-set** — is untouched by either result.

## ✅ The verify-at-outline carry resolved cleanly

`platform-runtime/**` was PLAN-06's one declared-but-unrealized entry. It is exactly the entry
carried into the emit as verify-at-outline, because PLAN-10 had changed 8 files under it after
PLAN-06's claims were stamped. The plan re-derived at outline and concluded no D-work needed that
surface. ⭐ **A declared entry that goes unrealized after a recorded re-derivation is the carry
working**, not an over-declaration — the same distinction PLAN-10's landing drew for its own nine
unrealized entries.

## ⛔ The hand-off carried NO verification section — and every prior landing in this lane did

This report states the merge, the landing emission, the worktree cleanup, the report path and the
condition-5 reviewer disclosure. It states **nothing about the build gate**: no test count, no
verify statement, no verifier-round report. PLAN-21 reported "20736 tests", PLAN-10 "25254", PLAN-22
"25270" — this one reports nothing.

**The gate did run and it was green.** Corroborated independently from the change ledger: full
`verify` at `2026-09-09T08:46:03Z`, `exit_code: 0`, **25493 tests** (plus a `quality-gate
pm-plugin-development` at `08:58:22Z`, also green — its `tests_run: 0` is correct for a
compile-and-lint gate and is not a finding). Fifty-six build entries were recorded for this
worktree, so the run was heavily gated throughout.

⛔ **The finding is the reporting, not the verification.** Had the ledger been unavailable — which
is precisely the situation of any reader who is not on this machine — the drain could not have
established that the gate ran at all. This is the standing *"the OpenCode lane drops a spec's
report-in-the-inbox-message obligation"* defect recurring in a new and more consequential place:
previously the lane dropped `total_tokens`, a fact nobody gates on; here it dropped the **gate
result itself**.

## Metrics and Anomalies

- **Tokens: not reported.** `landing-check` → `complete: false`, `missing_keys: [total_tokens]`.
  **10-for-10 on the OpenCode lane.**
- **Test count 25270 → 25493 (+223).** Stable growth; the closed instability watch stays closed on a
  fifth reading.
- **Post-merge verify — FIFTH consecutive substantively-clean case.** Verify `08:46:03Z`, merge
  `09:35:48Z`; merge parent `9853a7aba` (#1455) landed `00:58:37Z`, nearly eight hours earlier, and
  nothing landed in the window. Verified tree equals merged tree.

## Routing and Merge Behavior

- **Review:** `coderabbitai` and `cuioss-review-bot` both reviewed; no outstanding findings.
  `sourcery-ai` rate-limited on the per-developer budget (~5d5h remaining) — **optional reviewer,
  correctly disclosed as a shortfall rather than silently omitted**, and correctly not treated as a
  merge-gate failure.
- **CI/merge:** merged via the merge queue as `8fc353b6e`, confirmed an ancestor of `origin/main`.
  Branch prefix `feature/` — canonical. Worktree removed, branch deleted, main fast-forwarded.

## Reconciliation Actions

- [x] row `status` → `landed`; `pr` `#1456`; `landing` `landings/PLAN-06.md`; `plan_marshall_plan_id` `n/a`
- [x] epic.md narrative reconciled from status.json
- [x] Open Defect — landing incomplete (`total_tokens`), folded as the 10th instance
- [x] Open Defect updated — the lane's report gap now reaches the GATE RESULT, not just tokens
- [x] PLAN-11 residue F1 and F2's plugin-doctor/plugin-architecture half — CLOSED
- [x] resume_anchor updated; START-HERE and Ordered Queue regenerated

## Follow-Ups

- **F1** ⛔ PLAN-11 residue F2's **`plan-retrospective`** reference-integrity half is still in no
  staged spec's surface. Two plans remain (PLAN-07, PLAN-12); if neither absorbs it, it needs a home
  before WS-03 closes.
- **F2** ⛔ **PR #1445 is still open**, four landings after PLAN-21 raised it and two after PLAN-22
  reproduced the defect it documents.
