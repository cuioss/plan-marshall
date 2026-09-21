envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T15:50:13Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
bundle=pm-plugin-development
source_plan=inventory-blind-spot

# Symmetric-peer audit found the same defect re-expressed in the peer's own idiom

## Observation

The plan's target defect lived in `_classify_marketplace`: only an enumerated set of skill
sub-directories was recognised, so everything else classified as `None` (invisible to the inventory).

Its symmetric peer `_classify_generic` — the classifier for non-marketplace projects — carried **the
same defect**, but expressed in a **different idiom**: it recognised only `README*` and `CHANGELOG*`
as documentation. Same shape (an enumeration standing in for a category), different surface (filename
prefixes instead of directory names). A textual search for the buggy construct would not have found it;
only the structural question "who else answers this same question?" did.

## Solution

When fixing a classifier / dispatcher / resolver, enumerate its **symmetric peers** — the other
functions that answer the same question for a different input domain — and audit each one for the
*shape* of the defect, not for its *text*. The peer's version will usually be written in whatever
idiom that domain suggested, so:

- Do not search for the literal construct you just fixed.
- Ask: "what is the category-membership decision here, and what set stands in for the category?"
- Apply the fix in the peer's own idiom, and note explicitly when the peer's narrower scope is
  **deliberate** rather than defective — here `_classify_generic` intentionally stayed
  extension-driven, because path position carries no role guarantee in an arbitrary project, and that
  deliberate narrowness got its own boundary-pinning assertion.

The `ext-self-review-plan-marshall` symmetric-pair-function candidate class is the deterministic
surface that should be producing this pairing. It fired here (`pre-submission-self-review` ran clean
over 39 candidates), but the peer was found during implementation rather than surfaced by the
detector — worth checking whether the symmetric-pair detector's pairing heuristic covers
`_classify_marketplace` / `_classify_generic`-style pairs (shared verb prefix, disjoint input domain).

## Impact

Applies to every `_classify_*`, `_resolve_*`, `_detect_*`, `_dispatch_*` family in the codebase.
The recurrence signature: a fix touches one member of a same-prefix function family and the sibling
is never opened.
