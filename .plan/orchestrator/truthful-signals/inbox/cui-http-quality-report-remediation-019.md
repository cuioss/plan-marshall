envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T15:50:47Z

component=plan-marshall:plan-orchestrator
category=improvement

# Candidate lesson: a spec that forbids .java edits clashes with review demands for build-time doc checks

- Suggested component: plan-marshall:plan-orchestrator (staged plan spec authoring)
- Suggested category: improvement
- Signal source: automated review and triage
- Evidence: work log f22ebe, "TASK-18/19 are test-scope Java by explicit operator override of the plan's no-.java rule". Work log TASK-018 (LogMessagesDocumentationTest added) and TASK-019 (NfkcFoldClaimInvariantTest rework). Work log 20ac85: CodeQL then raised NumberFormatException findings on those tests, which led to TASK-021 and TASK-022.

## What happened

The PLAN-13 spec allowed only documentation changes and no .java edits. The review bot asked for build-time checks so that hand-maintained doc lists (log-message docs, NFKC fold claims) cannot drift. The operator overrode the spec to allow test-scope Java. The new tests then drew their own CodeQL findings, which needed another loop-back round.

## Why it matters

When a docs-only plan corrects hand-maintained inventories, reviewers will reasonably ask for an executable guard. A blanket no-.java rule turns that request into a mid-run scope override and an extra review round.

## Suggested fix

When staging a docs-reconciliation plan spec, decide up front whether test-scope guards for hand-maintained doc lists are in scope. Allow `src/test/**` explicitly, or route the guards to a sibling plan. Do not leave a blanket no-.java rule.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-13 (cuioss/cui-http #262), inbox message `plan-13-asciidoc-specs-requirements-adrs-006.md`. Routed by the cui-http orchestrator on 2026-10-05 (operator directive: all plan-marshall findings go to `truthful-signals`).
