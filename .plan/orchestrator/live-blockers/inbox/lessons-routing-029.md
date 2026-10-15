envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:33:21Z

# Lessons ingest: sibling-repository deliverable lifecycle still breaks across outline, footprint and finalize

Severity: high (prior ruling 2026-10-12: sibling-repo deliverable lifecycle = high; recurrence of `lessons-routing-018`). Bundle: `plan-marshall` (`phase-3-outline`, `phase-4-plan`, retrospective footprint, `phase-6-finalize`).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox messages `-203`..`-286`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-203` | Outline deliverable touching sibling repo used `../` paths and the sibling module; unresolvable from the worktree. Rewritten in-run to absolute sibling checkout, module `none`, own branch/PR/verify there. |
| `pm-mcp-core-m2-m4-213` | Cross-repository deliverable verified by this repository's Maven verify instead of the sibling checkout's command. |
| `pm-mcp-core-m2-m4-240` | Declared sibling-repo paths graded 0% partial by construction in the footprint set (cross-repo treated as unrealised). |
| `pm-mcp-core-m2-m4-265` | Cross-repository deliverables vanish from the task plan (sibling deliverable dropped to verification-only). |
| `pm-mcp-core-m2-m4-285` | Sibling `LogMessages.adoc` drifted; D6 reported 0% coverage from the finalize fix tasks. |

Asked for: the sibling-repo deliverable path (absolute checkout, no own-module, own branch/PR/verify, footprint-exempt, task-planned) holds end to end; check against `-018` for residual.

Owner today: none (nearest: `-018`). Not re-checked at HEAD by the ingest.
