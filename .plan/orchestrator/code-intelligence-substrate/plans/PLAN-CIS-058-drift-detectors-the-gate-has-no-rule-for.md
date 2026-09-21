<!-- ⛔ RETIRED 2026-09-12 — ABSORBED INTO `PLAN-CIS-049`, NOT ABANDONED.

This spec is no longer emittable and its queue row reads `retired`. Every one of its three
deliverables survives inside
`plans/PLAN-CIS-049-architecture-store-query-truthfulness.md`:

  D1 (the verb-set-versus-docs rule)  -> PLAN-CIS-049 D7, RE-SCOPED to complete the SHIPPED rule
                                          (7845a4b9a / #1370) rather than build one
  D2 (heading-hierarchy placement)    -> PLAN-CIS-049 D8
  D3 (revoked-tools verification)     -> PLAN-CIS-049 D9

Reason for the merge (operator direction, 2026-09-12): larger plans, ceiling twelve deliverables,
grouped by shared target. This spec and PLAN-CIS-049 were declared MUTUALLY EXCLUSIVE FOR EMISSION
in this very file (see the surface-collision warning below) because both own
`manage-architecture/standards/client-api.md` and `argparse_surface.py`. Merging dissolves the
exclusion instead of scheduling around it.

The three blocking verdicts recorded below (claims 0, 4 and 5, all `contradicted` / `rescoped: no`)
were ABSORBED into PLAN-CIS-049 D7 in the same act. They are left here verbatim as the record of
what was refuted and when; do not re-stamp them, and do not resurrect this file.
-->

# PLAN-CIS-058: Drift detectors the quality gate has no rule for

epic: code-intelligence-substrate
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Authored by the orchestrator on 2026-08-22 during the landed-corpus ingest, because the
> 2026-08 cloud wave left this work uncovered. See § Provenance.

## Objective

Two obligations the epic keeps discovering and never assigns an owner. Both are **missing structural
checks**, not one-off defects, and both are the reason a defect class keeps recurring rather than
being closed once.

The first: **verb-set-versus-docs drift has no detector.** Two consecutive plans over the same query
surface each shipped a documentation set that no longer matched the verbs it documented — and the
second plan's audit found the drift was *worse* than the first plan's own cold read had disclosed
(11 of 17 verb sections misfiled, not 7). Neither plan was careless; there is simply no rule that
can fail on it, so it survives every gate. Its own audit names this as the root cause and recommends
prioritising the detector over further one-off doc patches.

The second: **a verification obligation the epic wrote down and never discharged.** `PLAN-CIS-002`'s
D2 required verifying a claim *inside a dispatched leaf with `Grep`/`Glob` revoked* — the only
configuration that proves a capability answer is real rather than an artifact of the verifier having
other tools available. That obligation was discharged by no plan, and its audit records it as unmet
epic-wide.

## Deliverables

Three deliverables.

1. **D1 — A plugin-doctor rule for verb-set-versus-docs drift.** A skill's documented verb set must
   be derivable from its script's argparse surface, and a documented verb with no registered
   counterpart — or a registered verb with no documentation section — must fail the gate. ⛔ **The
   rule must be population-derived**: it publishes how many verbs and how many documented sections it
   compared. A rule that can return "0 mismatches" from an empty comparison set is the exact defect
   this epic keeps finding, and shipping one here would be the fourth recorded instance of a fix
   reproducing its own target.

2. **D2 — Heading-hierarchy placement, as part of the same rule or beside it.** The observed drift
   was not only *which* verbs are documented but *where* the sections sit — 11 of 17 misfiled under
   the wrong `H2`. Decide from the evidence whether that is the same check or a sibling, and record
   the reasoning. ⚠ **Re-derive the 11-of-17 count at outline**; it was measured in August 2026 and
   the tree has moved. The count is a lead, not a fact.

3. **D3 — Discharge the revoked-tools verification obligation, or retire it with a reason.** Either
   perform the verification `PLAN-CIS-002`'s D2 requires — inside a dispatched leaf with `Grep` and
   `Glob` revoked — and record the result, or establish that the obligation is unsatisfiable as
   written and retire it explicitly. ⛔ **What is not acceptable is a third year of it sitting
   unmet and unowned.** If it is retired, the retirement states what weaker check replaces it.

**Split verdict:** three deliverables, well below the threshold. D1 and D2 are one surface; D3 is a
different one, and pairing them is deliberate — both are *structural checks the epic specified and
never built*, and neither is large enough to justify its own plan.

## Claim Labels

- **OBSERVED**: no plugin-doctor rule catches verb-set-versus-docs drift — established by
  `PLAN-CIS-046`'s audit (G14), which names it as the root cause of the drift surviving two
  consecutive plans. Archived at `cloud-runs/135-remove-lsp-query-facade/gaps.md`.
  - verdict: contradicted | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: no | evidence: REFUTED at HEAD by a positive account. Commit 7845a4b9a (#1370) added marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_documented_verb_set_drift.py (686 lines) carrying rule_id documented_verb_set_drift; it is registered in _rule_registry.py and wired in _runner.py and detects verb_missing_from_docs and phantom_documented_verb - exactly the verb-set-versus-docs drift D1 targets. It also publishes population_size on every finding with a verb_set_drift_empty_population guard so it meets the spec's own anti-vacuity bar. The spec's build-it premise is dead; its complete-it branch is what remains.
- **OBSERVED**: `PLAN-CIS-002`'s D2 revoked-tools verification was never discharged by that plan or
  any later one — its audit G7. Archived at
  `cloud-runs/130-lsp-shaped-query-api/gaps.md`.
  - verdict: unverifiable | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Unreachable population: the claim rests on the git-ignored per-plan artifact cloud-runs/130-lsp-shaped-query-api/gaps.md, which is outside the crawled inventory (architecture find returned count 0). No commit among the 46 since 91a07aaa4 references PLAN-CIS-002 D2 or revoked-tools verification. Not settleable from this checkout; unverifiable admits by contract and leaves the debt on the record.
- **HYPOTHESIS**: the heading-hierarchy misfiling is still present and still measures near 11 of 17 —
  confirm/refute at outline against the live query-surface documentation (verify-at-outline). ⚠ A
  count measured in August 2026 is a lead.
  - verdict: unverifiable | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Unreachable in this pass: client-api.md has had no commit since #1252, well before the 46-commit window, so nothing at HEAD contradicts the recorded ~11-of-17 count - but re-deriving the exact figure needs a fresh heading sweep, which is the D-level measurement the spec itself defers to outline. Not corroborated, because the count was not re-executed.
- **HYPOTHESIS**: `plugin-doctor`'s existing analyzer framework can host D1 without a new extension
  point — confirm/refute at `pm-plugin-development:plugin-doctor` at outline (verify-at-outline).
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Corroborated by the strongest possible evidence - the thing was actually built that way. D1 shipped as an ordinary analyzer: _analyze_documented_verb_set_drift.py registered via RuleDescriptor in _rule_registry.py and wired in _runner.py alongside siblings such as _analyze_verb_chains.py. No new extension point was added.
- **HYPOTHESIS**: the argparse surface is already derivable through an existing seam
  (`script-shared`'s argparse surface helper) and D1 can consume it rather than re-parse —
  confirm/refute at outline (verify-at-outline).
  - verdict: contradicted | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: no | evidence: REFUTED at HEAD with a positive account. The shipped D1 imports only _analyze_verb_chains and _doctor_shared - never argparse_surface.py - and implements its own AST walk (derive_registered_verbs / VerbSet) with fail-closed skip states. The reason is recorded in argparse_surface.py's own docstring: a static AST walk was abandoned in this tree after producing 1323 false positives. The consume-the-seam hypothesis is therefore not merely unrealised but actively contraindicated.
- **Verify-first clause:** re-derive at outline that no such rule has been added since 2026-08-22.
  If one exists, this plan re-scopes to *complete* it — in particular to check whether it publishes
  its population.
  - verdict: contradicted | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: no | evidence: The verify-first clause asked whether such a rule had been added since 2026-08-22, and the answer at HEAD is YES: commit 7845a4b9a (#1370) landed 2026-08-31, inside the 46-commit window since 91a07aaa4. The clause's own complete-it branch therefore fires, and its named check - does the rule publish its population - is already satisfied. The spec must absorb this before it is emittable.

## Expected Surface

- **HYPOTHESIS**: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/` — the new
  analyzer and its registration (verify-at-outline)
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/argparse_surface.py`
  — the existing argparse-derivation seam this rule should consume (verify-at-outline)
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md`
  — the drifted document that motivated the rule, as the rule's first real subject
  (verify-at-outline)
- Test surface: the analyzer's own tests, **population-derived from the live skill set** — copy the
  `test/_shared/_dispatch_roster.py` pattern rather than enumerating skills by hand, and include a
  matched negative control (a synthetic skill with a deliberately undocumented verb must fail).

⛔ **Surface collision warning.** `client-api.md` is contended with `PLAN-CIS-049` and
`PLAN-CIS-053`. `argparse_surface.py` is contended with `PLAN-CIS-049`. **This plan may not be
emitted alongside either.**

## Dependencies and Sequencing

- **Depends on**: none.
- **Overlaps with**: `PLAN-CIS-049` (`argparse_surface.py`, `client-api.md`) and `PLAN-CIS-053`
  (`client-api.md`) — mutually exclusive for emission with both.
- **Adjacent to**: `PLAN-CIS-054`, which fixes the *content* of drifted documentation. This plan
  builds the rule that stops it recurring. ⭐ **Running this one first is worth considering**: a
  detector that lands before the sweep tells the sweep where to look, and tells it when it is done.
  That ordering is offered, not mandated — `PLAN-CIS-054`'s own charter puts it last for a different
  and equally good reason.

## Provenance

Authored 2026-08-22 by the orchestrator during the landed-corpus ingest. Both items were found by
the audit and recorded in per-plan gap entries, but **neither was assigned to any of the eight `5xx`
fix plans** — the wave groups by owning surface and shared mechanism, and a *missing* detector has
no owning surface to be grouped under. That is a real gap in the wave's own coverage model, and it
is recorded in `epic.md` § Structural Findings rather than left to be rediscovered.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-058-drift-detectors-the-gate-has-no-rule-for.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message.
