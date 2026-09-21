# Landing Analysis: PLAN-01 — Rung 2 `marshalld` build server

epic: plan-server
workstream: WS-01
pr: #933 (squash-merged to main via merge queue, 2026-07-18)

> Landing record for one shipped plan. Lives at `landings/PLAN-01.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact.

## Ground-truth verification

- PR #933 merged: **corroborated** — `origin/main` carries `35a293ee6 feat(build-server): implement marshalld build daemon (#933)` (squash form).
- README merge-both vs upstream #928: **corroborated** — `36e05634f docs(user): add Windows / WSL setup guide (#928)` is also on main, ahead of #933, consistent with the reported conflict resolution.
- Deliverable-level fidelity below is taken from the operator's trusted landing narrative + the archived plan at `.plan/local/archived-plans/2026-07-18-plan-server-core/`; not independently re-diffed line-by-line (operator narrative is trusted; the two concrete PR claims were checked).

## Deliverable Fidelity vs Spec

Spec: `plans/plan-server-core.md` (11 deliverables per the epic 00-README Rung 2 row).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Wire protocol / registry / schema | shipped-as-specified | operator narrative; archived plan |
| marshalld daemon core — double-fork→PID 1, asyncio Unix socket, verifier/scheduler/supervisor/journal | shipped-as-specified | hard constraint (double-fork) honored; #933 diff |
| `manage-build-server` control skill (install/upgrade/start/stop/drain/status/register/unregister) | shipped-as-specified | operator narrative |
| `build-server-client` skill + change-ledger `kind=job` persistence | shipped-modified | job_id persistence realized as change-ledger `kind=job` extension — spec-driven scope expansion beyond the bare "write job_id to ledger" line |
| build-execute routing on ONE machine-global queue file; `build_queue.py` refactored to shared reader/writer | shipped-modified | operator decision: single queue file serves daemon + fallback (neither retired outright nor kept as a separate limiter — the spec's "retire-what-you-replace" resolved as refactor-to-shared) |
| `await-long-running.md` seam → pointer into client skill | shipped-as-specified | operator narrative |
| phase-1-init preflight gate (registry read + ping + ask-to-start, every outcome logged) | shipped-as-specified | operator narrative |
| README + installation WSL2 machine-requirement docs | shipped-as-specified | merged around upstream #928 |
| `doc/concepts/build-server.adoc` | shipped-as-specified | operator narrative |
| `doc/developer/build-architecture.adoc` (architecture.md → as-built AsciiDoc) | shipped-as-specified | operator narrative |
| Acceptance suite (all § Acceptance items) | shipped-as-specified | whole-module tests + coverage green |
| **S2 cwd-escape hardening** | added-unplanned | finalize security-audit found the verifier checked `exec_path` but not the independently-settable `project_path` used as build cwd; fixed pre-merge with regression tests; lesson `2026-07-18-17-001` |

Verdict: **11/11 spec deliverables shipped** (2 shipped-modified with recorded rationale), plus 1 unplanned security fix. No deliverable dropped.

## Metrics and Anomalies

- Tokens: 12.1M total across the plan.
- Duration: 6h33m worked.
- Anomalies: light-lane mis-route corrected at intake (escalated to deep/full per the spec's explicit posture); zero harness kills reported. Finalize security-audit earned its keep (real S2 cwd-escape caught pre-merge).

## Routing and Merge Behavior

- Review: gemini pruned from `enabled_bots` (sunset); full auto-finalize. 0 new-code Sonar issues; whole-tree plugin-doctor clean; CI 11 checks green.
- CI/merge: squash-merged via the merge queue (the SQUASH re-provisioning from #923's landing held). README conflict vs upstream #928 (Windows/WSL guide) resolved merge-both.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-01 → status `shipped`, pr `#933`, landing `landings/PLAN-01.md`
- [x] epic.md Ordered Queue row reconciled from status.json
- [x] Open Defects retired: merge-queue MERGE-vs-squash (held squash), `plan_id=null` build-queue bypass (subsumed by the daemon-owned queue rewrite), inherited worktree-resolution defects (absorbed into the Rung 2 queue/registration path) — verify residue in close
- [x] Watches retired: WSL2 reaper-escape re-run (rode the plan); token/finalize-idle framing guard (plan stayed on-thesis)
- [x] resume_anchor updated → close
- [x] START-HERE block regenerated

## Follow-Ups

- **Daemon ships dormant / opt-in** — nothing changes until a project runs `manage-build-server register`. The meta-project itself is NOT enrolled, so current build behavior (incl. leaf-backgrounding) is unchanged. Not a defect; a deployment note. → carried into `history.md` as the standing state.
- Lesson `2026-07-18-17-001` (verify EVERY client-settable execution-path field, not just the obvious one) captured in the global lessons store. → no orchestrator action.
- Names CONFIRMED (no rename): `marshalld` / `build-server-client` / `manage-build-server`. → 00-README Naming section already reconciled by operator.
