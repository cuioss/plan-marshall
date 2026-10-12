envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:08Z

# Candidate lesson: Q-Gate assessment-coverage check always fires on Java deep-lane outlines

Source: Q-Gate finding 77203b (phase 3-outline, resolved accepted by operator).

The 3-outline Q-Gate check 2.2 ("no CERTAIN_INCLUDE assessments recorded for any affected file") fired because the assessment store was empty for all 22 affected files. The Java-domain deep-lane outline path records no per-file assessments at all, so the finding is structural rather than plan-specific and needed an operator acceptance to clear.

Candidate rule / fix direction: either have the Java deep-lane outline record assessments for its affected files, or make the Q-Gate assessment-coverage check aware of outline paths that do not produce assessments, so it does not cost an operator decision on every Java plan.

Scope hint: plan-marshall phase-3-outline Q-Gate (framework), not pm-mcp-core.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-04-service-unit-002.md` from plan plan-04-service-unit (PLAN-04, #25)
