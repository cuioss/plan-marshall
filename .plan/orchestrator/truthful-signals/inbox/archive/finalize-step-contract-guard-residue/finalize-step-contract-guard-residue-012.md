envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:38:39Z

component=plan-marshall:phase-6-finalize
category=bug

# A `mutates_source` step ordered above a head-dependent gate strands that gate's verdict on a superseded tree, and a forward pass never revisits it

> Provenance: this candidate is **orchestrator-reported, not re-measured by me.** The
> commit shas and step ordering below come from the finalize run's own first-party
> observation as forwarded to this step; I did not independently re-derive them from the
> ledger. Everything in § Solution is structural and checkable from the step frontmatter
> and `verdict-currency.md` without the shas.

## The observation

Within a single forward pass of the finalize step order:

1. `pre-push-quality-gate` (head-dependent) ran and recorded its verdict against
   HEAD `250aa788`.
2. `simplify` (a `mutates_source: true` step ordered later) then committed — twice —
   advancing HEAD to `990d88010`.

The gate's recorded verdict now names a tree that no longer exists. The re-entry check
would re-fire the gate on a fresh entry, but **a forward pass never revisits an earlier
order**, so within this run nothing did. CI covered the merged tree; the *local* gate's
record did not.

## Why the existing machinery did not catch it

`phase-6-finalize` already has the concept and the vocabulary — `standards/verdict-currency.md`
exists precisely to reason about whether a recorded verdict still describes the current
HEAD, and `test_head_dependence_derivation.py` derives which steps are head-dependent. The
step frontmatter already carries both facts needed to detect this statically:
`mutates_source` on the mutating step, and head-dependence on the gate.

What is missing is the **ordering invariant that relates them**. Currency is currently
treated as a re-entry question ("is this verdict still current when we come back?") rather
than an ordering question ("can this verdict still be current by the time the pass ends?").
The second is decidable before the run starts, from the order numbers alone.

## Solution

State and enforce the invariant at the level where it is statically decidable:

> For any head-dependent step `G` and any `mutates_source: true` step `M`, if
> `order(M) > order(G)` then `G`'s verdict is *provably* stale at end-of-pass whenever `M`
> actually commits.

Three enforcement points, in increasing cost:

1. **A roster test** over the finalize step frontmatter that fails when a `mutates_source`
   step is ordered above a head-dependent gate with no re-fire between them. This is
   population-derived from the frontmatter — the same shape as the existing dispatch-roster
   and head-dependence tests — so it cannot silently pass over an empty set, provided it
   publishes the population size it scanned.
2. **A recorded-HEAD field on every head-dependent verdict**, compared against actual HEAD
   at end-of-pass. This makes the staleness *observable in the record* rather than only
   preventable by ordering — the more robust of the two, because it also catches a mutation
   from a source the ordering analysis did not model.
3. **Re-firing** the gate. Correct but expensive, and unnecessary if (1) holds; keep it as
   the remedy when (2) detects staleness rather than as the default.

(1) and (2) are complementary, not alternatives: (1) prevents the statically-visible case,
(2) detects the rest. Shipping only (1) would leave a guard that is green by construction
against exactly the mutations it enumerated.

## Impact

The failure mode is a locally-recorded green gate over a tree that was never gated. It is
masked here because CI independently verifies the merged tree, which is why it can persist
undetected: the *outcome* is right for a reason unrelated to the *signal*. That masking is
the reason to fix it in the record rather than to rely on CI — a gate whose correctness
comes entirely from a different check is not a gate, and the next step ordered into that
window inherits a guarantee nobody is providing.
