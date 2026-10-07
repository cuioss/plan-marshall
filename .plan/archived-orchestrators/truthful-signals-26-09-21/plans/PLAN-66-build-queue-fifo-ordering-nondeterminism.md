# PLAN-66: build_queue FIFO Front Sampled Outside the Serialized Critical Section (LIVE BUG)

epic: truthful-signals
workstream: WS-01

> Staged plan spec (lessons-triage 2026-07-25, **PRIORITY — extracted from PLAN-63**). A live
> concurrency correctness bug surfaced by the triage workflow: the build-queue FIFO front is selected
> by a timestamp sampled OUTSIDE the serialized read-modify-write, the exact divergence its sibling
> `merge_lock.py` already fixed (#735). Root cause known, single-file, mirror-fix available →
> **surgical / micro-lane**. Operator-prioritized.

## Objective

`manage-locks` `build_queue.py` selects the FIFO front by a timestamp key (`min(ts)` / `sorted`) whose
`ts=time.time()` value is **sampled outside** the `_mutate` read-modify-write critical section, so
under concurrency the admission order can diverge from the true append order. Its sibling
`merge_lock.py` already fixed the identical defect in #735 (`_fifo_front` now returns `waiting[0]`,
admit-ts informational). Bring `build_queue.py` to the same single-source-of-truth invariant.

## ⚠ Mechanism — verified at HEAD (triage workflow, 2026-07-25)

- `merge_lock.py:365` `_fifo_front` returns `waiting[0]` — the serialized structure's own append order
  is the FIFO source of truth; the admit timestamp is informational (fixed #735).
- `build_queue.py:354` samples `ts=time.time()` **outside** the `_mutate` rmw and selects the front via
  `sorted` / `min(ts)` (front-selection at ~`:301`, `:385`, `:517`). Because the key is sampled before
  entering the serialized section, two near-simultaneous enqueues can be ordered by clock skew rather
  than append order — a FIFO-fairness / lost-ordering divergence the merge-lock path no longer has.

## Deliverables

### D1 — GATE: confirm the divergence and pick the mirror shape (mutates nothing)
Confirm `build_queue.py` still selects the front by an outside-sampled `ts` and enumerate every
front-selection / ordering site (`:301`, `:354`, `:385`, `:517` per the triage read). Confirm the
`merge_lock.py` `_fifo_front` pattern (append-order front, informational ts) is the sanctioned mirror.
Decide: adopt the append-order-front invariant, or (if an ordering key genuinely must drive selection)
sample it INSIDE the `_mutate` critical section.

### D2 — single-source FIFO ordering
Make `build_queue.py` select the front from the serialized structure's own append order
(`waiting[0]`-equivalent), or sample the ordering key inside the `_mutate` rmw — matching the
`merge_lock.py` #735 invariant. No FIFO decision reads a value sampled before the serialized section.

### D3 — regression test (concurrency-ordering)
A test that enqueues entries whose wall-clock sample order differs from their append/admission order
and asserts the front follows append order, not the outside-sampled timestamp. Mirror the merge-lock
FIFO test if one exists. Pins the invariant against re-divergence.

## Lessons Carried (bound 2026-07-25 · lessons-triage)

Carry at phase-1-init via `manage-lessons convert-to-plan --lesson-id 2026-06-21-11-002 --plan-id
{plan_marshall_plan_id}`; retire at finalize (provenance to tombstone `--reason`).

- `2026-06-21-11-002` — **OPEN (live)** — FIFO/sequence ordering key sampled outside the serialized
  critical section diverges from append order under concurrency; the `merge_lock.py` half landed #735,
  the `build_queue.py` sibling still carries the divergence. This plan closes the sibling.

## Expected surface

- `manage-locks/scripts/build_queue.py` (front-selection / ordering sites)
- a test under `test/plan-marshall/manage-locks/**`

**Disjointness:** single file `build_queue.py` + its test — surgical. Disjoint from the 3 launched
(PLAN-27 java, PLAN-47/48 orchestrator-config) and from PLAN-53 (`orchestrator.py`). **Emittable now**;
strongest free-slot candidate (live correctness bug, operator-prioritized).

## Notes

- Micro-lane / recipe-surgical-fix shape: root cause diagnosed, mirror-fix (`merge_lock.py` #735)
  exists, single-file bounded change. A small plan is justified here despite the "small plans are
  expensive" guidance because it is a prioritized live correctness defect, not discretionary work.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
