envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:52Z

# Candidate lesson: A deliverable that deletes a specification section must name every pointer to that section in the other deliverables

- Component: plan-marshall:phase-3-outline
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-002 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Quality-check finding 68267b (phase 3-outline, severity warning) of plan primitive-spi-and-validators, resolved `taken_into_account` on 2026-10-09 by one re-run of the outline.

## What happened

Deliverable 6 deletes the specification sections its coverage table marks covered, among them "Primitive SPI Contract" in `doc/specification/workflow-dsl/05-primitives.adoc`. `pm-core/src/main/java/de/planmarshall/core/spi/package-info.java` line 16 pointed at exactly that section. Deliverable 2 listed the file as write-replace, but its change text only extended the Javadoc; it did not say the pointer is removed, although the same deliverable stated for `Primitive.java` that Javadoc names the requirement and never a specification anchor. The outline would have left a dead reference.

## Fix applied

The change text of deliverable 2 for `package-info.java` now states that the line naming the specification file and section is replaced by a pointer to the requirement PM-IMPL-5.

## Proposed rule

When one deliverable deletes or renames a document section, the outline searches the affected files of all deliverables for references to it and states the removal or replacement in the change text of the deliverable that owns each referencing file.

## Not closed by this plan

The finding also names `pm-workflow/src/main/java/de/planmarshall/workflow/primitive/package-info.java` line 13, which names the same specification file without a section. It was out of scope and stays valid only as long as that file keeps sections.

## Evidence

- Finding 68267b and its resolution detail of 2026-10-09T21:46:42Z.
- Decision log 86a6f6 (deliverable 2: fail), b511a7, 5da8cc.
