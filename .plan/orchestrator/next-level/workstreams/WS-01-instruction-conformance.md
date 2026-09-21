# WS-01: Instruction conformance testing

epic: next-level

> Charter document for one workstream. Lives at `workstreams/WS-01-instruction-conformance.md` and is
> tracked in the epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

The repository's hard rules exist, in their own words, "because Claude regularly violates them
despite softer guidance" — an empirical claim about model behaviour that has never been derived. This
workstream builds the instrument that derives it: a conformance run that places a documented rule
under conditions engineered to make an agent defect from it, and reports a three-valued verdict with
the population it was scored over. It closes when a rule's continued necessity is a measurement rather
than a memory.

The adaptation is deliberate and narrow. The idea taken from outside is *put the instruction under
pressure instead of trusting it*. Everything else — the fixture format, the dispatch vehicle, the
verdict vocabulary, the storage — is this repository's existing machinery, and the verdict obeys this
repository's own evidence discipline: a rule that could not be scored reports `indeterminate` and
never `held`.

## Scope

- In scope: the conformance fixture format; the dispatch of a scenario into an
  `execution-context-{level}` leaf; the three-valued verdict and its population reporting; the first
  authored scenario set and its published baseline; the surfacing of results through `manage-findings`.
- Out of scope: editing any instruction prose on the strength of a conformance result (that edit is
  gated behind WS-02's cross-model evidence and is explicitly forbidden here); the multi-model
  dimension (WS-02 owns it); anything touching resident-context cost (WS-03 owns it).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-conformance-harness-seam | staged | The runnable seam: fixture format, dispatch, three-valued verdict over a stated population. One rule end-to-end. |
| PLAN-02-baseline-conformance-corpus | staged | Author the first scenario set against the highest-cost hard rules and publish the baseline. |

## Sequencing and Surface Notes

- PLAN-02 consumes PLAN-01's fixture format and cannot be authored against a format that does not
  exist. Strictly sequenced; never paired.
- Both plans touch a new skill surface that does not yet exist, so their declared surfaces overlap by
  construction. Neither may be paired with the other under any parallelization scope.
- ⚠ A conformance result is a signal about **one model on one runtime**. WS-02 owns the generalisation,
  and PLAN-01 must not quietly imply the verdict is fleet-wide — this is the exact
  confident-signal-hides-a-caveat shape the sibling `truthful-signals` epic exists to catch, and
  producing a fresh instance of it inside the instrument built to prevent it would be the worst
  available outcome.
