envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T13:59:57Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
created=2026-08-02
bundle=pm-plugin-development

# Apply the rule you are enforcing to the artifacts your own change creates

PLAN-CIS-027's D4/D5 deliverable was, in substance, *stop duplicating the resolver roster*. It
removed roster-coupled counts and duplicate roster enumerations from five surfaces
(`ext-point-derivation-resolver.md`, `module-discovery.md`, `extension_base.py`,
`extension-architecture.adoc`, `code-intelligence.adoc`), collapsing the roster to a single
enumeration point.

In the same change, the plan **authored a brand-new** `EXPECTED_RESOLVER_IDS` literal in
`test_graph_family_bundle_project.py` — a fresh, hand-maintained copy of the very roster it was
de-duplicating everywhere else. CodeRabbit caught it on #1079; the plan's own self-review did
not.

The blind spot is structural, not careless. De-duplication sweeps are scoped by *"which files
already contain a copy?"* — an inventory taken **before** the change. Files the change itself
creates are, by construction, absent from that inventory, so the sweep's own scope definition
guarantees it cannot see them.

## Solution

When a change's deliverable is a **rule** (de-duplicate X, derive Y from its authoritative
source, never hard-code Z), run the rule a second time against the **change's own diff** before
submission — the added and modified hunks, not the pre-change inventory. Phrase the check as
*"does anything I wrote violate the thing I just made illegal?"*

Here the corrective was to derive the resolver ids from the discovery stage
(`pipeline['resolvers']`) rather than restating them, leaving exactly one executable roster pin
(`aefa66e`).

## Impact

Applies to every rule-shaped deliverable: de-duplication sweeps, "derive from the registration
mechanism" refactors, count-prose removals, hard-coded-command eliminations, and structural lint
rollouts. Note the recurring shape — the plan-marshall corpus already records a case of a
**vacuous guard introduced by a fix for vacuous guards**; this is the same family. A change that
establishes a rule is the single most likely place for the rule's next violation, because the
author is thinking about enforcement rather than about compliance.

Worth considering as a deterministic candidate in `ext-self-review-plan-marshall`: when a diff
*removes* N occurrences of a repeated literal, flag any occurrence of that same literal the diff
*adds*.
