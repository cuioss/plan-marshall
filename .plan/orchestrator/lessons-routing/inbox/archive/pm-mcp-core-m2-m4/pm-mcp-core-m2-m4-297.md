envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T20:22:07Z

# Candidate lesson: read-only inputs created by other deliverables were missing from affected files

Source: Q-Gate finding 46f50b (phase 4-plan, scope_criterion_validator under_coverage, severity warning, resolved: fixed).

## What happened

Deliverable 11's success criterion ("72 bullets after; 6, 11, 8, 12 merged and 9, 12, 7, 7 split") was
operationalized as a directory_enum over eight package files, but the deliverable's affected files listed only
seven read files. It omitted `doc/plans/start-source-intake.adoc` and `doc/plans/epic-resource-and-release.adoc`,
which its own "Change per file" text said are read and counted, and which deliverables 6 and 7 create.

## Resolution in this plan

The outline and the task plan were rebuilt: deliverable 11 lists all nine read files (the eight counted package
files plus README.adoc as a documented read-only extra), and TASK-12 names the same nine.

## Candidate rule

When a deliverable's verification counts or reads files, list every one of them as a (read) affected file,
including files that only come into existence through an earlier deliverable; the counted population of a
success criterion must equal the read set the deliverable declares.
