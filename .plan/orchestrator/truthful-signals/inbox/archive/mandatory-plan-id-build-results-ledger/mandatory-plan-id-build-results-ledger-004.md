envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:27:41Z

## Finding: `scope_creep_check` returns a CLEAN verdict derived from an ABSENT baseline

**Observed in**: main, reproduced **4 times** across `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.

### What was observed

`scope_creep_check` returned:

```toon
status: success
residual_count: 0
reason: no_baseline_sha
```

The `reason` field states plainly that there was **no baseline to compare against** — and
the verdict fields nevertheless report the shape of a clean pass. `status: success` with
`residual_count: 0` is what a genuinely scope-clean run looks like, so a consumer reading
only the verdict cannot tell the two apart.

Reproduced 4 separate times in this one plan, so this is the *normal* path, not an edge.

### Why it matters

This is the canonical form of the defect this epic exists to eliminate: **a confident
answer synthesized from a missing input**. "I compared and found nothing" and "I could not
compare" are different facts with different consequences, and here they share a
representation. The `reason: no_baseline_sha` field is doing the work of a caveat that no
consumer is obliged to read.

The correct verdict is a third state — `undecidable` (or equivalent) — that is
structurally distinct from `success`, so a consumer must handle it rather than being able
to accidentally read it as green.

### Suggested shape of a fix (not implemented)

- Introduce an explicit `undecidable` status for the no-baseline branch; do not return
  `success`.
- Suppress `residual_count` (or emit it as `null`) when no comparison was performed —
  a count of zero must mean *counted zero*, never *did not count*.
- Audit every consumer that branches on `scope_creep_check`'s status for the new state.

### Related pattern

Same archetype as the Sonar `count_status: confirmed` finding in this same batch, and the
same archetype as the epic's standing "which kind of zero is this" rule that
`orchestrator inbox list` already implements correctly with its `inbox_state` discriminator
(`missing` = could not look, `present` + `count: 0` = looked, found nothing). That
discriminator is the reference implementation this verb should copy.
