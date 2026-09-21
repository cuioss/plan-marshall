# Landing Analysis: PLAN-32 — Truthful Build-Timeout Accounting

epic: plan-optimization
workstream: WS-10
pr: #972 (`8e77da80f`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.
>
> **This plan was resumed from a dead session** (the original died at 4-plan; outline survived).
> The resumption succeeded — it ran to a clean merge, validating the "resume, don't re-emit"
> call.

## Deliverable Fidelity vs Spec

Verified against merge commit `8e77da80f` (13 files, +624/-22). **2/2 shipped.** The spec's five
deliverables (D1–D5 as staged) collapsed to two as executed — a legitimate consolidation, and the
executed count is what is recorded here, not the spec's.

| Deliverable (as executed) | Verdict | Evidence |
|---|---|---|
| D1 — order the bounds + attach truthful timeout evidence | shipped | `cmd_run_common`'s timeout branch now parses the log in the **same try/except shape as the success branch** and attaches a zero-failure test summary + `tool_duration_seconds` — one edit covering **both** in-process and daemon-routed paths (`_build_shared.py` +29, `_build_parse.py` +16, `_build_format.py` +26). `execute_direct_base` gained a per-tool `min_timeout` floor (`_build_execute.py` +19, verified `:149,:174,:204`); the pytest tool pins the outer floor to **600s**, strictly above pytest's 300s backstop (`_pyproject_execute.py`, `run_config.py`) |
| D2 — regression + bound-ordering invariant | shipped | `test_timeout_truthful_evidence.py` (+282, NEW) for the killed-after-green case; `test_truthful_status_guard.py` (+103); `test_pyproject_cmd_parse.py` (+49). A **drift-guard test reads pyproject.toml live and fails if either bound moves to re-invert the ordering** |

**The design note held exactly.** The spec's key insight — that `subprocess.TimeoutExpired` fires
only on a genuine kill, so the fix is *"consult `test_summary` on the timeout branch"* rather than
*"don't say timeout"* — is precisely what shipped: the timeout branch mirrors the success branch's
parse. This is the exact mirror of PLAN-24, as the spec predicted, and confirms the scoped-split
resolution of the #909 contract (half (a), the shared terminal-status correctness).

- ⚠ **Minor narrative imprecision (not a defect):** the report said the floor pins in
  `pyproject_build.py`; it actually landed in `_pyproject_execute.py` + `run_config.py`.
  `pyproject_build.py` is not in the diff. Mechanism is correct; only the filename was off.
- **`MIN_TIMEOUT` stays 60** so Maven/Gradle/npm are bit-for-bit unchanged — the floor is
  pytest-scoped, exactly the "do not rework adaptive learning wholesale" constraint the spec set.

## Two Watch Resolutions (both armed at emit)

- **✅ Composed-manifest control — did NOT strand.** PLAN-32 was the clean control (manifest
  composed post-#962). `lessons-housekeeping` ran clean (0 removed, 1 adapted, 119 retained) with
  no stranded promotion. **This closes the `composed-manifest-snapshot` watch**: PLAN-28's fix
  works on freshly-composed manifests; the PLAN-24 stranding was purely the pre-#962 migration
  boundary, exactly as diagnosed. Retire the watch.
- **⚠ Bound-ordering class → n=3, and it did NOT fully generalize.** PLAN-32 fixed the
  subprocess-side bound (`min_timeout` floor > pytest backstop). But finding 2 below shows the
  **per-task Bash-envelope timeout has no analogous floor** — the same defect on the harness side.
  So PLAN-32's guard is subprocess-scoped and the class is **not closed**. Lesson
  `2026-07-22-00-001`. A follow-up is owed (not staged — see Follow-Ups).

## Metrics and Anomalies

- Tokens: **2M** · Duration: **1h41m** (cheapest WS-10 fix; the surviving outline saved the front half)
- Deploy: 1109 files → **0.1.1182**; 10 bundles synced, on-main executor regenerated
- Anomalies — three, all operator-flagged, all handled correctly:
  1. **`plan-retrospective` cut off by the weekly API limit** mid-pass — not a defect. Recorded
     `failed`, and the remaining deterministic steps continued rather than halting. **A deliberate,
     correct deviation** from the guard's halt contract: stopping there would have left the plugin
     cache unsynced and the on-main executor stale right after a merge. The step is recorded for
     retry. (See Follow-Ups — this is a real gap in the halt contract.)
  2. **Task envelope `bash_timeout_seconds` was 323s while verify took 393s** — the executor
     overrode to 900s rather than kill a passing build. **This is finding 2** (bound-ordering
     recurring on the harness side).
  3. **Q-Gate caught two real outline defects pre-code**: a second exhaustive whitelist in
     `_build_format.py` that would have silently dropped the new field on the TOON path, and a
     volatile learned timeout (232s → 216s on re-read) presented as ground truth. **Both fixed in
     one outline loop-back before any code was written** — Q-Gate earning its place.

## Routing and Merge Behavior

- **Review**: **0 actionable comments, 0 pr-comment findings.** Every catch was a *local* gate
  (Q-Gate outline loop-back, self-review). Continues the epic-long pattern: local gates outperform
  bots on this surface.
- **CI/merge**: 11/11 green, merged via queue, worktree + branch removed, `main` at `8e77da80f`.
- **Surface collisions**: none — despite PLAN-33/34/36 running concurrently and the plan-server
  epic's PLAN-05 being adjacent in `script-shared/build`. The adjacency I flagged did not bite.

## Reconciliation Actions

- [x] status.json `plans[]` updated (`shipped`, pr `972`, landing `landings/PLAN-32.md`)
- [x] epic.md queue row reconciled
- [x] **`composed-manifest-snapshot` watch RETIRED** — control passed
- [x] **Bound-ordering class → n=3**, not closed (harness-side floor missing; lesson `2026-07-22-00-001`)
- [x] ⚠ **PLAN-23 and PLAN-35 UNBLOCKED** — their adjacency to PLAN-32 is released now that it has
      landed. PLAN-23 still owes re-grounding (its cited `_build_cli.py` lines moved under #972's
      `_build_execute*` edits) + a verify-first clause. PLAN-35's mutual-exclusion with PLAN-36
      stands until PLAN-36 lands
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **⚠ Harness-side timeout floor is missing — the bound-ordering class is NOT closed** (n=3, lesson
  `2026-07-22-00-001`). PLAN-32 floored the subprocess bound; the **per-task Bash envelope**
  (`bash_timeout_seconds`) has no equivalent floor, and it under-set 323s against a 393s verify
  this very run. Same defect, different layer. Candidate for a follow-up — **not staged (queue is
  busy; four running + five staged)**. It is a sibling of PLAN-32, cleanly scopeable.
- **⚠ NEW — the finalize halt contract has no "deterministic tail" carve-out.** When
  `plan-retrospective` died on the API limit, halting per contract would have left the cache
  unsynced and the executor stale post-merge — strictly worse than continuing. The operator made
  the right call *against* the contract. That means the contract is wrong: a non-deterministic
  step failing should not block the deterministic post-merge tail (sync-cache, deploy-target,
  executor regen). Worth a spec — the halt guard needs to distinguish "must halt" from "record and
  continue the mechanical tail". Related to PLAN-36 D3 (completion-guard family) but distinct.
- **The retrospective owes a retry** — it never ran for #972, so PLAN-32 has no retrospective
  artifact. Low urgency; the landing record covers the orchestrator's needs.
