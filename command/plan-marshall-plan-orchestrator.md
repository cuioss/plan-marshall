---
description: Resumable epic-orchestration skill - decomposes epics into workstreams and staged plans, emits ready-to-run /plan-marshall commands, tracks plan lifecycles, analyzes landings, owns the append-only inbox channel executing plans write their structured messages to, reconciles the persisted orchestrator ledger, and reviews the epic spec corpus - re-grounding staged specs against HEAD into a persisted per-claim verdict field, cross-checking duplication across sibling epics and live plans, and reporting a restart-readiness verdict; orchestrates, never implements
---

Load and run the `plan-marshall-plan-orchestrator` skill via the `skill` tool, then carry out its instructions using the user input below.

User input:

$ARGUMENTS
