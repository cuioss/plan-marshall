envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:14Z

# Exclude read-intent files from outline-vs-shipped include_unrealised

**Signal source**: plan-retrospective (outline-vs-shipped, artifact-consistency), finalize step of workflow-dsl-parser-and-ast.

**Component (suggested)**: `plan-marshall:plan-retrospective` (`check-outline-vs-shipped`); possibly also `plan-marshall:phase-3-outline` (assessment recording)

**Category (suggested)**: bug

## Context

outline-vs-shipped reported 17 include_unrealised paths. Five of them (`pm-workflow/.../ast/SourceLocation.java`, `.../ast/LinkRelation.java`, `pm-core/.../spi/OutcomeClass.java`, `pom.xml`, `pm-core/pom.xml`) are read-intent files: the outline and the task steps mark them `read`, and nobody expected them to change. The sibling aspect artifact-consistency excludes exactly this class (`read_intent_excluded: 9`) from its recall denominator, so the two aspects disagree on the same declaration.

## Root cause

The deep-lane outline re-entry recorded one CERTAIN_INCLUDE assessment "for each distinct affected file", read-intent files included (72 + 1 = 73 assessments against 64 modify + 9 read paths). check-outline-vs-shipped treats every CERTAIN_INCLUDE assessment as a forecast modification and does not consult the declared intent.

## Proposed action

In check-outline-vs-shipped, drop assessed paths whose declared intent is `read` from the include_unrealised population (publishing the excluded count, as artifact-consistency does). Optionally, have phase-3-outline record read-intent files with a distinct assessment certainty or skip them.

## Evidence

- aspect: outline_vs_shipped — include_unrealised members include SourceLocation.java, LinkRelation.java, OutcomeClass.java, pom.xml, pm-core/pom.xml
- aspect: artifact_consistency — read_intent_excluded: 9 on the same plan
- TASK-001 steps 24-26 mark SourceLocation, LinkRelation and OutcomeClass as `read`
- Distinct from lessons-capture 010 (that one is about assessments missing on re-entry; this one is about read-intent assessments being graded as unrealised)

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-016.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
