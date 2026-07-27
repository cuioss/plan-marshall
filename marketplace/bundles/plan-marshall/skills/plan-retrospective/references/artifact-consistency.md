# Aspect: Artifact Consistency

Cross-checks between plan artifacts to catch drift, missing files, and mismatched counts. Facts come from `check-artifact-consistency.py`; this document tells the LLM how to judge the facts.

## Inputs

The script consumes:
- `status.toon` (phase position, metadata)
- `solution_outline.md` (deliverables section)
- `references.json` / `references.toon` (domains; `base_branch` for the footprint diff)
- the plan's live footprint — derived from the worktree (`{base}...HEAD` ∪ porcelain) when one is on disk, falling back to the legacy `references.modified_files` key only for archived plans created before the ledger was removed
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
  affected_files_recall,fail,"Recall 50% below 70% threshold"
  affected_files_exact_match,inconclusive,"both the declared set and the resolved footprint are empty"
  metrics_generated,fail,"metrics.md not found (record-metrics skipped?)"
findings[*]{severity,message}:
  error,"metrics.md missing — record-metrics step did not run"
  warning,"Recall 50% below 70% threshold"
  warning,"both the declared set and the resolved footprint are empty — the comparison substantiates no verdict"
summary:
  passed: N
  failed: N
  skipped: N
```

## Novel Checks (from verify-structure.py)

- **solution_outline_sections**: required sections are `summary`, `overview`, `deliverables`.
- **deliverable_count**: extracted from the Deliverables section using heading level 3 (`### `).
- **task_deliverable_match**: each deliverable index (1..N) MUST have a corresponding task whose `deliverable` field matches.
- **affected_files_recall**: when `solution_outline.md` declares `Affected files:` bullets per deliverable, the plan's live footprint SHOULD contain at least 70% of them. < 70% is a fail. The declaration state is read **per deliverable**, not off the flattened aggregate: any deliverable whose own content carries the `Affected files:` heading yet yields no parsed bullet reports `fail` naming that deliverable by number and title, and that verdict fires even when sibling deliverables declared files and the aggregate declared set is non-empty — an unparseable bullet list cannot substantiate any coverage verdict, and a sibling's declaration must not mask it. `skip` is reserved for an outline where no deliverable declares an `Affected files` section at all.
- **affected_files_exact_match**: the declared set and the resolved footprint MUST agree exactly. A both-empty comparison reports `inconclusive` — two empty sets are trivially equal whether the plan really touched no files or both the parser and the footprint resolver failed — and is accompanied by a `severity: warning` finding. `pass` is reserved for two non-empty, exactly-agreeing sets. When the check reports `status: warn`, the retrospective synthesizer MUST surface the drift in the report naming `outline_only` and `references_only` verbatim.

## Borrowed grammar: the `Affected files:` bullet form is owned elsewhere

The `Affected files:` bullet grammar the `affected_files_*` checks parse is **owned by `plan-marshall:manage-solution-outline`**, which authors and validates those bullets. `check-artifact-consistency.py` re-parses that grammar with its own regex — a second reader of a format it does not own — so the two can drift apart silently: the owner accepts a bullet form the borrowed reader cannot match, and the check reports an empty declared set rather than a parse error.

Two obligations follow, and they are the recurrence guard for that drift:

- **A change to the bullet grammar in `manage-solution-outline` MUST be mirrored into this check's extractor in the same change.** The canonical annotated form is ``- `path/to/file` (intent)`` — the backtick-delimited span is the path and everything after the closing backtick is metadata to discard. A bare, un-annotated ``- path/to/file`` is also accepted. A grammar addition that lands on only one side is a defect even though both sides individually pass their own tests.
- **The borrowed reader MUST fail loudly, never quietly.** Because the reader can silently under-match, an `Affected files:` heading present in a deliverable's own content but yielding no parsed bullet is treated as a parse failure (`fail`) for that deliverable — regardless of what its siblings declared — and a both-empty comparison is `inconclusive` — see the two check definitions above. Those verdicts exist specifically because a borrowed parser's silence is indistinguishable from a genuine absence.

Reusing the owner's extractor rather than re-implementing the grammar removes the drift class entirely and is the preferred direction whenever this check is next reworked.

## Manifest-Aware Mode (when `execution.toon` exists)

When the plan directory contains an `execution.toon` manifest produced by `plan-marshall:manage-execution-manifest`, the script enters manifest-aware mode for the `affected_files_exact_match` check:

- The `warn` outcome is downgraded to `info` and annotated with `forwarded_to_manifest: true` in the top-level `affected_files_exact_match` payload.
- A forwarding finding is emitted (`severity: info`) so the report renderer routes the reader to the dedicated **Manifest Decisions** section instead of double-counting the same drift.
- The actual drift cross-check is delegated to `plan-marshall:plan-retrospective:check-manifest-consistency`, which compares the manifest assumptions against the actual end-of-execute git diff. Cross-check rules are codified in `standards/manifest-crosscheck.md`.

Pre-manifest plans (legacy / in-flight, no `execution.toon`) keep the original `warn` behavior so existing reports and tests stay stable. The `affected_files_exact_match` payload always includes `manifest_present` and `forwarded_to_manifest` flags so downstream consumers can branch deterministically.

## LLM Interpretation Rules

- `fail` checks MUST surface in the final report.
- `inconclusive` checks MUST surface in the final report. `inconclusive` means the check's inputs could not substantiate any verdict — it is NOT a benign non-failure and MUST NOT be read as a pass. Name the unresolvable input (an empty declared set, an empty resolved footprint, or both) so the reader can repair the plan state rather than trusting an absent signal.
- `warn` checks surface only when their message is actionable (e.g., the drifting `outline_only` / `references_only` sets are named).
- `info` checks do NOT surface here — the manifest-aware forwarding downgrade routes the reader to the **Manifest Decisions** section instead.
- `skip` checks do NOT surface — the check had nothing to judge (see `affected_files_recall`'s no-deliverable-declares-a-section branch).
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
