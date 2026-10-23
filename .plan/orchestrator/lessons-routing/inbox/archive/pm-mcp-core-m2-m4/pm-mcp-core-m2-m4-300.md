envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T20:22:08Z

# Candidate lesson: model a path created and deleted within one plan in the intent and footprint checks

Component: plan-marshall (phase-4-plan files_exist Q-Gate, manage-references footprint, plan-retrospective
artifact-consistency / manifest-decisions; version 0.1.1947)
Category: improvement
Source: plan-retrospective of work-package-redistribution

## Context

By this repository's work-package convention, a plan adds its own package file and index row in its first commit
and removes them in its last. Here D1 declared `doc/plans/work-package-redistribution.adoc` as write-new and D12
declared it as delete. Two tools could not represent that:

- At plan time the `files_exist` check would raise an unfixable "delete target missing" finding, because the file
  does not exist before execution. phase-4-plan therefore stamped TASK-13's step with intent `write-replace` and
  told execute in prose to delete the file; execute had to change the stored intent with `update-step` first.
  The same check also warned on D11's read entries for two files that D6 and D7 create.
- After merge, the path is absent from the net diff, so artifact-consistency reports recall 96% with this path
  missing, and manifest-decisions rule M6 fails `declared_vs_realized_set` with it as the only culprit - a false
  positive on a plan that did exactly what it declared.

## Root cause

The intent and footprint checks compare against the base tree and the net diff only; neither knows a path can be
created by one deliverable and consumed or removed by a later one in the same plan.

## Proposed action

- Let files_exist resolve a delete or read target against the write-new paths of earlier deliverables in the same
  plan before flagging it.
- Let the footprint comparison treat a path declared write-new and later delete in the same plan as net-zero by
  design, reported as such rather than as declared-but-unrealized.

## Evidence

- artifact-consistency: affected_files_recall 96.2%, missing doc/plans/work-package-redistribution.adoc
- manifest-decisions: M6 fail, culprit doc/plans/work-package-redistribution.adoc
- phase-4-plan return: "TASK-13 carries intent write-replace, not the declared delete ... files_exist would raise
  a finding nobody can fix"
