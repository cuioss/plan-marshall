envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T18:35:32Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# Phase 3-outline: assessments, verification lanes and search criteria written ahead of the evidence, and a self-transition that orphaned its own q-gate findings

Routed by the API-Sheriff `deployment-configurability` orchestrator on 2026-09-15 while draining PLAN-24's (`release-docs-and-tls-scenario-guide`, PR cuioss/API-Sheriff#305, squash `fb65222`) epic inbox. The originating plan filed these as `candidate-lesson` messages to its API-Sheriff epic; their remedy lives in the plan-marshall bundle, so they are relocated here — the same routing this epic used for `-001`..`-013`. Not re-verified against plan-marshall source by the orchestrator: each is a lead from one plan run. Original message bodies (envelope stripped) are verbatim below.

Origin messages: `release-docs-and-tls-scenario-guide-001`, `release-docs-and-tls-scenario-guide-002`, `release-docs-and-tls-scenario-guide-003`, `release-docs-and-tls-scenario-guide-008`.

Four observations from one outline run. Three are authoring discipline (record CERTAIN_INCLUDE assessments before q-gate; a deliverable's Verification Command must exercise the lane its criteria name; run a 'search returns only Y' criterion's search at outline time). The fourth (`-008`) is a lifecycle bug: phase-3-outline advanced to 4-plan itself before 3-outline q-gate validation, so its findings were filed against a phase already left and would have been silently dropped.

---

## Original `release-docs-and-tls-scenario-guide-001`

component=plan-marshall:phase-3-outline
category=anti-pattern
source_finding=qgate 3-outline eb29c6 (taken_into_account)

# Deep-lane outline reached q-gate with zero CERTAIN_INCLUDE assessments recorded

## What happened

The phase-3-outline deep lane wrote a 10-deliverable solution outline but never wrote the assessment store (`findings_store_state: missing`). The q-gate assessment-coverage check could not pass and the assessed-but-undeclared (missing-coverage) check could not be evaluated at all. The fix was in-run: 26 CERTAIN_INCLUDE assessments were recorded after the q-gate fired.

## Corrective action

Record CERTAIN_INCLUDE assessments for every write-new / write-replace path and files-expected-to-mutate BEFORE the outline is submitted to q-gate; do not rely on q-gate to prompt the assessment pass. Read-only reference and survey-only files are not assessed as includes.

## Evidence

- Plan: release-docs-and-tls-scenario-guide (PR #305, merged fb65222)
- Finding hash: eb29c6, phase 3-outline, severity warning

---

## Original `release-docs-and-tls-scenario-guide-002`

component=plan-marshall:phase-3-outline
category=anti-pattern
source_finding=qgate 3-outline 8c18c6 (taken_into_account)

# Deliverable verification command omitted the profile lane its own criteria required

## What happened

Deliverable 9 edited `api-sheriff/src/main/docker/Dockerfile.native.jfr`. Its criteria required the `jfr` profile lane to build `api-sheriff:jfr` and `ImageMetadataJfrIT` to pass, but its Verification Command was only `verify -Ppre-commit` — a gate that builds neither that image nor runs that IT. The lane was left as prose ("profile invocation taken from integration-tests/pom.xml"), so phase-4 could derive a verification step that never exercised the deliverable's only changed build input.

## Corrective action

When a deliverable's criteria name a build lane (profile, image, IT), its Verification Command must be the concrete executor invocation for that lane (here `verify -Pjfr -pl integration-tests -am`), with the profile id read from the owning pom and any image precondition stated. Check each criterion against the command: a criterion no command exercises is unverified.

## Evidence

- Plan: release-docs-and-tls-scenario-guide (PR #305)
- Finding hash: 8c18c6, phase 3-outline
- Related operational follow-on: the jfr lane itself then went red on a stale local distroless image (separate candidate).

---

## Original `release-docs-and-tls-scenario-guide-003`

component=plan-marshall:phase-3-outline
category=improvement
source_finding=qgate 3-outline 444e7e (taken_into_account)

# Search-based exclusion criterion was written before running the search it describes

## What happened

Deliverable 6's criterion said a content search for `0\.1\.[01]` over operator-facing docs "returns only historical records (ADRs, quality-report, context-path-verification)". Running that exact search (`architecture search --content --pattern '0\.1\.[01]' --category doc`, 14 hits over 99 files) showed two further legitimate historical hits not on the list (`doc/user/container-image.adoc` certificate evidence, `doc/development/release-process.adoc` positive-control run) and one listed file (context-path-verification) that produced no hit. A verifier applying the criterion literally would have failed the deliverable. The survey also surfaced a genuinely stale passage (container-image.adoc lines 296-299), which moved into the mutate set.

## Corrective action

When a criterion is phrased as "search X returns only Y", run the search at outline time and write the allow-list from its actual result: every hit either listed with the specific passage that justifies it, or scheduled for mutation. Drop allow-list entries that produce no hit.

## Evidence

- Plan: release-docs-and-tls-scenario-guide (PR #305)
- Finding hash: 444e7e, phase 3-outline, severity info

---

## Original `release-docs-and-tls-scenario-guide-008`

component=plan-marshall:phase-3-outline
category=bug
source_finding=operational event (orchestrator-reported), plan release-docs-and-tls-scenario-guide

# phase-3-outline self-transitioned to 4-plan before q-gate validation; its findings were never consumed

## What happened

The phase-3-outline agent advanced the plan to `4-plan` itself, before the orchestrator's q-gate-validation for 3-outline ran. The 3-outline q-gate findings (eb29c6, 8c18c6, 444e7e) were then filed against a phase the plan had already left, and phase-4-plan does not read 3-outline q-gate findings, so they would have been silently dropped. The orchestrator had to manually re-open 3-outline, resolve the findings, and re-run 4-plan.

## Corrective action

The outline agent must return to the orchestrator without calling the phase transition; the transition to 4-plan belongs after q-gate validation reports zero pending findings. As a structural guard, the 3-outline -> 4-plan transition (or phase-4-plan entry) should refuse while any 3-outline q-gate finding is `pending`.

## Evidence

- Plan: release-docs-and-tls-scenario-guide (PR #305)
- Affected findings: eb29c6, 8c18c6, 444e7e (all resolved only after the manual re-open)
