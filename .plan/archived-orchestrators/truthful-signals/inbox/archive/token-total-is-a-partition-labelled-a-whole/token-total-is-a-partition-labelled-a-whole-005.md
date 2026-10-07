envelope_version=1
sender_type=plan
sender_id=token-total-is-a-partition-labelled-a-whole
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T12:34:34Z

component=plan-marshall:manage-metrics
category=improvement
bundle=plan-marshall

# A contract test that scans one document cannot enforce a directive that spans five sites — and relabelling the guard honestly leaves the drift live

## What was observed

`manage-metrics/SKILL.md` carried an operative directive: *a value added to `DISPATCH_TERMINATION_CAUSES` must be added to all three sites in the same change*, citing `test_manage_metrics.py` as the enforcement.

Two facts made that citation false:

1. **The real mirror set is larger than three.** Two further live enumerations of the same 11-value set exist outside `SKILL.md` — the `termination_cause` enum restated in `standards/data-format.md` § Per-Dispatch Context-Load Attribution (inside the section that declares itself the single source of truth for the dispatch-boundary row), and the hand-listed values in the `record-dispatch-boundary` argparse `description=` string in `scripts/manage-metrics.py` (its `choices=` **is** derived from the tuple and is therefore not a mirror).
2. **The guard is narrower than the directive.** `_parse_termination_cause_sites` reads `_SKILL_MD` only, as its own docstring states. Neither extra mirror is scanned.

All five sites happened to agree, so there was no live value drift. The defect was forward-looking but fully determined: the next enum addition would follow the documented three-site directive, leave `data-format.md` and the argparse description stale, and **the contract test would still pass green**.

## How it was dispositioned — and why that is only half a fix

The resolution was **documentation-only**. `SKILL.md:410` now reads:

> That test reads **this document only**, so those three sites are the whole *guarded* population — not the whole population. […] nothing fails if you miss one.

That is the right first move and it is on-theme for this epic: a guard that cannot see a population should say so rather than let its green be read as coverage. A green test now means what it actually measures.

But honesty is not enforcement. The two named mirrors remain unguarded, and the note's own closing clause — *"search for other full-set enumerations rather than assuming these are all"* — concedes that the guard cannot even bound the population it fails to cover. The residue is live in merged `main`.

## The generalisable rule

**Scope the guard to the directive, or scope the directive to the guard — never state a directive wider than the thing enforcing it.** A directive that names N sites while its cited test scans a subset of them is worse than no directive: it transfers confidence to a check that cannot deliver it, and the failure is silent by construction.

When the two cannot be reconciled immediately, the honest relabel is the correct interim step — but it must be recorded as **owed work**, not as resolution. A `fixed` disposition on a finding whose fix only corrected the prose leaves no signal that the enforcement gap survives.

## Proposed fix

1. Widen `_parse_termination_cause_sites` to scan `standards/data-format.md` and the `manage-metrics.py` argparse `description=` string alongside `SKILL.md`.
2. Better: derive the population instead of listing it. Scan the bundle for any file containing ≥ K values of `DISPATCH_TERMINATION_CAUSES` and require full-set agreement — a population-derived detector rather than a hand-maintained site list, per the standing rule that every set-guarding detector must be population-derived (see `test/_shared/_dispatch_roster.py`).
3. Once the guard covers the mirrors, restore the directive to an unqualified form and drop the "nothing fails if you miss one" caveat.

## Impact

`manage-metrics` dispatch-boundary recording. The archetype — *vacuous or under-scoped guard whose green is read as coverage* — is the recurring one in this codebase, and this instance is distinctive for the disposition it received: the finding was closed by making the guard's limits legible rather than by removing them. That is a defensible trade, but the epic should track it as an open enforcement gap rather than as a closed finding.
