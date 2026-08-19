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
is no new store. **Only a MODULE-ATTRIBUTED recurrence is promotable**; an
UNATTRIBUTED recurrence is not (see § "(d) Attribution gate").

- **Module-attributed pattern** (the recurrence carries a concrete `module`, or a
  `component` that resolves to one) → route to that concrete module, selecting the
  verb by the disposition's generalized shape in § (a):

  ```bash
  # suppressed → best-practice
  python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    enrich best-practice --module {module} --practice "{generalized practice}"
  # accepted / taken_into_account → insight
  python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    enrich insight --module {module} --insight "{generalized insight}"
  ```

- **Unattributed pattern** (the recurrence carries no concrete `module` and no
  `component`, so it collapses to the `default` fallback bucket) → **NOT
  PROMOTED.** File no owed hint for it — see § "(d) Attribution gate".

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

## (d) Attribution gate — the unattributed `default` bucket is not promotable

The `default` bucket is the sink a finding collapses into when it carries no
concrete `module` and no `component`. It is NOT a genuine cross-cutting
judgement: the aggregation keys on a single module value and cannot detect a
recurrence that genuinely spans several modules, so **on this disposition→hint
routing path** `default` means *unattributed*, never *cross-cutting*.

That scoping is load-bearing rather than pedantic: the `default` bucket has a
second, still-live producer, and the claim is false of it. The cross-cutting
lessons-capture route in
[`../workflow/lessons-capture.md`](../workflow/lessons-capture.md) deliberately
routes a genuinely cross-cutting fact to `default` — there, `default` DOES mean
cross-cutting, and that route is retained, not retired. A reader who takes the
unscoped form and applies it to a `default` entry from that producer will
misclassify a deliberate cross-cutting record as unattributed noise. Promoting an unattributed recurrence would
route an unverified hint to the widest possible blast radius — the least
attributable evidence landing in the most general slot.

Therefore an unattributed recurrence (its module resolves to `default`) is
**counted but never promoted**. Both surfaces enforce this:

- the **cross-plan auditor** drops `default`-bucket tuples from its candidate rows
  in `cross_preference_pattern` and reports the tally as
  `unattributed_excluded_count`;
- the **per-plan emitter** discards `default`-bucket tuples at its threshold gate
  before it files any owed hint.

This gate is independent of the threshold: a `default`-bucket tuple is dropped
even when it clears the recurrence count.

## (e) Authorship admissibility — a self-authored comment is not preference evidence

A finding contributes to a preference recurrence only when it is not the
pipeline's own control traffic. A `pr-comment` finding is admissible ONLY when it
is positively attributed to a recognized external reviewer bot — i.e. it carries a
`bot_kind` that is a **recognized reviewer identity**, validated against the
registry-derived set (the ingest verb stamps `bot_kind` from the comment author
login and `add_finding` validates it at write time; the auditor re-validates
archived records against the live registry, since it reads JSONL directly rather
than through that write-time check). A `pr-comment` with no `bot_kind` — or one
whose `bot_kind` is not a recognized reviewer identity — cannot be told apart from
the pipeline's own posted comments: the ingest verb records the pipeline's own PR
comments (a review-trigger comment, a description-restore) with `bot_kind` absent,
exactly as it records an unattributed human comment. Admitting one would let the
pipeline's own control traffic become evidence about the pipeline's preferences —
a SELF-REINFORCING artifact that grows with pipeline chattiness, not with operator
judgement.

There is no self-login signal on the finding (the comment-preparation verb stamps
no marker), so this gate fails CLOSED on positive external attribution rather than
trying to recognize "self" directly. Non-comment findings (lint/sonar/bug/…) carry
no author and are never pipeline-authored PR chatter — they are unaffected, and
their tool-disposition recurrences remain the primary preference signal.

Both surfaces apply this before a recurrence is counted: the cross-plan auditor
structurally in `cross_preference_pattern`; the per-plan emitter by admitting a
`pr-comment` finding only when its `bot_kind` is a **recognized reviewer identity**
in the registry-derived set, and excluding every other one when it aggregates
dispositions. Presence of the field is not the test: an unrecognized `bot_kind`
passes a presence check and fails the admissibility this section opens with, so the
two must not be conflated — the emitter is an LLM-executed prose contract, and this
paragraph IS its implementation.

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
