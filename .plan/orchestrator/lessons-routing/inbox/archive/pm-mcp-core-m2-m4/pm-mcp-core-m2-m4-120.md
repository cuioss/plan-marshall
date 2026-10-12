envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T05:32:00Z

# Dispatched leaves cannot find their workflow doc in a consumer repository

Source: plan-retrospective of static-verifier-and-fuzzer (chat-history aspect); hand-back reports of q-gate-validation, sonar-roundtrip and verification-feedback.

## What happened

The execution-context dispatcher resolves a `workflow` notation such as `plan-marshall:plan-marshall/workflow/q-gate-validation.md` to `marketplace/bundles/{bundle}/skills/{skill}/...` relative to the working tree. pm-mcp-core is a consumer repository with no `marketplace/` tree, so that path does not exist. Three separate leaves in this plan hit it:

- q-gate-validation read the doc from `/Users/oliver/git/plan-marshall/marketplace/bundles/...`.
- sonar-roundtrip read it from `/Users/oliver/git/plan-marshall/target/claude/plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md`.
- verification-feedback failed its first Read, then used the `target/claude/...` copy.

Each leaf chose its fallback by its own judgement, and two of them chose different trees (source vs built target). The dispatcher contract says a missing doc must return `workflow_not_found`; the leaves improvised instead, which is the right outcome by luck, not by contract.

## Candidate rule / fix

Resolve the workflow notation against the installed skill base directory (the same root the Skill loader reports as "Base directory for this skill"), not against `marketplace/bundles/` under the working tree. Until then, state the fallback order in the execution-context Step 4 table so every leaf picks the same copy. Owner: plan-marshall `execution-context` / `extension-api` (ext-point-execution-context-workflow).

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-and-fuzzer-007.md` from plan static-verifier-and-fuzzer (PLAN-10, #32)
