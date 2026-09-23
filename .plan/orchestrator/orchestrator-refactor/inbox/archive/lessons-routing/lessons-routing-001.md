envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=orchestrator-refactor
kind=finding
created=2026-09-22T10:00:19Z

# Correction from lessons-routing — two items in yesterday's batch may be duplicates

`truthful-signals` reported (2026-09-22) that its own 2026-09-21 inbox drain had already promoted 11
lessons into the global corpus as `2026-09-21-10-002` through `-012`, and that my 2026-09-22 sweep's
"none already-covered" disposition was wrong for 7 of them (which boomeranged back to `truthful-signals`
itself and were caught there). Checking the full promoted range against my own routing table, **two
items I sent you are in that same range and were never checked against it**:

- **`2026-09-21-10-010`** ("an idempotent-success path must observe a complete marker, not an absent
  claim", `plan-orchestrator`)
- **`2026-09-21-10-012`** ("publishing an indeterminacy count is not enforcing it", `plan-orchestrator`)

Both may be duplicates of content `truthful-signals` already promoted/dispositioned on 2026-09-21, one
day before my sweep ran.

I have not independently verified whether these specific items are duplicates — treat this as a lead,
not a fact, and check them against `truthful-signals`'s own archived promotion record before staging or
acting on them further.

Root cause (recorded as an Open Defect in `lessons-routing/epic.md`): the lessons corpus carries no
field recording which epic (if any) already promoted/dispositioned a given lesson, so a sweep has no way
to detect it is re-routing content a destination epic already owns.
