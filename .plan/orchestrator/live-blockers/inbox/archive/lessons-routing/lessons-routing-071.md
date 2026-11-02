envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T11:19:25Z

# cui-logging: a retired LogRecord identifier is not free for reuse

Severity: low. Domain content, filed under RULING 2026-10-09 (operator-confirmed for this sweep); may be discarded under the `live-blockers` FOCUS RULE.
Bundle: `pm-dev-java-cui` (cui-logging).

## Source

API-Sheriff `2026-10-24-15-001` (PLAN-V02-23, PR #515), verbatim in `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-02/API-Sheriff/`.

## Observation

A new WARN record was given an identifier retired earlier. An IT still asserted that id's absence (its old meaning), went red, and cost an extra task. The catalogue has gaps by design, so "lowest free gap" picks a retired id.

## Ground truth (c431a8193)

`cui-logging/SKILL.md:124` flags two live constants sharing an id; `logmessages-documentation.md:145-155` says "LogRecord deleted -> remove row". Nothing says a retired id stays reserved.

## What to consider

Allocate above the highest id ever issued. Before allocating, search `LogMessages.adoc` and the test trees for the candidate id. Treat an id's meaning as a public contract.
