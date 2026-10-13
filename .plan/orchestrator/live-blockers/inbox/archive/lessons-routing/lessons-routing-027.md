envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-13T08:10:57Z

# [HIGH] CodeRabbit concerns raised only in its summary comment are never filed — security concerns included

- Severity: **high** (operator ruling 2026-10-13).
- Bundle: `plan-marshall` — `automatic-review` (CodeRabbit registry), `workflow-integration-github` (`fetch_findings` producer).
- Source: pm-mcp-core PLAN-18 `verify-not-resolve`, PR #43 (Claude Code). Message `pm-mcp-core-m2-m4-171`; full body at `lessons-routing/lessons-archive/filed-live-blockers/pm-mcp-core-m2-m4-171.md`.

## What happened

CodeRabbit raised review defects and two security concerns, some of them only inside its summary/walkthrough comment, not as inline threads. `fetch_findings` filed nothing for those; they were found by reading the summary by hand. The findings count read complete.

## Verified at `0c87ca07b`

`marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` lines 59–61 list `<!-- This is an auto-generated comment: summarize by coderabbit.ai -->` and `## Walkthrough` under `ignore_patterns`, and § "Producer stage" (line 127) states these are whole-comment drops for "CodeRabbit comments that carry no per-line finding". `github_pr.py` applies them in pre-filter 4 (`_is_obvious_noise`), counted only into `skipped_noise`. No code reads the summary body for actionable, "Outside diff range" or security sections. The premise that the summary carries no finding does not hold.

## Asked

Parse the summary/walkthrough body for actionable and security items and file them, or at least report that a dropped summary carried such items rather than counting it as noise. A fixture with a summary-only security concern pins it. Not owned by any staged plan; nearest is PLAN-LB-31 (in-house reviewer) or the remainder of `lessons-routing-017`.
