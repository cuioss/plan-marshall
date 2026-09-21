# History: operator-ux — Operator UX: reduce interaction friction across the plan-marshall lifecycle

> Frozen record of the closed epic. Written by the `close` verb 2026-09-16; the tree remains on disk as the audit record (close freezes, never deletes).

- Epic: operator-ux (opened 2026-09-01, closed 2026-09-16)
- Final phase: closed. Terminal queue state below rendered from `status.json` at close.

## Vision as pursued

Reduce interaction friction across the plan-marshall lifecycle: resolve skill domains without over-prompting (WS-01), set autonomy defaults that match operator intent (WS-02), sharpen prompt quality (WS-03), establish how plan-marshall talks — language, vocabulary, output volume (WS-04), remediate user-facing sites (WS-05), add a persisted interaction-mode preference (WS-06). WS-07 (persona-loading-structure) was chartered but never decomposed — see closing rationale.

## Queue outcome per plan (10/10 shipped, 0 parked, 0 dropped)

| Plan | Workstream | PR | Landing |
|------|------------|----|---------|
| PLAN-01 domain-over-provision | WS-01 | #1380 | landings/PLAN-01.md |
| PLAN-02 domain-glob-seeding | WS-01 | #1406 | landings/PLAN-02.md |
| PLAN-03 domain-post-plan-narrow | WS-01 | #1422 | landings/PLAN-03.md |
| PLAN-04 autonomy-gate-defaults | WS-02 | #1437 | landings/PLAN-04.md |
| PLAN-05 prompt-standard-and-doctor-rule | WS-03 | #1378 | landings/PLAN-05.md |
| PLAN-06 user-language-and-vocabulary | WS-04 | #1382 | landings/PLAN-06.md |
| PLAN-07 output-volume-standard | WS-04 | #1387 | landings/PLAN-07.md |
| PLAN-08 remediate-user-facing-sites | WS-05 | #1447 | landings/PLAN-08.md |
| PLAN-09 interaction-mode | WS-06 | #1502 | landings/PLAN-09.md |
| PLAN-10 always-on-is-not-a-resolve | WS-01 | #1391 | landings/PLAN-10.md |

Per-plan fidelity, metrics, and routing detail live in `landings/PLAN-NN.md`. Final drain (2026-09-16): 14/14 PLAN-09 inbox messages consumed — 4 promoted to the global lessons corpus (`2026-09-16-17-001`…`-004`), 9 discarded with reasons, landing recorded as reconciled-duplicate.

## Decision record (summary)

Full append-only record in `logs/decision.log`; curated narrative in `epic.md` § Decisions. Load-bearing rulings: `parallelization_scope: 2`; user-communication as a new unconditional standards file (PLAN-06/07); finalize-machinery debt routed to a separate epic (not folded here); WS-07 admitted to this epic as a deliberate authorship exception; BCP-47 value standard declined; derive-vs-collapse enforcement-matrix fork reserved to the operator.

## Carried-forward leads (not silently dropped)

1. **WS-07-persona-loading-structure undecomposed.** Charter exists (`workstreams/WS-07-persona-loading-structure.md`); zero plans staged. The decompose-vs-close fork was decided as close by the operator on 2026-09-16. A future epic may adopt the charter as decompose input.
2. **`interaction_mode` consumer wiring.** Persisted knob with mode-to-behaviour mapping doc; only the phase-1 ambiguous-domain branch consumes it (`epic.md` Open Defects). Needs operator scoping.
3. **Enforcement-matrix derive-vs-collapse fork** (`epic.md` Open Defects) — still owed to the operator.
4. **PLAN-03 `domain_narrow_report` unwired consumer** (`plan-marshall/workflow/planning-outline.md`) — recorded in `epic.md` Open Defects.
5. **Finalize-machinery transfers** — three `phase-6-finalize` Open Defects plus recurring corpus lessons were designated for the separate finalize-machinery epic; see `epic.md` Open Defects and the Watches section for the transfer list.
6. **Open `test-quality` analysis debt** noted in earlier anchors (PLAN-110/PLAN-130 landings owed reconciliation in that epic, not this one).

## Closing rationale

All 10 staged plans shipped; inbox fully drained (0 queued, 96 archived); no launched or running plans remain. The operator chose close over WS-07 decomposition. The epic's purpose — the six shipped workstreams — is complete; the residue above is recorded as leads for future epics, not as retained queue.
