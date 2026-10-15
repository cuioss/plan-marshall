envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T13:50:31Z

# Add a documented verb to drop stale affected_files paths in outline/plan

- component: plan-marshall:phase-3-outline
- category: improvement
- source: plan-retrospective (session-log-and-generations, PR #51)

## Context

After an operator decision at outline, the ADR `pm-runtime/doc/adr/runtime-start/002-sweep-seam-factory-kept-for-the-assembly.adoc`
was renamed to `002-sweep-seam-factory-removed.adoc`. The old path stayed in `references.affected_files`.
The outline leaf and then the 4-plan leaf both reported they could not remove it: `sync-affected-files` only
adds paths, and `manage-references set-list` exists but no phase workflow documents it. The 4-plan leaf
worked around it by passing `--affected-files-count 69` to the manifest compose.

## Root cause

The outline-to-references sync is additive. Neither phase-3-outline nor phase-4-plan has a documented step to
make `affected_files` equal to the outline's current declared set, so a rename or removal leaves a stale entry.

## Proposed action

Make the outline sync reconcile (replace) `affected_files` with the outline's declared set, or document a
`set-list`/prune step in phase-3-outline for re-dispatches that rename or drop files.

## Evidence

- aspect: chat_history_analysis - outline re-dispatch: "The sync only ever adds paths, and replacing the whole list isn't a step in this phase."
- aspect: chat_history_analysis - 4-plan leaf: "The phase has no documented verb to drop ... from references.affected_files."
- aspect: artifact_consistency - declared 69 vs affected_files 70 entries

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `session-log-and-generations-011.md` from plan session-log-and-generations (PLAN-12, #51; Claude Code)
