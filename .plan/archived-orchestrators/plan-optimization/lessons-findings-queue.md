# Consolidated plan queue — findings + lessons (aggregated for parallelism)

> **✅ WAVE 1 COMPLETE (2026-07-17): every plan in this doc (P1–P9 + SS) has SHIPPED.** This file is
> now an archived record of the first aggregation. **WAVE 2** — the plans distilled from the open
> defects wave 1 surfaced — lives in **[`HANDOVER.md`](HANDOVER.md) §4** as 4 startable plans
> (`manifest-compose-gaps`, `finalize-step-integrity`, `leaf-validator-yield`, `P7 docs-contract`)
> plus items handed to the plan-server epic. The full shipped detail is in
> [`HISTORY-snapshot-4-queue-wave.md`](HISTORY-snapshot-4-queue-wave.md). Read HANDOVER §4, not this
> table, for what to run next.


**Built 2026-07-16** from (a) HANDOVER §5 open-defect findings accumulated this session and (b) a full
review of the 96 active plan-marshall lessons (`manage-lessons aggregate` + manual clustering). This
is the actionable queue; HANDOVER §4 holds the standing/running plans (plan-server epic,
marshall-orchestrator, ci-pr-safe-merge).

**✅ ALL SPEC DOCS WRITTEN 2026-07-16.** Every P-plan and the design-first SS below is now an
executable `plans/…` document (each grounded against real source by a dedicated writer pass; several
writers corrected the finding's own premise — noted per row). Run any with
`/plan-marshall task="implement .plan/plan-optimization/plans/<doc>"`. **Premise corrections surfaced
during authoring (act on these, not the original finding text):** P8's knob is `pr_merge_strategy`
not `pr_strategy`; P6 found `merge_lock` already resolves and owasp is already 2025-numbered
(confirm-and-drop); P4 confirmed `17-006` and `13-12-001` are retire-only; SS found orphaned *files*
are already swept (the real gap is deleted-symbol survivors inside still-present files).

## Aggregation & parallelism rules applied

- **Plans are as large as sensible**, aggregated by **same component / same phase / same error-class**.
  A plan bundles every lesson+finding on one surface so the fix lands once.
- **Parallel groups**: each plan is tagged with a GROUP. **Different GROUPs touch disjoint file
  surfaces and may run concurrently.** Same-GROUP plans share files → serialize or coordinate.
- **Excluded** (deliberately not queued): lessons marked "expected false-positive, resolve accepted"
  (`28-17-001`, `16-12-001`, `21-11-001`, `28-17-002` are Q-Gate/refine false-positive-accepts, not
  bugs); one-off already-shipped-context lessons; anything an outline should first confirm is
  already fixed (flagged **verify-not-shipped** below).

## The queue

| Plan | GROUP (parallel key) | Surface (component/phase) | Absorbs (lessons + §5 findings) | Error class |
|------|------|------|------|------|
| ~~**P1 · finalize-commit-integrity**~~ | ✅ **SHIPPED #914** | — | 5 arms shipped as CODE guards: remote-parity push re-fire + clean-tree 5→6 post-condition (9-for-9 class closed) + handshake-drift auto-resolve + `lessons-capture` `mutates_source:true` + worktree-remove move-back guard. Retired 5 folded lessons; +2 new. **Arm 6 freshness-gate SPLIT OUT** (own follow-up / fold into P2). | — DONE |
| ~~**P2 · finalize-triage-unification (=UT)**~~ | ✅ **SHIPPED #920** | — | Per-signal FIND-gate on each producer's own `_ci_barrier.py` arm (failed arm still FINDs = #572 deadlock fix) + ONE dispatcher-owned unified triage over pr-comment∪sonar-issue; 13 tests reproducing #572. Cross-producer dedup deferred; `_ci_barrier.py` read-only. Retired `17-010`; new `17-001` (leaf edited MAIN checkout). **⚠ did NOT absorb the parked follow-ups** (P4-C1 aspect-wiring, P1 arm-6, plugin-doctor whole-tree, prepare_execute) — now orphaned. | — DONE |
| ~~**P3 · architecture-resolution**~~ | ✅ **SHIPPED #917** | — | 6 deliverables: Failsafe-IT routing + unified `route_matches` (nested-pom classify) + domain-affinity module ties + `build.maven.profiles.mutating` signal + `pm-documents` impl-profile skill set + stale-notation retire-only. Retired `16-001`/`17-011/12/13`/`06-00-001`/`09-09-001`; new `2026-07-17-09-001`. | — DONE |
| ~~**P4 · manage-execution-manifest**~~ | ✅ **SHIPPED #916 (⚠ C1 partial)** | — | Gaps A (enhancement change_type)/B1 (verb routing)/B2 (marshal-authoritative steps)/C1 (negation-phrase classifier) landed; retired `17-001/02/06`+`13-12-001`. **⚠ C1 fixed the classifier ONLY — the phase-1→phase-4 aspect wiring survives, so docs-only plans STILL build. Wiring follow-up → HANDOVER §5.** | — DONE except C1 wiring |
| ~~**P5 · consumer-domain-standards**~~ | ✅ **SHIPPED #918** | — | 5 standard docs updated as authoring rules: cui-http resolver-adoption + secure-default-flip; cui-http-testing MockWebServer IT self-checks; cui-logging CWE-117 every-channel sanitization; cui-testing `@TypeGeneratorMethodSource` reflective-access; asciidoc pre-submission self-check pair. Removed 4 folded lessons (`17-017/018/019/020`); retained 4 partially-folded. **⚠ meta-irony: the catch-at-authoring plan itself took 11 review-bot corrections — surfaced in quality-verification-report.md, NOT recorded as a lesson.** | — DONE |
| ~~**P6 · small-tooling-batch**~~ | ✅ **SHIPPED #921** | — | 4 disjoint fixes: D1 ADR width-agnostic numbering (`17-005`); D2 build-npm `--warning-baseline` exit-authority (`17-014`); D3 manage-lessons cross-repo wrong-store REFUSAL guard (the lesson-store trap — structural fix); D4 test-compile wired into `cmd_verify` = CI gates mypy over `test/` (`15-12-001`). Dropped merge_lock/owasp (done). Retired 3 lessons; folded `12-001`. item 6b (2 dormated-audit doc chores) DEFERRED — no anchor, likely already shipped #799 (verify-then-close). Follow-up PR #924 open. | — DONE |
| **P7 · docs-contract-consistency** | DOCS | phase-6-finalize docs + manage-config knob docs + persona standards | §5 `loop_back_without_asking` HALT-not-ASK contradiction (`SKILL.md:894` vs `:1058`); `*_without_asking` family inconsistency; stale `auto_merge_after_ci` docs (`configuration.adoc`); diagnosis-discipline standard (seed `16-006`); upstream-availability consumer-upgrade warn | doc/contract drift; mostly no-code |
| ~~**P8 · merge-queue-squash-reconcile**~~ | ✅ **SHIPPED #919** | — | ruleset method parameterized from `pr_merge_strategy` (squash→SQUASH) + enable-time reconcile + probe seam + merge-routing warn; self-validated live (reproduced #445 legibly). **⚠ Re-provision queue via steward to activate.** | — DONE |
| ~~**P9 · metrics-corpus-integrity**~~ | ✅ **SHIPPED #922** | — | D1 phase-total↔dispatch-boundary reconcile (fixes under-count) + D2 inline 6-finalize attribution (fixes inline=0) + D3 loop-back monotonicity guard (fixes timestamp corruption) + D5 era-stamp; D4 corpus caveat applied out-of-PR to gitignored `gen.py`/01/02. Dogfooded clean on own record-metrics. | — DONE |
| ~~**SS · survivor-sweep**~~ | ✅ **SHIPPED #913** | — | ADR-007 authored: **decided NO gate** (orphaned files already swept; residual in-body cross-file survivors sit at dev-time/self-review, not CI — `target/` gitignored). Lessons folded into `17-020`. Archived. | — DONE |

## Parallelization plan

```
**✅ ENTIRE AGGREGATED QUEUE (WAVE 1) SHIPPED: P1#914/P2#920/P3#917/P4#916(C1 open)/P5#918/P6#921/P8#919/P9#922 + SS#913.** The orphan pile this table's plans left behind was CONVERTED into WAVE 2 → see [`HANDOVER.md`](HANDOVER.md) §4 (`manifest-compose-gaps`, `finalize-step-integrity`, `leaf-validator-yield`, P7; credentials/build-maven bugs → plan-server epic). Rung 1 SHIPPED #923; Rung 2 (marshalld) unblocked — plan-server epic, tracked separately.
FINALIZE group (share phase-6 files):   P1 ✅ SHIPPED #914 → P2 now UNBLOCKED (may absorb P1's arm-6 freshness-gate split-out)
DOCS:                                    P7 lightly touches phase-6 SKILL.md → sequence AFTER P1/P2
DESIGN-FIRST (independent):              SS (survivor-sweep) — ✅ SHIPPED #913 (ADR-007: no gate)
```

- **P5 (STANDARDS) is the cleanest parallel candidate** — pm-dev-java-cui / pm-documents bundles are
  fully disjoint from every plan-marshall workflow plan. Start it alongside anything.
- **P1 and P2 both edit phase-6-finalize** — run serially or fold into ONE `finalize-hardening` plan
  (arguably the right call: same phase, overlapping files, related error classes). Decide at outline.
- Up to **5 concurrent** (P3/P4/P5/P6/P8) is safe if the operator wants max throughput; the
  build-server/harness-kill caveats do NOT gate this (concurrency was falsified as the kill trigger).

## Cross-refs into the standing queue (HANDOVER §4, not re-listed here)

- **plan-server epic** (`.plan/plan-server/`): BK shipped #912; Rung 1 SHIPPED #923; Rung 2 unblocked. Absorbs
  the build-timeout **residuals** `16-003` leaves (adaptive-timeout 1.25× floor, `--timeout`-not-an-
  override, `plan_id=null` queue bypass) — these are NOT in P-plans above; they belong to Rung 1.
- **UT** = P2 above (same plan, spec already staged).
- **TT** (terminal-title): may be dissolved by BK #912 — re-scope at its outline before running.
- **SS** (survivor-sweep, §4): design-first, WT residual.
- **marshall-orchestrator** (running): its dogfood (D10) will ingest THIS queue + HANDOVER.

## Lifecycle

Spec docs are written (see the `plans/…` column). Up to **6 disjoint plans can run concurrently**
(P3∥P4∥P5∥P6∥P8∥P9); P1→P2 serialize (or fold into one finalize plan at outline); P7 follows P1/P2;
SS is independent design-first. On each landing, retire the absorbed lessons (via the plan's
`finalize-step-lessons-housekeeping` / `manage-lessons remove --force`) and strike the row here + the
matching §5/§6 finding in HANDOVER. **Outline-gate reminder — some absorbed items are already
confirm-and-drop** (P4: `17-006`/`13-12-001`; P6: `merge_lock`, owasp; P3: stale-notation pair): the
plan's job for those is to verify-then-retire, not to implement.
