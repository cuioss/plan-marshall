envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=finding
created=2026-10-12T12:40:44Z

# [HIGH][Antigravity] Token and tool metrics are not recorded at all — every step reads "unmeasured", the landing reports total_tokens=0

- Component: plan-marshall:platform-runtime (runtime-info / transcript collection), plan-marshall:manage-metrics, plan-marshall:manage-execution-manifest (record-step)
- Category: bug

## What happened

Under Antigravity the plan recorded no consumption at all. Every `record-step` line in the decision log reads `total_tokens=unmeasured, tool_uses=unmeasured, duration_ms=unmeasured` (verify:quality-gate, verify:module-tests, ci-verify, automatic-review, sonar-roundtrip). `metrics.md` shows "-" for Worked, Tokens, Tool Uses and Billing in every phase. The landing-facts block carries `total_tokens=0`, and the residue says "Session token consumption recorded as 0 due to transcript-less platform runtime on Antigravity".

## Why it matters

- `total_tokens=0` is a real-looking number and passes `landing-check` as complete. The landing payload spec treats `unknown` as missing, but this is not `unknown`, so a plan with no measurement is indistinguishable from a free one.
- Budget anchors, the dispatch audit and cross-plan comparisons all silently lose this plan.

## Suggested direction

- On a transcript-less runtime, emit `total_tokens=unknown` rather than `0`, so `landing-check` flags it.
- Add a platform-runtime capability flag (`transcripts: none`) that `record-metrics` reports in its header.
- Investigate whether Antigravity exposes usage through any other channel.

- Priority: **HIGH** (operator decision 2026-10-12: Antigravity issues are filed directly as high priority)
- Platform: Antigravity — first plan of epic pm-mcp-core-m2-m4 run under it
- Plan: `plan-41-static-verifier-remaining-rules` (PLAN-41), pm-mcp-core PR #34, merge commit ebe82b3
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-41-static-verifier-remaining-rules/` (logs/, metrics.md, execution.toon, build-results/)
- Origin: filed by the orchestrator of epic pm-mcp-core-m2-m4 from its landing analysis, verified against the archived plan and the PR
