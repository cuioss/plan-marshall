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
registry-derived set. That validation depends on resolving the live registry, and
when it cannot be resolved the rule takes a documented degrade path instead — see
§ "The recognized-set resolution has two states, and the gate publishes which"
below, which is part of this contract, not an exception to it.

⚠ **The write-time check does not enforce this, and must not be mistaken for it.**
What `add_finding` rejects and what it admits is stated once, at the field's own
specification — see
[`../../manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md)
§ Optional Fields, the `bot_kind` row. The only consequence that matters here is
that a finding whose `bot_kind` is **absent** passes the write untouched, so the
store legitimately holds records this gate must still exclude.

The admissibility gate is therefore **load-bearing at aggregation, not
redundant with the write**: it is the only place that distinguishes "attributed
to a recognized reviewer" from "present in the store". Both consuming surfaces
apply it — the auditor re-validating archived records against the live registry
because it reads JSONL directly; the emitter per the paragraph below. A
`pr-comment` with no `bot_kind` cannot be told apart from
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

Both surfaces apply this before a recurrence is counted, and both reach ONE
implementation rather than each carrying a copy: the rule lives in
[`../../manage-findings/scripts/_preference_admissibility.py`](../../manage-findings/scripts/_preference_admissibility.py).
The cross-plan auditor imports that module and applies the predicate in
`cross_preference_pattern`; the per-plan emitter invokes the same predicate
through `manage-findings list --preference-admissible`, so the exclusion happens
in the script before the step aggregates anything.

### The recognized-set resolution has two states, and the gate publishes which

The recognized reviewer set is re-derived from the live registry each time the
gate runs, and that derivation can fail — the registry module may be
unresolvable in the calling envelope. The rule therefore has two states, and both
are part of this contract:

| Basis | What ran | What is admitted |
|-------|----------|------------------|
| `recognized` | The registry resolved; the gate validated each `bot_kind` against the live set. | Only a `pr-comment` carrying a recognized reviewer identity. |
| `presence_only` | The registry was unresolvable; the gate degraded. | Any `pr-comment` carrying a PRESENT `bot_kind`, unvalidated. |

The degrade is deliberate, not an oversight. Rejecting every `pr-comment` on an
unresolvable registry would hand preference learning a clean zero over a
population it never read — every recurrence threshold would silently under-fire
with nothing in the output saying so, the failure mode the fail-closed-with-an-
explicit-unknown-state discipline exists to prevent. And the threat this gate
actually defends against is untouched by the degrade: the pipeline's own posted
comments carry an **absent** `bot_kind`, and the presence check runs before the
registry check, so they are excluded on BOTH paths. What `presence_only` does
admit is the narrow residual — a present-but-unrecognized identity, i.e. a legacy
or de-registered reviewer.

**Neither state is silent.** Both surfaces publish
`preference_admissibility_basis` alongside their result:

- `manage-findings list --preference-admissible` carries it in the TOON payload
  whenever the flag is on, and omits it when the flag is off (an absent field
  means the narrowing did not run — it never asserts a basis);
- the cross-plan auditor's `preference-pattern-detector` block carries it under
  the same absent-key-is-undeclared rule.

The two basis values are declared once, beside the rule whose paths they name, in
[`../../manage-findings/scripts/_preference_admissibility.py`](../../manage-findings/scripts/_preference_admissibility.py)
(`PREFERENCE_BASIS_RECOGNIZED` / `PREFERENCE_BASIS_PRESENCE_ONLY`). Both surfaces
read them from there — the emitter side by importing them, the auditor off the
module object its loader already returns — so neither can drift from the other on
the vocabulary it publishes.

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
