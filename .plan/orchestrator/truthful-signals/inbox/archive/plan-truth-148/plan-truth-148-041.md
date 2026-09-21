envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:13Z

# Candidate lesson: an overview diagram numbered 10 boxes for 11 deliverables

- source_signal: qgate / 3-outline
- record_id: 6f4ea7
- component: solution-outline-overview
- resolution: taken_into_account — recorded, not corrected (the outline is a consumed planning artifact and all 11 deliverables executed)

## What happened

The Overview rendered a dependency graph labelled D1-D10 while the Deliverables section numbered 1-11. From deliverable 5 onward the two disagreed: one box covered three deliverables, another covered two, and deliverable 7 had no identity of its own. A reader following the graph mis-maps every dependency edge from 5 onward.

## Candidate rule

When an outline's diagram keeps the REQUEST's numbering while the Deliverables section renumbers, the two identifier spaces silently collide. Either renumber the diagram to the deliverable numbering or state in the Overview that the diagram deliberately uses the request numbering — an unlabelled dual numbering is a dependency-graph misread waiting to happen.
