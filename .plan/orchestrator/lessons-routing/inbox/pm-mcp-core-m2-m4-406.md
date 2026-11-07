envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T14:28:24Z

component=plan-marshall:workflow-integration-sonar
category=improvement
source_plan=pm-mcp-core:plan-v2-98-optional-conversion-workflow

# Give sonar-roundtrip a branch for configured Sonar without host credentials

## Context

In 6-finalize of pm-mcp-core PLAN-V2-98 the sonar-roundtrip step failed with "sonar new-code count undecidable: no credentials configured". The project has SonarCloud configured and the PR carried a Sonar quality-gate comment, but this host has no producer credentials. The step's Branch C wording does not describe "configured but no credentials on this host", so the operator closed it with a plain-HTTP read of the public API (0 open issues on the PR, gate OK); the step recorded `work_performed: false`.

## Root cause

sonar-roundtrip assumes producer credentials are present whenever Sonar is configured; the no-credentials case falls into a branch written for a different situation.

## Proposed action

Add an explicit branch for "Sonar configured, no producer credentials on this host": read the PR's open issues and quality gate through the unauthenticated public API (as `read_open_issues` does for a plan-less caller) and record the result with its provenance, or ask the operator with that option named.

## Evidence

- status.metadata.halts.6-finalize.sonar-roundtrip: outcome failed, reason "no credentials configured"
- phase_steps sonar-roundtrip display_detail "no producer creds; plain-HTTP read: 0 open on PR, gate OK"
- operator report at finalize
