envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:28:13Z

# Candidate lesson: a new guard publisher landed without its paired registration row

## Signal source

Q-Gate `5-execute` finding `4f7e38` (severity error, test-failure). `verify plan-marshall` failed: 22295 passed / 1 failed.

## Observation

TASK-016 added `test/plan-marshall/plan-orchestrator/test_inbox_delivery.py`, which publishes `GUARD_POPULATION_LABEL = "mailbox check-point roster rows"` to opt into the `pytest_report_header` population publication. The matching registration row in `_ROUTING_GUARD_MODULES` in `test/conftest.py` was never added.

`test_the_routing_guard_roster_carries_no_drift` detected it: *"1 publisher(s) with no `_ROUTING_GUARD_MODULES` row"*.

## Why it is worth recording as a positive signal too

The finding's own triage text makes the load-bearing distinction: this was *"a genuine registration omission in the plan's own footprint, not a flake and not a pre-existing defect: the guard is population-derived and correctly detected a live publisher missing from the roster."*

That is a population-derived guard working exactly as designed — the inverse of finding `974a5e` in the same plan, where a roster guard would have under-covered silently. The two together are a useful matched pair: the same architectural pattern (roster + publishers + drift check) fails open when it walks one document of two, and fails closed when both directions are pinned.

## Corrective rule

1. **A publisher and its registration row are one edit.** Adding `GUARD_POPULATION_LABEL` to a test module without the `_ROUTING_GUARD_MODULES` row in the same commit is an incomplete change, not a follow-up.
2. This class is cheap to prevent structurally: the drift check already exists and fires. The residual cost is one full `verify` cycle (878s on re-run here) per omission, so the value of catching it at edit time rather than verify time is measurable.
3. When a plan adds a new test module that opts into any shared reporting or routing seam, **enumerate that seam's registration points** as part of the deliverable rather than discovering them from a red build.
