envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T18:35:35Z

component=plan-marshall:plan-marshall
category=improvement

# A harness-killed background build wait is a lost observer, not a lost build: re-attach to the marshalld job before resubmitting

Routed by the API-Sheriff `deployment-configurability` orchestrator on 2026-09-15 while draining PLAN-24's (`release-docs-and-tls-scenario-guide`, PR cuioss/API-Sheriff#305, squash `fb65222`) epic inbox. The originating plan filed these as `candidate-lesson` messages to its API-Sheriff epic; their remedy lives in the plan-marshall bundle, so they are relocated here — the same routing this epic used for `-001`..`-013`. Not re-verified against plan-marshall source by the orchestrator: each is a lead from one plan run. Original message bodies (envelope stripped) are verbatim below.

Origin messages: `release-docs-and-tls-scenario-guide-010`.

Operator's landing paste reports five kills; the lesson body says four. Both agree every kill was recovered by re-attach.

---

## Original `release-docs-and-tls-scenario-guide-010`

component=plan-marshall:plan-marshall
category=improvement
source_finding=operational event (orchestrator-reported), plan release-docs-and-tls-scenario-guide

# Harness killed background build waits four times under low memory; marshalld re-attach recovered each

## What happened

Across this run the harness killed the orchestrator's backgrounded long-running build waits (the await-long-running seam) four times while the machine was under low memory. Each time the build itself kept running in the marshalld build server, and re-attaching to the daemon job recovered the result without re-running the build.

## Corrective action

Treat a killed background wait as a lost observer, not a lost build: on the wake path, re-attach to the marshalld job by id before considering a resubmit. Worth confirming the await-long-running seam and classify-outcome document the daemon re-attach as the first recovery step (and that a kill under memory pressure is not reclassified as a build failure).

## Evidence

- Plan: release-docs-and-tls-scenario-guide (PR #305) — 4 harness kills, 4 successful re-attaches
