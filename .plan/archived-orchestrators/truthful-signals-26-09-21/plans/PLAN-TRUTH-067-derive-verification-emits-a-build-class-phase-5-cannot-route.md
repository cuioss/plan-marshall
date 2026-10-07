# PLAN-TRUTH-067: `derive-verification` emits a `build_class` phase-5 cannot route

epic: truthful-signals
workstream: WS-01

> Staged plan spec — ready for `/plan-marshall` hand-off. Staged at the 2026-08-08 inbox drain
> from routed lessons cluster C01 (`lessons-handling-26-08-08-01-001`), the flagship dedup
> result of that run.

## Objective

`architecture derive-verification` emits compile / test-compile `build_class` commands that
phase-5's per-task routing cannot map to a valid canonical step, so `manage-execution-manifest`
compose fails with `unresolvable_step verify:compile`. The emission reports `status: success`
while producing an unroutable command — the failure surfaces two components downstream, at
compose time, where its cause is no longer visible. This plan makes the emitter incapable of
emitting a `build_class` that has no phase-5 route.

## Deliverables

1. Constrain `derive-verification` to emit only `build_class` values that have a registered
   phase-5 canonical route — an unroutable class is a **failure at emission**, not a `success`
   payload that breaks compose later.
2. Make the emitter's `status` honest: a payload containing an unroutable command must not
   return `status: success`.
3. Give compose's `unresolvable_step` error the provenance of the command it could not route
   (which emitter produced it, under which `build_class`), so the next instance is diagnosable
   at the point of failure.
4. A matched control pair in tests: a routable class composes; an unroutable class is refused
   at emission and never reaches compose.

Four deliverables — under the split guard.

## Claim Labels

- OBSERVED (five-way duplicate, the dedup evidence): five lessons filed over four days against
  **three** different components are one defect — `2026-07-28-15-001` and `-15-002`,
  `2026-07-28-19-001`, `2026-07-28-20-001`, `2026-07-28-21-001`. Each was filed from the side
  it happened to fail on, which is why the duplication went unnoticed. Cluster reports **8
  corpus instances** in total.
- OBSERVED: the emission reports `status: success` while carrying an unroutable command —
  recorded in `2026-07-28-19-001`.
- ⚠ **ALL OF THE ABOVE IS SECOND-HAND.** These are corpus lesson texts relayed by the
  lessons-handling run; **no symbol was read by this epic**. The five wordings are five
  *reports* of a defect, not five *observations* of it — per this epic's standing rule, a claim
  repeated across messages is still one source until independently derived.
- HYPOTHESIS: the defect is still live in HEAD — confirm/refute at
  `manage-architecture` § `derive-verification` (the `build_class` emission site) and at
  `manage-execution-manifest` § the compose step-resolution symbol that raises
  `unresolvable_step` (verify-at-outline). ⛔ **The lessons are dated 2026-07-28; a fix may have
  landed since.** If HEAD refutes it, the plan closes as already-fixed and the corpus lessons
  are retired — that is a legitimate outcome, not a wasted run.
- Verify-first clause: D0 re-derives the five lessons against HEAD **before any deliverable is
  scoped**. A refuted premise loops back and re-scopes to lesson retirement only.

## Expected Surface

- HYPOTHESIS: `plan-marshall:manage-architecture` — `derive-verification` `build_class` emission
  (verify-at-outline)
- HYPOTHESIS: `plan-marshall:manage-execution-manifest` — compose step resolution /
  `unresolvable_step` (verify-at-outline)
- HYPOTHESIS: `plan-marshall:phase-4-plan` — the stamping site that writes the command into a
  task's `verification.commands` (verify-at-outline)

Every surface entry is a HYPOTHESIS on purpose: the cluster names components, and a component
name is not a file. Resolve each to a file and symbol at outline before scoping on it.

## Dependencies and Sequencing

- Depends on: none
- ⚠ Overlaps with: `PLAN-TRUTH-019` (build-gate coverage parity) may touch the same
  `build_class` vocabulary — check at outline; if it does, serialize.
- Adjacent to: `PLAN-TRUTH-028` (domain-invariant chain hardcodes the Python toolchain) — same
  build-class family, different axis.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-067-derive-verification-emits-a-build-class-phase-5-cannot-route.md"
```

## Write-Boundary

Touches only its own repository source and tests. Creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
