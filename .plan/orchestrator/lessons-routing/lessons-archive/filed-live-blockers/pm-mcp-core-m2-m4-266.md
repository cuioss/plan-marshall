envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-14T13:31:54Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan static-verifier-residuals (PLAN-56, pm-mcp-core #66, merged 7981d17), drained 2026-10-14.
> Source inbox message(s): static-verifier-residuals-004.md 
> RECURRENCE of lessons-routing inbox messages already routed by this epic: pm-mcp-core-m2-m4-212, -226, -238, -248 (queued); -040, -174 (archived). Fold into those; this is new evidence from another plan, not a new lesson.

# Candidate lesson: deep-lane outline written without the assessment pass

Plan: static-verifier-residuals (PR plan-marshall/pm-mcp-core#66).
Signal source: Q-Gate finding 93a848 (phase 3-outline, "Missing CERTAIN_INCLUDE assessments
for all deliverables").

## What happened

The plan ran the deep planning lane, but the solution outline was produced with an empty
assessment store (assessment list total_count 0, findings_store_state missing). None of the
affected files of deliverables 1-8 was backed by a CERTAIN_INCLUDE assessment, so the
assessment-coverage check could confirm nothing. The fix recorded 48 assessments after the
fact, one per in-repository affected file.

## Candidate rule

On the deep lane, record the CERTAIN_INCLUDE assessments while discovering the affected files,
before the outline is written and before the Q-Gate runs; an outline whose assessment store is
empty should be refused (or flagged) by the outline step itself rather than surfacing as a
Q-Gate finding that is then satisfied retroactively.

## Suggested owner

plan-marshall phase-3-outline (deep lane step ordering). Classification deferred to the
orchestrator.
