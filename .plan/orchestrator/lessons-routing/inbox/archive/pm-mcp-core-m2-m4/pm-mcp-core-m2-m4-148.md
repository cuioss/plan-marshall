envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=finding
created=2026-10-12T18:39:03Z

# [HIGH][opencode] Metrics, phase boundaries and finalize build logs missing; harness not recorded (recurrence of the Antigravity findings)

- Component: plan-marshall:platform-runtime, plan-marshall:manage-metrics, plan-marshall:manage-status (phase boundaries), plan-marshall:build-maven (build-results archiving), plan-marshall:plan-orchestrator (`preflight` / client.toon)
- Category: bug

## What happened

- `total_tokens=0` ("transcript-less").
- `total_wall_seconds=192` covers phase 1-init only; later phases are unclosed.
- The executor log shows five finalize builds (14:58, 15:00, 15:02, 15:02 and 16:32Z, after the last commit), but **none of their logs is in the archived `build-results/`**. Only the execute builds, up to 14:46Z, are there. So the gates that ran on the pushed head cannot be shown.
- No `client.toon` or other harness stamp. opencode appears only in `work/fragment-chat-history-analysis.toon`.

## Why it matters

The same gaps as the Antigravity findings `pm-mcp-core-m2-m4-124.md`, `-125.md` and `-132.md`, now on a second harness: this is a non-Claude-Code platform problem, not an Antigravity quirk. The orchestrator cannot verify gate claims, cannot compare costs, and cannot tell harnesses apart mechanically.

## Suggested direction

- `total_tokens=unknown` instead of `0`.
- Phase closure enforced.
- Finalize build logs archived beside the execute ones.
- The harness stamped at phase-1-init into `status.json` and a landing-facts key.

- Priority: **HIGH** (filed like the Antigravity findings; first plan of epic pm-mcp-core-m2-m4 run under opencode)
- Platform: opencode
- Plan: `plan-44-static-verifier-rule-gaps` (PLAN-44), pm-mcp-core PR #38, merge commit 6caa663
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-44-static-verifier-rule-gaps/`; orchestrator landing record `landings/PLAN-44.md` of epic pm-mcp-core-m2-m4
- Origin: filed by the orchestrator of epic pm-mcp-core-m2-m4 from its extended landing analysis (independent code audit, key claims re-checked by hand)
