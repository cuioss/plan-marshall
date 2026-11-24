envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:45Z

component=plan-marshall:phase-6-finalize
category=improvement
title=quality-gate hand-back: a file-rewriting -Ppre-commit run leaves a dirty tree no leaf owns, and the commit verb assumed a staged index (UNCONFIRMED)
source_lesson=2026-11-24-07-011
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-24

# quality-gate hand-back: a file-rewriting -Ppre-commit run leaves a dirty tree no leaf owns, and the commit verb assumed a staged index (UNCONFIRMED)

**Unconfirmed.** The message states that the commit failed on an unstaged index; the work and decision logs of the plan do not record it. Treat it as a lead to check, not as a settled defect.

Source: reported by the orchestrator for this run, partly confirmed by the plan logs.

In the logs:
- signal-scan reports verification_handback_rows: 2 (prescribed hand-backs, not counted as failures).
- 2026-11-23T22:44:09Z decision: "Whole-tree verify:quality-gate resolves per_task live, but is handed back to the orchestrator per the dispatch instruction (verification_handback), not run in the leaf."
- 2026-11-23T22:26:36Z decision: inline triage edits were committed as b8e378c and the push was deferred because HEAD had moved past the pre-push-quality-gate stamp.

Reported fact, NOT confirmed in the work or decision log: after the handed-back quality gate (the -Ppre-commit profile rewrites files: license headers, OpenRewrite recipes), the resulting changes had to be committed by the orchestrator, and the commit verb failed because the changed files were not staged in the index.

Observation: a hand-back that runs a file-rewriting gate leaves a dirty tree that no leaf owns. The commit path assumed a staged index.

Candidate rule (for the orchestrator to classify): after a handed-back -Ppre-commit run, stage the rewritten paths before calling the commit verb, or let the commit verb stage the gate's own outputs. Check whether the commit verb is meant to stage on its own.

Context: plan plan-20-leftover-fixes-2.


Source: inbox plan-20-leftover-fixes-2-016.
