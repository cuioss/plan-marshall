envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:42Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: a standing cross-document constraint of the request is applied to every deliverable's affected-files list before the Q-Gate
source_lesson=2026-11-24-07-004
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-24

# phase-3-outline: a standing cross-document constraint of the request is applied to every deliverable's affected-files list before the Q-Gate

Source: Q-Gate finding bd697b, phase 3-outline, scope_criterion_validator, under_coverage, severity warning, resolution taken_into_account.

Observation: the request carried a standing constraint (a changed outcome of a public operation is updated in the Javadoc, the specification table, doc/specification/general.adoc and doc/clients/pm-mcp-core.adoc in the same commit), and the outline Summary repeated it. Deliverable 1 still changed outcomes of commit, worktreeStatus, worktreeRemove and worktreeAdd without listing general.adoc (GDR-GEN-3 row FAILED) or pm-mcp-core.adoc (Concurrent additions, Commit) in its affected files.

Resolution in run: D1 was extended with both files and the change per file.

Pattern note: four of the five outline Q-Gate findings of this plan (bd697b, 16006b, c5341a, c1c7d4) are the same shape: a standing cross-document constraint stated once in the request, not applied per deliverable to the affected-files list. Candidate rule: when a request states a standing "update X, Y, Z in the same commit" constraint, the outline author checks each deliverable against every named document before the Q-Gate runs.

Context: plan plan-20-leftover-fixes-2, PR 69 (merged f7eda4e).


Source: inbox plan-20-leftover-fixes-2-001 (Q-Gate finding bd697b). Recurrence evidence: findings 16006b, c5341a, c1c7d4 of the same plan have the same shape (see 2026-11-18-07-001 and the lessons below).
