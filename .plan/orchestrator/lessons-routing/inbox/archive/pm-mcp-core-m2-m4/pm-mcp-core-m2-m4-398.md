envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:31Z

component=plan-marshall:phase-5-execute
category=anti-pattern
created=2026-10-21
bundle=plan-marshall

# Correcting a specification rule needs a sweep of every document that restates it

Correcting one rule — here the axis binding moving from first use to the plan's start —
requires finding every document that RESTATES the rule, not only the document that
defines it. The definition site was corrected in the first pass; review then found three
successive waves of restatements across nine files:

- wave 1 (15:44Z, Q-Gate e9118e): `doc/Traceability.adoc:418` (PM-WF-25 and its trace
  record) and the state catalogue still stated the removed rule.
- wave 2 (16:02Z, Q-Gate 77aa9a): four more normative documents still carried the removed
  rule in their start-event summaries; fixed in 1e9da87.
- wave 3 (TASK-009, 17:24Z): `doc/specification/workflow-dsl/09-plan-instance.adoc` and
  ADR 017 still needed correction; the code review also caught ADR 030's related "only
  two ids are read outside this package" undercount.

The document families that mattered were not obvious from the definition site: normative
specification, state catalogue, traceability rows, `doc/plans/*.adoc`, ADRs, and developer
guides each restated the rule in their own vocabulary.

## Solution

Run the sweep as one enumerated pass over the old rule's distinctive phrasing ("first
use", "bound at", "axis binding") across the whole documentation surface, and read a
review wave that finds another restatement as evidence that the search scope was too
narrow — not as evidence that the correction is nearly done. Close the pass only when a
content search for the removed phrasing returns nothing outside the sites that
deliberately describe the change.

Adjacent finding worth folding into the same pass: prose that says "at each axis call
site" must be narrowed to "at each KEPT axis call site" when the implementation prunes
call sites before composing (09-plan-instance.adoc:82) — a restatement can also be too
permissive, not only stale.

## Impact

Any specification correction whose rule is quoted downstream: traceability records, state
catalogues, ADRs, and plan documents all restate normative rules and none of them
contains the definition.
