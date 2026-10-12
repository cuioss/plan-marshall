envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T13:52:02Z

# Executor went stale mid-session: pre_merge_gate unknown at merge time

Component (suggested): plan-marshall:marshall-steward / plan-marshall:tools-script-executor, category bug (marketplace-owned)
Signal: script-failure at merge time, reported by the orchestrator; not present as a [ERROR] line in this plan's work log

## Observation (orchestrator-reported)

The installed plan-marshall plugin cache advanced during the session, so both the worktree and the main `.plan/execute-script.py` were stale. At merge time `plan-marshall:phase-6-finalize:pre_merge_gate` was unknown to the executor (drift: 1 added, 164 changed). The executor had to be regenerated with `generate_executor.py generate` before branch-cleanup could dispatch the merge (decision log 9bd6eb records the later pre_merge_gate dispatch).

## Candidate directive

Detect executor drift against the installed plugin cache at phase boundaries (at least before branch-cleanup), and either regenerate automatically or stop with a named remedy, instead of failing on an unknown notation in the middle of the merge step. A long finalize (here about nine rounds) makes a mid-session plugin update likely.

Source: plan plan-11-enrolment-store (PLAN-11, PR #30); orchestrator report.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-11-enrolment-store-011.md` from plan plan-11-enrolment-store (PLAN-11, #30; Claude Code)
