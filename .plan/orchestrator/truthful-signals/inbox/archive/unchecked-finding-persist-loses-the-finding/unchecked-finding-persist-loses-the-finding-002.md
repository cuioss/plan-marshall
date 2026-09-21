envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:28:50Z

component=plan-marshall:phase-3-outline
category=anti-pattern
created=2026-07-28

# A request's enumerated list of affected sites is a sample, not a population

The request for this plan hypothesized five sites needing an unchecked-finding-persist
fix. A sweep-derived population count found 10 production persist sites — the request's
list was both short by two sites AND wrong in shape (it read as an enumeration when it
was actually a sample of what the reporter happened to notice).

## Solution

Whenever a request or finding lists specific affected call sites, population-derive the
real set with a structural sweep (grep/architecture-find across the whole surface,
grouped by the shared defect signature) before scoping the fix — never treat a
request's named list as the enumeration to fix.

## Impact

Any plan whose request names specific call sites, files, or emitters as "the affected
ones" should treat that list as a lower bound and a lead, not a ceiling.
