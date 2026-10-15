envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T18:29:08Z

# Per-package ADR numbers collide with sibling plans landing during finalize; the pre-merge ADR gate does not see them

## What happened

Plan 39 backfilled ADRs into per-package ADR directories (e.g. `pm-core/doc/adr`, `pm-runtime/doc/adr`, `pm-workflow/doc/adr`). While it was in finalize, sibling plans landed on main with their own per-package ADRs under the same numbers (#51 core-store/runtime-start, #54 workflow-verify). Git reported no conflict because the files had different slugs (`NNNN-a.adoc` vs `NNNN-b.adoc`). The pre-merge ADR gate (`manage-adr scan`) walks only the root `doc/adr`, so it missed the duplicates in the per-package directories. They were found by hand and fixed by renumbering twice, each time through a 5-execute loop-back.

## Rule

- The ADR duplicate-number check must walk every ADR directory in the repository (root and per-module `doc/adr`), not only the root one.
- Right before merge (after any rebase onto a moved main), re-run the duplicate-number check against the merged tree. Do not trust git's conflict detection for numbered files that have different slugs.
- When ADR numbers are allocated per directory and sibling plans in the same epic write to the same directories, the orchestrator should reserve or partition number ranges, or the numbers should be allocated at merge time.

## Evidence

Two renumbering loop-backs in plan-39-module-readmes-and-adrs, against PRs #51 and #54 that landed during its finalize.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-39-module-readmes-and-adrs-001.md` from plan plan-39-module-readmes-and-adrs (PLAN-39, #53; Claude Code)
