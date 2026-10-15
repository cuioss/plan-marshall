envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:45Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-005.md plan-09-audit-trail-010.md
> RECURRENCE of -212, -226, -238, -248, -266. Two messages merged: 005 (first outline) and 010 (the revision path repeats the gap within the same plan). Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Outline authored without the assessment pass (no CERTAIN_INCLUDE assessments)

- Source: Q-Gate record c93d13 (3-outline, warning), resolution `taken_into_account`.
- Suggested component: `plan-marshall:phase-3-outline` (deep lane).

## Observation

The first outline (6 deliverables, deep lane) was written with an empty assessment store (`findings_store_state: missing`), so validator 2.2 found no CERTAIN_INCLUDE assessment backing any affected file. The author then recorded one assessment per file after the fact. A follow-up record (4d7b10) shows the same gap recurring when the revised outline added two more files.

## Candidate rule

The deep-lane outline should record its CERTAIN_INCLUDE assessments while selecting affected files, not after Q-Gate asks for them; and every outline revision that adds an affected file must add its assessment in the same edit.

---

# Revised outline added files without their CERTAIN_INCLUDE assessments

- Source: Q-Gate record 4d7b10 (3-outline, warning, pm-core/src/test/.../store/EnrolmentStoreTest.java), resolution `fixed` (assessments 1f6f5e, e4f405).
- Suggested component: `plan-marshall:phase-3-outline` (revision path).

## Observation

The revision that resolved f9ad42 added `OwedAuditEvents.java` (read) and `EnrolmentStoreTest.java` (write-replace) to deliverable 2's affected files without recording assessments for them, so validator 2.2 fired again and cost another Q-Gate round. Recurrence of c93d13 within the same plan.

## Candidate rule

The outline revision path must record an assessment for every affected file it adds in the same edit (same rule as c93d13, applied to revisions).
