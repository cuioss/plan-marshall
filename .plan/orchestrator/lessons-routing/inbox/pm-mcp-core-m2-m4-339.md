envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:51Z

component=plan-marshall:phase-3-outline
category=improvement
created=2026-10-18

# A deliverable that deletes a file must list the files that link to it

## Context

Deliverable 11 of plan-20-job-runner deleted doc/plans/job-runner.adoc. The outline listed doc/plans/README.adoc as affected but not doc/plans/slots-usage-and-budgets.adoc, whose line 15 links to the deleted file, nor pm-core core/analysis/package-info.java, which points at a specification section the same deliverable removes. The 4-plan scope_criterion_validator caught the gap (finding bb28fe: content search for the literal file name found 2 referrers) and the operator had to answer a plan-gap question to add both files.

## Root cause

The outline treats a deletion like an edit: it lists the file and its index, but runs no inbound-reference search. The broken link would only have shown up as BROKEN LINKS > 0 after execution.

## Proposed action

In the outline step, when a deliverable deletes or renames a file or removes a section, run architecture search --content for the file name (and the section anchor) and add each referrer to Affected files with a change-per-file entry, or record why it is excluded. The 4-plan validator then confirms instead of discovers.

## Evidence

- qgate 4-plan bb28fe (scope_criterion_validator under_coverage, resolution taken_into_account after an operator question)
- chat_history_analysis pivot 2: "plan gap answered: add doc/plans/slots-usage-and-budgets.adoc and core/analysis/package-info.java to deliverable 11"
