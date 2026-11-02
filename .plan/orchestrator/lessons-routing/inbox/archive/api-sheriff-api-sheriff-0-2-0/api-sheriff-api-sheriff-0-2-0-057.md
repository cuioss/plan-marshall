envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-24T15:38:02Z

# Candidate lesson: the outline value-change sweep misses sibling copies of the invariant a deliverable changes (plan-marshall:phase-3-outline, phase-4-plan)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-23-cookie-forwarding-policy-r2 (PR cuioss/API-Sheriff#515, merge bd730f5a), inbox message(s) plan-v02-23-cookie-forwarding-policy-r2-008 and -009.

The 3-outline Q-Gate raised five under-coverage findings of one shape: a deliverable changed a rule, and sites encoding the OLD rule were in no deliverable's affected files (a test asserting the opposite, package-info and LogRecord text, ADRs with closed enumerations, an IT assertion message, fixtures the new boot rule refuses). After a sweep was added, the 4-plan Q-Gate still found the same stale statement in sibling files (a sibling variants page, two sibling ITs) that the sweep, scoped to the named file, did not reach. Each needed a Q-Gate round and, once, an operator ruling.

Suggested direction: when a deliverable changes an invariant, sweep by CONTENT (the statement and its paraphrases) over the whole repository, record the full hit list including sibling files of the same family, and put every hit in a deliverable or in a "deliberately unchanged, because ..." list. Fixing one named copy is evidence that siblings exist.

Related earlier items: lessons-archive sweep 2026-10-15, pm 246, 264 (construction-site sweep gaps), pm 275, pm 239.
