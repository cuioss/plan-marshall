envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:01:25Z

component=plan-marshall:marshall-orchestrator
category=anti-pattern

# A staged spec's central premise expires — re-measure it at outline, do not inherit it

PLAN-110's spec stated, confidently and with a count, that "~8 tests fail spuriously because nothing stubs the daemon routing probe." At outline the plan re-measured and found the premise **already false at the time the spec was staged**: both named modules patched `factory._route_to_daemon` inline, landed in `aafcd1928` / PR #949 *before* the spec was written into the epic ledger.

The spec's declared dependency was stale in the same way: it named PLAN-105 as a prerequisite, but the ledger's PLAN-105 is `closed-superseded` and is about something else entirely (the dispatched-leaf search primitive), not daemon routing.

This is the `truthful-signals` theme turned on the orchestrator's own artifacts: **a confidently-worded spec whose measured claims had expired.** The spec read as evidence because it carried a number.

## Solution

Treat every measured value in a staged plan spec as a **lead, not evidence**. The re-measure is an obligation of outline, not an optional sanity check:

1. At outline, re-run the measurement the spec asserts. If the spec says "N tests fail", run them and count.
2. Re-resolve every declared dependency against the *current* ledger state — a `closed-superseded` prerequisite is not a prerequisite, and a superseded id may have been reassigned to unrelated work.
3. When the re-measure contradicts the spec, the re-measure wins and the divergence is reported back to the epic. Do not silently re-scope, and do not proceed on the spec's numbers.

## Impact

Applies to every orchestrated plan launched from a staged spec. The staleness window is the gap between spec authoring and plan execution — in this case long enough for the target defect to be fixed by an unrelated PR. Reinforces the existing standing rule; this is a concrete recurrence with a named commit (`aafcd1928` / #949) and a stale-dependency second axis (the PLAN-105 reference) that the standing rule did not previously cover.
