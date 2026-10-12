envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:23Z

# Lessons ingest: in a consumer repository, dispatched leaves cannot resolve their workflow doc

Severity: high (graded at this ingest: every dispatch in every consumer repository meets a contract outcome of `workflow_not_found`; leaves improvise and pick different copies). Bundle: `plan-marshall` (`agents/execution-context.md` Step 4, `extension-api` ext-point-execution-context-workflow).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4`, three plans. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Plan | Statement |
|---|---|---|
| `pm-mcp-core-m2-m4-081` | PLAN-07 (#27) | create-pr, sonar-roundtrip and triage leaves found no file under `marketplace/bundles/…`; each fell back by hand to `plan-marshall/target/claude/…`. |
| `pm-mcp-core-m2-m4-094` | PLAN-36 (#31) | Same for create-pr and sonar-roundtrip. |
| `pm-mcp-core-m2-m4-120` | PLAN-10 (#32) | Three leaves; one read the source tree `plan-marshall/marketplace/bundles/…`, two the built `target/claude/…` — two different trees for the same notation, i.e. a possible stale copy. |

Ground truth at `fc0090a24`: `agents/execution-context.md:111-112` map `{bundle}:{skill}/…` only to `marketplace/bundles/{bundle}/skills/{skill}/…`, and `:119` returns `workflow_not_found` otherwise. **Still present.**

Asked for: resolve the notation through the installed skill base directory (the root the Skill loader reports), with `marketplace/bundles/` as the in-repo fallback, ideally as a script verb so the prompt carries a verified absolute path; state the order in Step 4.

Owner today: none found.
