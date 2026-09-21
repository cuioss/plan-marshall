# Landing Analysis: PLAN-13 — steward-provisioning-fail-closed

epic: plan-optimization
workstream: WS-03
pr: 950 — https://github.com/cuioss/plan-marshall/pull/950 (merged `e45c7ac8f`)

> Landing record for one shipped plan. Claims verified against ground truth: PR #950 confirmed
> `state: merged` via the CI abstraction; merge commit `e45c7ac8f` present on `origin/main`; the
> merged diff inspected (`git show --stat`) — 23 files / +824 independently corroborate all five
> deliverables (see the per-deliverable evidence column).

## Deliverable Fidelity vs Spec

The largest plan in the epic — 5 deliverables, held unsplit by recorded operator direction (2026-07-19,
fold-over-spawn chosen twice). It operationalizes ADR-009's fail-closed principle: two concrete verified
fail-silent-fresh sites fixed first (D1/D2), then the surface swept (D3) and the invariant encoded once
(D4), plus the separable upgrade-reload seam (D5). **All 5 shipped; neither split seam was needed.**

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — manifest resolver highest-version-wins, not first-hit-wins | shipped-as-specified | `generate_executor.py` (+153, `find_installed_manifest_path`) + `test_generate_executor.py` (+156, incl. the two-manifests-at-differing-versions regression) |
| D2 — prune superseded version dirs on regen (stop regenerated-every-run) | shipped-as-specified, **verified LIVE** | same-file regen/prune path + tests; **acceptance met against the real machine**: the session opened with preflight reporting `executor_action: regenerated` at identical versions (the exact defect), and after merge two consecutive preflights both report `fresh` |
| D3 — audit sweep of the provisioning surface | shipped-as-specified | new `marshall-steward/standards/provisioning-fail-closed-audit.md` (+111) — the written enumeration with fix-or-justify dispositions the spec required |
| D4 — encode the fail-closed invariant (not per-site patches) | shipped-as-specified | `_config_core.py` (+35) validated-write helper + `_cmd_system_plan.py` wiring + `test_provisioning_fail_closed_invariant.py` (+116) + ADR-009 adoc updated (`...fails_closed_with_an_explicit_unknown_state.adoc`) |
| D5 — harness-agnostic post-upgrade reload directive (runtime seam) | shipped-as-specified | `platform-runtime`: `contract.md` (+24), `runtime_base.py`, `_claude_runtime_impl.py` (+22), `opencode_runtime.py`, `platform_runtime.py`, SKILL.md + 4 test files; steward interface adapted (`marshall-steward/SKILL.md`, `upgrade-flow.md`) — resolves per `runtime.target` rather than hard-coding Claude, exactly as the operator constrained |

Net: **5/5 shipped-as-specified.** The split guard's two escape hatches (D3-tail, D5) went unused — the
operator's unsplit call held up. `adr-propose` correctly emitted **no new ADR** (ADR-009 already Accepted
and is the right home).

## Metrics and Anomalies

- Tokens: ~3.8M (largest in the epic — consistent with 5 deliverables)
- Duration: 2h35m worked / 13h54m wall / 11h18m idle. **Phase-6-finalize dominates: 1h4m worked against
  9h58m wall (8h54m idle) and 2.04M tokens** — >half the plan's tokens and ~72% of wall time in finalize.
- Anomalies:
  - **Two agent dispatches died mid-flight on API connection errors** (`lessons-capture`, `adr-propose`).
    Handled correctly per [[feedback_verify_disk_state_on_tool_contamination]]: disk state verified for
    both rather than trusting partial output, completed as recoveries with honest display details — no
    silent re-run, no marking-clean. lessons-capture had already recorded its lesson before dying.
    Same harness-instability class this epic tracks; not a plan-marshall defect.
  - **`marshal.json` reported stale and deliberately NOT touched** (`provisioned_version` 0.1.1152 vs
    installed 0.1.1159). This is the contract working as designed — marshal.json holds operator decisions
    and is never auto-mutated. **Operator action owed: run `/marshall-steward`** to refresh the stamps.

## Routing and Merge Behavior

- Review: **the local gates did the real work, not the bots.** Whole-tree module-tests caught a D5
  base-class test under-scope that per-task testing missed (a direct re-confirmation of the
  leaf-skips-pytest watch). Pre-submission self-review caught **3 genuine documentation defects across
  two rounds** (a missed rename cross-reference, a wrong architecture description in the new D3 audit doc,
  and nine drifted line citations → lesson recorded). Bots contributed nothing actionable: CodeRabbit
  passed clean; the only two Gemini comments were verified against the code and **refuted as false
  positives**. Sonar new-code issues: 0 (confirmed).
- CI/merge: all 24 finalize steps green; rebased onto origin/main, merged, cleanup complete; plugin cache
  synced (10 bundles) + executor regenerated (1100 files to `target/claude/`).

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — PLAN-13 → shipped, pr 950, plan_marshall_plan_id `steward-provisioning-fail-closed`, landing recorded
- [x] epic.md queue reconciled from status.json (WS-03 row 13)
- [x] Open Defect RESOLVED — API-Sheriff stale cache-root `dist-manifest.json` shadowing (folded as D1) moved out of Open Defects
- [x] Folded feature RESOLVED — single-command-upgrade reload directive (folded as D5) moved out of Open Defects
- [x] Watch RESOLVED — `executor_action: regenerated` on every run (folded as D2), verified live on the real machine
- [x] Watch RESOLVED — META-PATTERN steward provisioning fails-open/fails-silent (graduated to PLAN-13, now shipped)
- [x] resume_anchor updated — PLAN-18's {13,18} collision CLEARED; only the {17,18} collision remains
- [x] START-HERE block regenerated

## Follow-Ups

- **Operator action owed: `/marshall-steward`** — `marshal.json` provisioning stamps are stale
  (0.1.1152 vs installed 0.1.1159). Correct-by-design (never auto-mutated), but it should be refreshed
  at convenience. Tracked in the resume anchor as a non-plan item.
- **`leaf-skips-pytest` watch (lesson 22-001) reinforced again** — whole-tree module-tests caught a D5
  test under-scope that per-task verification missed. Third independent confirmation across the epic
  (PLAN-14, PLAN-16, now PLAN-13). Still a standing gap; **now the strongest verification-hardening
  candidate** alongside `step_record_mismatched_key`.
- **PLAN-18 unblocked by half** — the {13,18} manage-config + fail-closed-invariant collision is CLEARED
  by this landing (D4 encoded the invariant PLAN-18 would have collided with). PLAN-18's release now
  gates ONLY on PLAN-17's merge-queue-ruleset/`ci_base` coordination.
