# Workstream: Truthful Signals & Machinery Integrity

id: WS-01
slug: truthful-signals
epic: truthful-signals
status: active

## Charter

Close the family of defects in which a tool, gate, or hand-off reports a confident clean/complete
signal while silently suppressing the caveat that makes it wrong — and the adjacent family in which
machinery silently loses information it was handed.

The workstream is the epic's single active slice: every staged plan belongs to it. Grouping is by
theme rather than by surface, because the archetype recurs across unrelated surfaces
(build routing, architecture query, retrospective compilation, finalize step ordering, terminal
title delivery, plan-spec ingestion).

## Scope

In scope:

- Signals that report success while dropping, eliding, or failing to propagate a real finding.
- Machinery that loses an operator-supplied brief, a spec body, or a fragment between stages.
- Observability gaps where the caveat IS detected but is written to a channel nobody reads.
- Orchestrator-tier configuration and autonomy knobs that make the above surfaces governable.
- Two operator-requested renames that close out the epic's vocabulary debt.

Out of scope:

- Harness-level instability (dispatch cancellation, tool-grant nondeterminism, timeout floors) —
  tracked as UNOWNED-INFRA watches, not our code.
- Any re-opening of the closed `plan-optimization` and `plan-server` epics.

## Plans

The ordered queue, per-plan surfaces, and sequencing gates are rendered in the epic's generated
START HERE block and are authoritative in `status.json` (`plans[]`). Charter-level sequencing notes:

- PLAN-41 is the priority head: it repairs the spec hand-off every later emit depends on. **(Shipped
  #991.)**
- **PLAN-TRUTH-015** (orchestrator rename; was PLAN-49) is drain-gated and runs last — it renames
  directories that most other plans modify.
- PLAN-47 and PLAN-48 share the new `orchestrator` config block and coordinate at outline. **(Both
  shipped, #997 / #996.)**

⚠ **Charter-level ids were re-scoped on 2026-07-30.** Every staged plan in this workstream now carries a
an epic-scoped `PLAN-TRUTH-{NNN}` id. Shipped, running, launched,
superseded and transferred rows kept their original ids by design. See `plan-id-rename-map.md`.

## Done Criteria

The workstream completes when every staged plan has shipped or been explicitly retired, the flagship
archetype has no open instance, and the closing rename (PLAN-TRUTH-015) has landed.
