# Landing Analysis: PLAN-42 — Waiting-Standard Usage Is Runtime-Invisible

epic: truthful-signals
workstream: WS-01
pr: 988

> Landing record. Written from the operator's finalize paste (trusted narrative) and corroborated
> against merged commit `110a51367` on `origin/main` ("stamp the selected wait mechanism on every
> long-running wait"). The ship also settles the PLAN-42 spec-corruption dispute — see below.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — GATE: re-trace the two wait arms and where each is (not) logged | shipped-as-specified | Both arms enumerated and classified; the CI-wait arm and build-wait arm each got an emitter (below). |
| D2 — mechanism-selection record on the CI-wait / await arm | shipped-as-specified | `record_wait_mechanism` in `ci_base.py` + both GitHub/GitLab `cmd_ci_wait` handlers; closed vocabulary `seed_only/watch_tail/poll_fallback`; D4 poll_fallback regression test. |
| D3 — cover the build-wait arm | shipped-as-specified | `mechanism=` field on `_record_resolution` + `_audit_log`, drawn from the same shared closed `WAIT_MECHANISMS` vocabulary (`daemon_longpoll/in_process_fallback/no_build`). |
| (spec D4 — fallback-marker regression test) | shipped-as-specified | poll_fallback regression test on the CI arm pins the silent-degrade case. |
| Docs (spec had this folded in D2/D3) | shipped-as-specified | `await-long-running.md` / `waiting.md` corrected; `--dispatch` obligation documented. |

The spec's D1–D4 landed as the report's 3 deliverables + docs (D1 gate + D4 test folded into the two
arm-emitters). No deliverable dropped. Closed-vocabulary design (a single shared `WAIT_MECHANISMS`)
is a cleaner realization of the spec's per-arm-stamp intent — shipped-as-specified, not modified.

## Metrics and Anomalies

- Tokens: 2.9M. Duration: 1h59m. Lesson `2026-07-23-02-001`.
- Notable: **self-review caught a genuine contract-drift bug the plan itself introduced** — the
  fail-loud daemon-refusal path (which runs NO build) was mislabeled `in_process_fallback`. Fixed by
  adding a `no_build` vocabulary member — the honest label for "nothing ran." This is itself a
  truthful-signals fix inside a truthful-signals plan: a mechanism record that lied about what ran.
- The feature was **observed working live during its own finalize** (`mechanism=daemon_longpoll` on
  routed builds, `mechanism=seed_only` on the merge-queue CI wait) — a self-demonstrating landing.

## Routing and Merge Behavior

- Review: automatic-review + CodeRabbit. Unified triage: 2 CodeRabbit findings FIXED (mechanism
  return field only routed to the log sink, not the `cmd_ci_wait` return dict; + a seed_only test
  gap); 1 declined as a verified false positive (`dispatch=None` guard).
- CI/merge: green across 3 HEADs; rebased onto advanced main (#989/#990, no conflict); squash-merged
  via merge queue. deploy-target v0.1.1201.
- **Merge-gate decision (operator-confirmed):** CodeRabbit declined to re-review the rebased HEAD (a
  pure replay of already-reviewed commits onto newly-landed #989/#990, disjoint files). Operator
  chose merge-anyway — content already reviewed, merge queue re-tested CI. Recorded; not a defect.
- Collisions: none. PLAN-42 ran concurrent with PLAN-41/27/46 and rebased cleanly onto #989/#990.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — PLAN-42 → shipped, pr=988, landing=landings/PLAN-42.md
- [x] epic.md queue reconciled from status.json
- [x] Flagship-archetype instance (3) "waiting-seam invisible synchronous fallback" RETIRED — resolved #988
- [x] PLAN-42 spec-corruption discrepancy watch RESOLVED — the ship proves the clean spec ran
- [x] PLAN-45 unblocked (was sequenced behind in-flight PLAN-42); re-ground vs #988 before emit
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **Corruption dispute closed.** PLAN-42 shipped its real waiting-observability deliverables, not
  preference-emitter — confirming the on-disk spec was clean (verified 3 ways earlier). The memory
  note flagging corruption should be corrected. No spec fix was owed or performed.
- The `no_build` vocabulary addition (honest label for "nothing ran") is a clean data point for the
  truthful-status contract family (PLAN-24 #963 / PLAN-32 #972) and for PLAN-45's fail-closed design.
