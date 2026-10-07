# PLAN-103: The wrong_store guard refuses project-local lessons from their own correct store

epic: truthful-signals
workstream: WS-01

> Staged plan spec — small and bounded. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

`manage-lessons add` refuses a **prefix-less** (project-local) component with `wrong_store`, because
the guard treats the whole component name as a bundle name. The only escape is
`--allow-foreign-store` — a flag whose name and documented purpose are the **cross-repo** case. Fix
the guard so a project-local lesson files into its own store without a flag.

## ⭐ Root cause — CONFIRMED first-party, not inferred

The reporter flagged their root cause as inferred and asked for confirmation. **Confirmed at HEAD**,
`manage-lessons/scripts/_lessons_io.py`:

```python
bundle = component.split(':', 1)[0]
if main_anchored_store_owns_bundle(bundle):
    return
```

For `--component integration-tests` (no `:`), `bundle` becomes `integration-tests`, ownership can
never hold, and the guard refuses.

⛔ **The refusal message is FALSE, not merely unhelpful.** It says *"store does not own bundle
'integration-tests'"* — **but `integration-tests` was never a bundle.** The guard states a confident
reason that is untrue, which is precisely this epic's theme at the error-message layer.

⚠ **The function's own docstring declares the input contract** — *"The `bundle:skill[:script]`
component notation"* — **and the code never verifies it.** A prefix-less component is neither
rejected as malformed nor handled as local; it is silently misread. **The contract is documented and
unenforced**, the doc-contract-divergence archetype inside the guard.

## Observed impact

- **A store that demonstrably owns the shape is refused it.** The API-Sheriff store already contains
  `2026-07-25-15-001` with component `integration-tests`, and that lesson is referenced as MANDATORY
  by two staged plan specs in its epic. The guard refuses to file a lesson of a shape the store
  already holds.
- Reproduced with `integration-tests` and `api-sheriff-roadmap`, and by inspection every other
  prefix-less component in that store (`sonar-new-code-coverage`, `pre-commit-formatter`).
- ⛔ **The more damaging half — flag-signal destruction.** Operators are pushed into
  `--allow-foreign-store` for the entirely **local** case. Once that is routine, a **genuine
  cross-repo mis-file becomes indistinguishable from ordinary local filing**, and the flag stops
  carrying information. **The guard degrades the very safety property it exists to provide.**
- ⚠ **This defect blocked a real hand-off:** seven plan-marshall-component lessons raised in the
  API-Sheriff repo could not be filed there and had to be carried across by hand.

## Deliverables

1. **D1 — GATE (mutates nothing): settle what a prefix-less component means.** Recommended and
   reporter-proposed: **apply the ownership check only when the component carries a bundle prefix
   (contains `:`)** — a prefix-less component is project-local by construction. ⚠ D1 must also decide
   whether a prefix-less component should be validated against *anything*, or accepted as free-form;
   "skip the check" and "accept any string" are different decisions and only one of them is stated by
   the recommendation.
2. **D2 — implement, and make the refusal truthful when it does fire.** A refusal for a genuinely
   foreign bundle should say so; a malformed component should be rejected as malformed. **No path may
   report a reason that is not the actual reason.**
3. **D3 — tests, verified to FAIL pre-fix.** (a) A prefix-less component files into the local store
   with no flag. (b) A genuinely foreign `bundle:skill` component is still refused without
   `--allow-foreign-store`. (c) The refusal message names the real cause. ⚠ **(b) is the regression
   that matters** — the fix must not turn the guard off.

Three deliverables. Small by construction.

## Claim Labels

- OBSERVED (orchestrator-verified first-party 2026-07-28): the `split(':', 1)[0]` derivation and the
  refusal text at `manage-lessons/scripts/_lessons_io.py` (~`:57-66`); the docstring's declared
  `bundle:skill[:script]` contract.
- OBSERVED (reporter, quoted verbatim): the refusal for `--component integration-tests`; the presence
  of `2026-07-25-15-001` with that component in the API-Sheriff store.
- HYPOTHESIS: the same derivation is used by the **second** `wrong_store` site
  (`manage-lessons.py:797`, alongside `:399`) — confirm/refute at both call sites
  (verify-at-outline). **Fixing one and not the other would leave the defect half-live.**
- Verify-first clause: re-read the guard at HEAD before scoping. If `manage-lessons` changed
  meanwhile — see the in-flight overlap below — re-baseline rather than proceeding.

## Expected Surface

- OBSERVED: `manage-lessons/scripts/_lessons_io.py` — the ownership guard.
- OBSERVED: `manage-lessons/scripts/manage-lessons.py` — `:399` and `:797`, the two `wrong_store`
  returns.
- HYPOTHESIS: `script-shared/scripts/marketplace_paths.py` `main_anchored_store_owns_bundle` — read
  only unless D1 moves the prefix decision there (verify-at-outline).
- OBSERVED: `manage-lessons` SKILL docs, wherever `--allow-foreign-store` is described.
- OBSERVED: tests under `test/plan-marshall/manage-lessons/**`.

**Disjointness:** `manage-lessons`.
⛔ **BLOCKED while PLAN-90 is in flight** — it holds `manage-lessons`. Same serialization class:
sequence, never pair.

## Dependencies and Sequencing

- Depends on: **PLAN-90 landing** (surface conflict only, not a logical dependency).
- ⚠ **Faster alternative available to the operator:** PLAN-90 is in flight and already owns this
  skill. If the operator pastes this defect into PLAN-90, it can be fixed there and **this plan
  retired** — the same absorb-into-the-running-plan route PLAN-95 took. Recorded so the choice is
  deliberate rather than defaulted into.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-103-wrong-store-guard-refuses-project-local-lessons.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
