envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:32Z

component=pm-documents:ref-documentation
category=anti-pattern
created=2026-10-21
bundle=pm-documents

# "Declared once" is a claim about every consumer, not about the declaration

ADR 017 stated that the lane entry ids are declared once in `LaneEntryIds` and that "a
rename moves the split, the checks and the fixture with it". The fixture
`per-lane-rework.pmwf` and `PerLaneRework.deepPrunesLightCalls` repeat the ids as text, so
a rename of the constants leaves the fixture unchanged: `InstancePruner.otherLane` prunes
nothing and `deepPrunesLightCalls` fails instead of migrating.

## Solution

Before writing that a rename moves something with it, search the literal value (not only
the symbol) and confirm no fixture, resource, or test repeats it as text. Where a
duplication exists, state it in the document rather than implying otherwise — the ADR now
names both the fixture and the test method that carry the ids by value.

## Impact

Any "single source of truth" or "rename-safe" claim about constants that cross into
fixture files, resources, or generated artifacts, where the symbol cannot reach.
