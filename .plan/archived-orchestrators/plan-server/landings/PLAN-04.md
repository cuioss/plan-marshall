# Landing Analysis: PLAN-04 — Explicit execution_mode on the build-server client API

epic: plan-server
workstream: WS-01
pr: #956 (squash-merged via merge queue, 2026-07-21)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a
> lead, never a fact.

## Deliverable Fidelity vs Spec

The spec listed 6 deliverables; the plan shipped them as 2 deliverable-groups, exactly as
the spec's own split-guard rationale anticipated (D2–D5 are thin consequences of the D1
API change; D6 is D1's doc surface). All six spec items are accounted for. Ground truth =
merge commit `1c402964a` on `origin/main` (git log + `git show --stat`).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 `execution_mode` param (auto/in_process/daemon) on the routing seam | shipped-as-specified | `1c402964a` adds the param to `script-shared/scripts/build/_build_execute_factory.py`; `auto` byte-identical to prior registry+ping+fallback |
| D2 `in_process` path pinning (no submit, foreground) | shipped-as-specified | same commit; `in_process` pins foreground unconditionally |
| D3 `daemon` fail-loud semantics | shipped-as-specified | same commit; `daemon` fails loud with a named reason on refusal/absence |
| D4 requested-vs-resolved routing traceability | shipped-as-specified | console line + `decision.log` entry extended to record requested AND resolved mode |
| D5 test conversion to `execution_mode=in_process` | shipped-as-specified | `test/plan-marshall/build-server/test_build_execute_routing.py` declares `in_process`, now daemon-state-independent |
| D6 build-architecture diagram rework + SVG | shipped-as-specified | `doc/developer/build-architecture.adoc` reworked (+36/−3); NEW `doc/resources/diagrams/build-execution-mode-routing.svg` per `pm-documents:ref-svg-diagrams`. Owning-doc path CONFIRMED (`build-architecture.adoc`, not build.adoc/marketplace-build.adoc) |

Surface note: the spec's Expected Surface named `build-server-client/**` and
`manage-locks/build_queue.py`; the change actually landed entirely in
`script-shared/scripts/build/` (`_build_execute_factory.py` + `_build_cli.py`) — the seam
the spec correctly identified. `build-server-client/**` and `build_queue.py` were NOT
touched. Minor prediction drift, not a defect.

## Metrics and Anomalies

- Tokens: 2.97M total.
- Duration: 1h52m worked / 9h17m wall-clock — the ~7.5h gap was idle CI waiting, notably a
  ~35-min CodeRabbit org-level review rate-limit that reported a non-required failing check
  across every CI run.
- Anomalies:
  - **One real in-plan bug, caught by a review bot in the plan's OWN deliverable-4 code.**
    Gemini flagged that the `auto` + daemon-incompatible path left `fallback_reason=None`,
    so the audit log recorded `reason=None`. Loop-back to phase-5, TASK-004 fixed it
    symmetrically, re-verified, merged. Lesson captured + promoted into `ref-code-quality`.
    (Matches the standing rule: a sunset/pruned bot can still post a valid finding.)
  - CodeRabbit rate-limit accepted as a bot condition, not a code defect — the required
    `verify/conclusion` check was green on every run; operator chose proceed-and-merge.

## Routing and Merge Behavior

- Review: Gemini (1 valid actionable finding, fixed via loop-back) + CodeRabbit
  (rate-limited, non-required check red — accepted as bot condition). 2 reviewers compared
  in review-retrospective.
- CI/merge: green (`verify/conclusion` always green); squash-merged via merge queue.
- Surface collision: the spec sequenced PLAN-04 AFTER PLAN-03 on a predicted
  `build-server-client/**` overlap. In the event PLAN-04's real surface was
  `script-shared/`, so that specific overlap did not materialize — but sequencing was still
  correct on the genuine dependency (D4 builds on PLAN-03's logging seam). No rebase
  conflicts.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-04 → shipped, pr=#956, landing=landings/PLAN-04.md
- [x] epic.md queue row PLAN-04 reconciled to shipped
- [x] Open Defect (test-hermeticity / 8 spurious failures) RESOLVED via D5 — tests now
      declare `execution_mode=in_process`, daemon-state-independent
- [x] Watch (worktree-container routing UNOBSERVED) SURVIVES — PLAN-04 ran in-process
      (daemon deliberately not started), so it did NOT settle the watch; re-pointed to the
      owed operator daemon restart
- [x] Owed-operator daemon-restart entry updated: now on #956 code (was #949)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **Sub-mechanism of the 8 failures NOT reported.** The spec asked the plan to state, in
  this landing, whether the failures were path-selection or contract-shape mismatch (sync
  in-process result vs the daemon's `job_id`/`queued` response). The landing narrative did
  not settle it. Practically moot — the tests pass under `in_process` regardless — but the
  contract-equivalence question (should the two execution paths be contract-equivalent?)
  remains genuinely open and un-investigated. Recorded as a low-priority watch; stage a
  plan only if the question resurfaces.
- **Worktree-routing proof STILL owed** — gated solely on the operator daemon restart on
  #956 code + one worktree build; see the Watch and the owed-operator defect. This is the
  epic's last substantive open thread.
- Outside the epic surface (advisory only, not staged here): (1) uncommitted
  lessons-housekeeping edits on `main` (ref-code-quality + persona-module-tester standards)
  need a follow-up `chore/` PR — branch protection blocks direct push; (2) `marshal.json`
  stale (0.1.1152 provisioned vs installed advanced by this plan) — `/marshall-steward` +
  session restart to reconcile.
