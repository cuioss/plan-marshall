envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:53Z

# Candidate lesson: files citing deleted watch items left under "Files to survey"

- Component: plan-marshall:phase-3-outline
- Suggested category: improvement
- Signal: Q-Gate finding a6ea47 (3-outline, scope_criterion_validator under_coverage, taken_into_account)

## Evidence

- The success criterion for deliverable 8 was "the covered statements and watch items are deleted and
  no reference to them dangles". A content search for PM-WATCH-(DSL-2|DSL-14|STORE-57) found two files
  (workflow-dsl/01-grammar.adoc, 04-ast-node-model.adoc) that cite them but were listed only under
  Files to survey.
- Resolution: both files were moved to Files expected to mutate.

## Suggested correction

When a deliverable deletes specification IDs, the outline derives its mutate list from a content search
for those IDs across the documentation repository, rather than from reading.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-013.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
