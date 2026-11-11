envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-11-09T16:24:23Z

Routed by the API Sheriff epic `kidicap-gateway-requirements` (standing operator rule 2026-10-15: plan-marshall-related findings go to lessons-routing). Origin: plan `plan-29-upstream-inert-keys`, API Sheriff PR #586 (merged 2026-11-09, ab568dab), plan-marshall 0.1.2088. The orchestrator verified the PR and CI state, not the plan-marshall-internal claims (Q-Gate finding contents) below; treat those as the plan lane's own report.

# Candidate lesson: outline declared ADR-0008 untouched, but amending ADR-0064 made it stale

Source record: Q-Gate finding ccb806 (phase 6-finalize, rule code-review, severity error, resolution
taken_into_account; code review closed at 90ada9d7e1435d8ea7ac67b10a40ba9046435804).

## What happened

The code review found doc/adr/0008-data-plane-transport.adoc:48 still saying ADR-0064 leaves the four upstream
timeout and retry keys open, after the plan's ADR-0064 amendment removed them. The outline had listed
ADR-0008 as untouched. Per the orchestrator's run notes, the fix forced a loop-back, an operator-authorized
acceptance-criterion reword, and a full re-run of the earlier HEAD-dependent finalize steps.

## Candidate rule

When a plan amends an ADR, the outline must sweep for every other ADR (and doc) that cites the amended ADR's
claim before declaring those documents untouched. "Untouched" is a claim about inbound references, not just
about the files the deliverable edits.

## Possible corrective surfaces (for orchestrator classification)

- phase-3-outline: when a deliverable amends ADR-N, run a content search for references to ADR-N and list
  each hit as affected or explicitly justified-untouched.
- The late discovery cost was high because it happened after HEAD-dependent steps had run; catching it at
  outline time avoids the loop-back and re-run.
