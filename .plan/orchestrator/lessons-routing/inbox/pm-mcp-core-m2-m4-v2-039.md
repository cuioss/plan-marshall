envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T13:43:24Z

component=plan-marshall:phase-6-finalize
category=improvement

# Let sonar-roundtrip settle a docs-only PR without an operator question

## Context

In plan-v2-155 (six .adoc files) the CI `skip-on-docs-only` setting skipped the build and Sonar jobs, so SonarCloud never analysed PR #524. The sonar-roundtrip step treats an unconfirmed count as failure, which would have halted the run with no way to clear it, so it put a question to the operator; the operator first answered "recreate pr and check then" and only after a second question chose "record Sonar as not analysed". The manifest had also kept pre-push-quality-gate on an unknown build verdict, which cost a second operator question.

## Root cause

The step does not read the build-decision / docs-only skip that the rest of finalize already knows, so a skip by design looks like a missing result.

## Proposed action

When the build decision is `not_necessary` (docs-only footprint) and CI skipped the Sonar job by configuration, record sonar-roundtrip as `not analysed (docs-only)` without asking; likewise drop pre-push-quality-gate once the footprint resolves docs-only.

## Evidence

- aspect: chat-history-analysis — two operator gates on Sonar, one on the pre-push gate
- aspect: manifest-decisions — pre_push_quality_gate_inactive kept the gate on "plan footprint unresolvable" at compose time
