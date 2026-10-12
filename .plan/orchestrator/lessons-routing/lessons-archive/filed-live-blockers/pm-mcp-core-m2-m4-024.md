envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:10Z

# Candidate lesson: verification-feedback refuses producer ci-verify-policy (unknown_producer)

- Component: plan-marshall:plan-marshall
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-14-003 (created 2026-10-10), epic pm-mcp-core-m2-m4

- Component: plan-marshall:plan-marshall workflow verification-feedback; plan-marshall:phase-6-finalize ci-verify
- Signal: script-failure cluster (reported by the finalize dispatcher)
- Evidence: dispatcher observation in the finalize run. NOT independently confirmed in this plan's work or
  decision log (those carry no [ERROR] line for it); the record would be in the script-execution log of the
  verification-feedback dispatch at 2026-10-10T06:58:38Z.

## What happened (as reported)

ci-verify emits per-producer needs-triage strings under producer `ci-verify-policy`, but verification-feedback's
accept-set does not contain that producer and returns `unknown_producer`. The documented red-CI triage path
(ci-verify -> verification-feedback) is therefore unreachable. In this run CI was green, so no defect landed
through the gap.

## Suggested direction

Align the producer vocabulary: add `ci-verify-policy` to verification-feedback's accepted producers, or derive
both from one shared constant, and add a contract test that pairs each ci-verify producer string with the
accept-set.

Source: inbox `lock-manager-and-leases-007.md`, plan lock-manager-and-leases (PLAN-01, #20).
