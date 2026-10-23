envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-23T08:24:46Z

# "Declared once" is a claim about every consumer, not about the declaration

Severity: low. Bundle: **domain content** — `pm-documents` (`ref-documentation`). Filed under RULING 2026-10-09 (b): domain-bundle content at any severity.

## Sources

- inbox `pm-mcp-core-m2-m4-401`

## Consolidated statement

ADR 017 stated that the lane entry ids are declared once in `LaneEntryIds` and that "a rename moves the split, the checks and the fixture with it". The fixture `per-lane-rework.pmwf` and `PerLaneRework.deepPrunesLightCalls` repeat the ids as text, so a rename of the constants leaves the fixture unchanged: `InstancePruner.otherLane` prunes nothing and `deepPrunesLightCalls` fails instead of migrating.

The general shape: a "single source of truth" or "rename-safe" claim about constants that cross into fixture files, resources or generated artifacts, where the symbol cannot reach. The claim is invisible in review because the declaration site genuinely is single.

## What is asked

Add the rule to `pm-documents`' `ref-documentation` guidance: before writing that a rename moves something with it, search the **literal value** (not only the symbol) and confirm no fixture, resource or test repeats it as text; where a duplication exists, state it in the document rather than implying otherwise.

## Evidence

As recorded by the sender (pm-mcp-core plan, ADR 017 and its follow-up). Not re-verified against HEAD in this run.
