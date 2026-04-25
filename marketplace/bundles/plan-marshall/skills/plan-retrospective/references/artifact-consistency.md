# Aspect: Artifact Consistency

Cross-checks between plan artifacts to catch drift, missing files, and mismatched counts. Facts come from `check-artifact-consistency.py`; this document tells the LLM how to judge the facts.

## Inputs

The script consumes:
- `status.toon` (phase position, metadata)
- `solution_outline.md` (deliverables section)
- `references.json` / `references.toon` (modified_files, domains)
- `tasks/TASK-*.json` (task step targets)
- `metrics.md` (when present)

## TOON Fragment Shape

```toon
aspect: artifact_consistency
status: success
plan_id: {plan_id}
files_present{name,present,path}:
  status.toon,true,...
  solution_outline.md,true,...
  references.json,true,...
  metrics.md,false,...
checks[*]{name,status,message}:
  solution_outline_sections,pass,"all required sections present"
  deliverable_count,pass,"6 deliverables declared"
  task_deliverable_match,pass,"6 tasks linked to 6 deliverables"
  affected_files_recall,partial,"5/6 expected files found in references.json"
  metrics_generated,fail,"metrics.md not found (record-metrics skipped?)"
findings[*]{severity,message}:
  error,"metrics.md missing — record-metrics step did not run"
  warning,"1 expected file missing from references.json"
summary:
  passed: N
  failed: N
  partial: N
```

## Novel Checks (from verify-structure.py)

- **solution_outline_sections**: required sections are `summary`, `overview`, `deliverables`.
- **deliverable_count**: extracted from the Deliverables section using heading level 3 (`### `).
- **task_deliverable_match**: each deliverable index (1..N) MUST have a corresponding task whose `deliverable` field matches.
- **affected_files_recall**: when `solution_outline.md` declares `Affected files:` bullets per deliverable, references.json `modified_files` SHOULD contain at least 70% of them. < 70% is a fail. When the peer top-level key `affected_files_exact_match` reports `status: warn`, the retrospective synthesizer MUST surface the drift in the report naming `outline_only` and `references_only` verbatim.

## Manifest-Aware Mode (when `execution.toon` exists)

When the plan directory contains an `execution.toon` manifest produced by `plan-marshall:manage-execution-manifest`, the script enters manifest-aware mode for the `affected_files_exact_match` check:

- The `warn` outcome is downgraded to `info` and annotated with `forwarded_to_manifest: true` in the top-level `affected_files_exact_match` payload.
- A forwarding finding is emitted (`severity: info`) so the report renderer routes the reader to the dedicated **Manifest Decisions** section instead of double-counting the same drift.
- The actual drift cross-check is delegated to `plan-marshall:plan-retrospective:check-manifest-consistency`, which compares the manifest assumptions against the actual end-of-execute git diff. Cross-check rules are codified in `standards/manifest-crosscheck.md`.

Pre-manifest plans (legacy / in-flight, no `execution.toon`) keep the original `warn` behavior so existing reports and tests stay stable. The `affected_files_exact_match` payload always includes `manifest_present` and `forwarded_to_manifest` flags so downstream consumers can branch deterministically.

## LLM Interpretation Rules

- `fail` checks MUST surface in the final report.
- `partial` checks surface only when their message is actionable (e.g., missing files named).
- Presence of `metrics.md` is required when the plan ran `default:record-metrics`. Absence implies either the step was skipped OR an earlier step crashed.

## Finding Shape

```toon
aspect: artifact_consistency
severity: info|warning|error
check: {check_name}
message: "{one-line summary}"
```

## Out of Scope

- Validating the content quality of each artifact — that belongs to request-result-alignment.
- Checking log completeness — that is logging-gap-analysis.
