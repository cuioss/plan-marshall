envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:49Z

# references.affected_files cannot drop paths an outline revision replaced

## Observation

The 3-outline fix pass rewrote deliverable 11's six relative `../plan-marshall-documentation/...` paths as absolute paths. `sync-affected-files` is add-only, so the six stale relative entries stayed in `references.affected_files` (58 entries vs 53 declared) and there is no verb to remove them. Every later consumer of the declared footprint (artifact consistency, manifest cross-check, scope checks) then compares against a list containing paths that no deliverable declares any more.

## Suggested direction

Give `sync-affected-files` a reconcile mode that replaces the list with exactly the outline's current declared set (reporting added and removed paths), or add a `remove-affected-files` verb; have the outline revision path call the reconcile mode.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-022.md` from plan runtime-lifecycle (PLAN-08, #29)
