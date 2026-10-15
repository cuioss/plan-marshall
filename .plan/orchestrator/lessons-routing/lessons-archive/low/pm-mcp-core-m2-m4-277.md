envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:47Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-013.md
> NEW for the execute phase; related to -243 (factual claims checked against the code). The documentation copies of the same claim (014-017) are folded into pm-mcp-core's own lesson 2026-10-11-20-001 and are not routed. Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Residual: runtime.audit wrote into the log through two paths, contradicting the outline

- Source: Q-Gate record f12251 (6-finalize, functional-review, error, residual at D4.R1), resolution `taken_into_account` (closed at f35a61c after TASK-13).
- Suggested component: `plan-marshall:phase-5-execute` / project-local (runtime.audit).

## Observation

D4 success criterion 3 said runtime.audit writes into the audit log only through `AuditLog.appendCheckpoint`; the implementation also called `AuditLog.append` from `AuditRotation.rename` (AuditRotation.java:249). Execute and its quality sweeps passed; only functional review found it.

## Candidate rule

"Sole path" / "only through" claims in an outline are verifiable invariants; the implementing task should check them mechanically (search for every call site of the guarded writer) before marking done.
