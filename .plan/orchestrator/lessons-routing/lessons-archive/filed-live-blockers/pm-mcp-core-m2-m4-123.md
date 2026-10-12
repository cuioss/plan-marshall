envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T05:32:01Z

# The deep-lane outline recorded no file assessments

Source: plan-retrospective of static-verifier-and-fuzzer (outline-vs-shipped aspect: `assessments_store_present: false`, 0 assessments, 28 of 28 shipped paths unassessed); q-gate-validation pass 1 finding 8b07d8.

## What happened

The plan ran the deep planning lane, but phase-3-outline wrote no CERTAIN_INCLUDE / CERTAIN_EXCLUDE assessments at all (`findings_store_state: missing`). q-gate-validation then flagged all 7 deliverables on that alone, although every file existed and every deliverable matched the request. The retrospective's outline-vs-shipped comparison has nothing to compare: every shipped path reads as "touched but unassessed".

The outline itself was sound; only the assessment record was missing. Either the deep lane skipped its assessment step for a greenfield package (the verify package held only `package-info.java`), or it has no assessment step when no domain outline skill applies (`no_domain_skill`, generic change-feature instructions were used).

## Candidate rule / fix

Make the deep lane's assessment step unconditional (record assessments for every declared file, including `write-new` ones), or have it record an explicit "assessment skipped: greenfield" marker that q-gate-validation and outline-vs-shipped accept instead of a missing store. Owner: plan-marshall `phase-3-outline` (deep lane, generic change-feature path).

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-and-fuzzer-010.md` from plan static-verifier-and-fuzzer (PLAN-10, #32)
