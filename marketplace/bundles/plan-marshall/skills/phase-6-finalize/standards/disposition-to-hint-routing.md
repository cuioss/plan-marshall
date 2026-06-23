---
name: disposition-to-hint-routing
mode: knowledge
---

# Disposition → Hint Generalization and Routing

The single, shared contract for turning recurring user gate-dispositions
(`suppressed` / `accepted` / `taken_into_account`) into durable architecture
hints. It is consumed by BOTH preference-learning surfaces:

- the **meta-only cross-plan auditor** (`audit-archived-plan-retrospectives`
  Step 4c), which aggregates dispositions across the whole archived-plan corpus,
  and
- the **consumer-available per-plan emitter**
  (`default:finalize-step-preference-emitter`), which aggregates one plan's
  dispositions at phase-6-finalize.

Neither surface restates the rules below — they reference this document. This is
the cross-cutting single source of truth for the generalization rule, the
routing targets, and the privacy invariant. The THRESHOLD GATE is deliberately
NOT owned here (see § "Threshold gate is surface-owned").

## (a) Generalization rule

A surfaced preference is a `(module, finding-class, disposition)` recurrence —
the SAME finding class repeatedly receiving the SAME disposition. The
generalization step turns that recurrence into a hint string framed in the
project's voice, NOT a transcription of the raw dispositions:

| Disposition | What the recurrence means | Generalized hint shape |
|-------------|---------------------------|------------------------|
| `suppressed` | the project repeatedly judges this finding class a non-issue in this context | a **best-practice**: "prefer to suppress {finding-class} in {module} because {project-specific reason}" |
| `accepted` | the project repeatedly accepts this finding class as a deliberate, tolerated tradeoff | an **insight**: "the project favours / tolerates {pattern} — {finding-class} is accepted in {module}" |
| `taken_into_account` | the project repeatedly folds this finding class into its work as a standing concern | an **insight**: "the project treats {finding-class} as a standing consideration in {module}" |

Generalize, do not transcribe: the hint names the durable preference the
recurrence implies, not the individual findings. A single occurrence is never
generalized — only a recurrence that cleared its surface's threshold gate.

## (b) Routing rule

Generalized hints are routed to the EXISTING `architecture enrich` sink — there
is no new store. The recurrence's module attribution selects the verb:

- **Module-attributed pattern** (the recurrence carries a concrete module) →

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    enrich best-practice --module {module} --practice "{generalized practice}"
  ```

- **Cross-cutting pattern** (the recurrence spans modules or carries no concrete
  module attribution) →

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    enrich insight --module default --insight "{generalized insight}"
  ```

Both verbs write into the existing `enriched.json` `best_practices[]` /
`insights[]` schema, which surfaces automatically through `get-module-context`
into the phase-3-outline `## Architecture Hints` section — biasing future
outlines. See `plan-marshall:manage-architecture` for the `enrich` verb surface.

## (c) Privacy invariant

**Generalize, do not log raw dispositions.** No per-finding hash IDs, no raw
`suppressed` / `accepted` / `taken_into_account` rows, and no individual finding
titles are ever written to `enriched.json`. Only the generalized hint string —
the durable preference framed in the project's voice — is persisted. The raw
disposition corpus stays in `artifacts/findings/*.jsonl` (the auditor) or behind
the `manage-findings` query (the emitter); it is never copied into the hint
store.

## Threshold gate is surface-owned

This contract owns generalization and routing ONLY — it does NOT own the
threshold mechanism that decides which recurrences are surfaced. The threshold
gate is owned by each surface:

- the **cross-plan auditor** gates via its `THRESHOLDS` script constant
  (`THRESHOLDS["preference_disposition_occurrences"]` in `scripts/audit.py`) —
  meta-only; consumers cannot edit it;
- the **per-plan emitter** gates via its `marshal.json` config knob (its
  `configurable:` block) — consumers CAN edit it.

Both surfaces feed only ALREADY-GATED recurrences into the generalization rule
above; the routing step never re-applies a threshold.
