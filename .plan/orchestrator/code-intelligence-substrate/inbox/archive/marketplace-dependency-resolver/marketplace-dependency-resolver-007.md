envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T19:17:07Z

component=plan-marshall:extension-api
category=anti-pattern
title=A plan spec allocated two implementors of a one-id-per-bundle extension point, and the cardinality was undocumented

# A plan spec allocated two implementors of a one-id-per-bundle extension point, and the cardinality was undocumented

## What happened

The plan spec for `marketplace-dependency-resolver` declared **two derivation
resolvers, both hosted on `pm-plugin-development`**. The Axis-C seam admits exactly
**one resolver id per bundle**. The spec was therefore not implementable as written,
and the discovery happened during execution — after the deliverable set was frozen,
after the split/no-split decision had been recorded, and after the plan had been
launched.

The resolution was to relocate the python-import resolver to `pm-dev-python`. That
worked, but it moved a deliverable across a bundle boundary mid-execution, which is
a scope change that the spec had not sized.

## The root cause is a missing contract statement, not a careless author

The extension point's contract doc did not state its per-bundle cardinality. In the
absence of a stated bound, "a bundle may implement this extension point" reads as
unbounded — which is the correct default reading for most extension points, and is
wrong for this one.

Nothing in the spec-authoring path could have caught it, because the fact was not
written down anywhere the author would look. The author did not skip a check; there
was no check to skip.

## Corrective rule — for extension-point contract docs

**Every extension-point contract MUST state its per-bundle cardinality explicitly**
— `exactly one per bundle`, `at most one per bundle`, or `unbounded` — as a declared
field of the contract, not as prose a reader might infer. A cardinality that is only
discoverable by reading the resolver implementation is a cardinality that will be
violated by the next spec written against it.

This is the same defect class as an undocumented uniqueness constraint on a database
column: the constraint is real and enforced, but the schema a caller reads does not
mention it, so the caller finds out at insert time.

## Corrective rule — for spec authoring

When a spec allocates **more than one implementor of the same extension point**,
resolve the extension point's cardinality **at outline time**, before the deliverable
set is frozen. This is a cheap read and it is the difference between a bundle
relocation costed into the plan and a bundle relocation absorbed mid-execution.

## Settled fact — do not re-derive

The follow-on worry that a domain bundle "is not guaranteed active" was verified
**UNFOUNDED**. `discover_derivation_resolvers` walks `discover_all_extensions`,
which is explicitly **unfiltered by project applicability** — hosting a resolver on
`pm-dev-python` does not make it conditional on the consuming project being a Python
project. This is settled; it should not be re-litigated by the next plan that
considers where to host a resolver.
