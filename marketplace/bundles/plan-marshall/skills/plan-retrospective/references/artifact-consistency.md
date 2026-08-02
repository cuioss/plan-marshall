# Aspect: Artifact Consistency

Cross-checks between plan artifacts to catch drift, missing files, and mismatched counts. Facts come from `check-artifact-consistency.py`; this document tells the LLM how to judge the facts.

## Inputs

The script consumes:
- `status.toon` (phase position, metadata)
- `solution_outline.md` (deliverables section)
- `references.json` / `references.toon` (domains; `base_branch` for the footprint diff)
- the plan's live footprint — derived from the worktree (`{base}...HEAD` ∪ porcelain) when one is on disk, falling back to the legacy `references.modified_files` key only for archived plans created before the ledger was removed. The footprint carries a **resolution state**: it either resolved (possibly to a genuinely empty set) or it could not be resolved at all. The two are distinct answers, never collapsed into one empty set — see [Footprint resolution state](#footprint-resolution-state)
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
  affected_files_recall,inconclusive,"Plan footprint could not be resolved — recall is unmeasurable, not 0%"
  affected_files_exact_match,inconclusive,"Plan footprint could not be resolved — the comparison substantiates no verdict"
  metrics_generated,inconclusive,"metrics.md not produced yet — default:record-metrics is ordered after plan-marshall:plan-retrospective"
findings[*]{severity,message}:
  warning,"metrics.md not produced yet — default:record-metrics (order 998) is ordered after plan-marshall:plan-retrospective (order 995), so it has not had its turn"
  warning,"Plan footprint could not be resolved (no live worktree diff and no modified_files key) — recall is unmeasurable, not 0%"
  warning,"Plan footprint could not be resolved (no live worktree diff and no modified_files key) — the comparison substantiates no verdict"
summary:
  passed: N
  failed: N
  skipped: N
  warn: N
  info: N
  inconclusive: N
```

`summary` carries a bucket for **every** status the checks emit, and the buckets sum to `len(checks)` — no verdict lands outside the summary, where a consumer would read it as a check that does not exist. The buckets are derived from the emitted checks rather than from a fixed status list, so a status added later is counted automatically. `pass` / `fail` / `skip` keep their established bucket names (`passed` / `failed` / `skipped`) and are always present even at zero; every other status buckets under its own name.

## Novel Checks (from verify-structure.py)

- **solution_outline_sections**: required sections are `summary`, `overview`, `deliverables`.
- **deliverable_count**: extracted from the Deliverables section using heading level 3 (`### `).
- **task_deliverable_match**: each deliverable index (1..N) MUST have a corresponding task whose `deliverable` field matches.
- **affected_files_recall**: when `solution_outline.md` declares `Affected files:` bullets per deliverable, the plan's live footprint SHOULD contain at least 70% of them. < 70% is a fail. The declaration state is read **per deliverable**, not off the flattened aggregate: any deliverable whose own content carries the `Affected files:` heading yet yields no parsed bullet reports `fail` naming that deliverable by number and title, and that verdict fires even when sibling deliverables declared files and the aggregate declared set is non-empty — an unparseable bullet list cannot substantiate any coverage verdict, and a sibling's declaration must not mask it. `skip` is reserved for an outline where no deliverable declares an `Affected files` section at all. When the footprint could not be resolved, the check reports `inconclusive` with a `severity: warning` finding and emits no percentage: a recall figure derived from an unresolved footprint is a confident claim about an input that was never measured. A percentage — including `0%` — is reported only from a footprint that genuinely resolved.
- **affected_files_exact_match**: the declared set and the resolved footprint MUST agree exactly. Two comparisons report `inconclusive`, each accompanied by a `severity: warning` finding: an **unresolvable footprint**, where there is no right-hand side to compare and a `warn` "Set mismatch" would claim drift from an unmeasured input; and a **both-empty** comparison, where two empty sets are trivially equal whether the plan really touched no files or both the parser and the footprint resolver failed. `pass` is reserved for two non-empty, exactly-agreeing sets. When the check reports `status: warn`, the retrospective synthesizer MUST surface the drift in the report naming `outline_only` and `references_only` verbatim.
- **metrics_generated**: `metrics.md` present is a `pass`. Absence substantiates "the producing step did not run" ONLY once that step has had its turn, so the verdict is derived from the two steps' **relative order**, not from the file's absence alone — see [Producer ordering](#producer-ordering). Producer ordered later ⇒ `inconclusive` naming the ordering, with a `severity: warning` finding; producer ordered earlier ⇒ `fail`, with a `severity: error` finding; ordering unresolvable ⇒ `inconclusive`, because whether the producer has had its turn is itself unmeasurable.

## Producer ordering

`metrics.md` is produced by `default:record-metrics` and read by `plan-marshall:plan-retrospective`, which hosts this check. The producer is ordered AFTER the consumer, so on a correctly-functioning run the artifact does not exist yet when the check reads for it: a `fail` claiming the producer "did not run" would be structurally guaranteed to be wrong rather than occasionally wrong.

Both orders are resolved from **discovery** — the same finalize-step ext-point registry the pipeline itself orders by — never from an order literal. Two consequences are load-bearing: renumbering a step moves the verdict with it instead of silently vacating the check, and a further consumer of the same artifact (`default:finalize-step-print-phase-breakdown` also reads `metrics.md`) needs no second hardcoded pair. When either order cannot be resolved, the check reports `inconclusive` rather than assuming a position — an unresolved ordering is an unmeasurable input, exactly as an unresolvable footprint is.

## Footprint resolution state

`_resolve_footprint` reports whether it resolved, not merely what it resolved to. "Resolved to a genuinely empty set" and "could not be resolved at all" are different answers, and both `affected_files_*` checks read the difference through one named predicate rather than by testing emptiness.

The footprint is **unresolvable** when neither resolution tier answers: no live worktree diff (the tier-1 `git` invocation failed, or archived mode skipped tier 1 and no worktree is on disk) and no `references.modified_files` key. A tier-1 diff failure reports unresolvable rather than falling through to the legacy key — the worktree resolved but the diff did not, so the legacy key would answer a different question while presenting as the same measurement. A `modified_files` key that is present but empty is the opposite case: a resolved, genuinely-empty footprint, which still yields a measured verdict.

Both peers of the `affected_files_*` pair consume this state. Hardening only one leaves the pair half-hardened: the same deleted worktree that makes recall unmeasurable also makes the exact-match comparison unmeasurable, and a peer that still reports confidently re-introduces the defect through the other half of the pair. The concrete failure this removes: a plan with a 21/21 exact footprint scored a confident "Recall 0% below 70% threshold" because `branch-cleanup` had already deleted the worktree the resolver measures.

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
- An `affected_files_*` check reporting `inconclusive` because the **footprint could not be resolved** (see [Footprint resolution state](#footprint-resolution-state)) falls under the rule above: surface it, never read it as a pass, and name the unresolved footprint as the input to repair. The usual cause is a worktree the merge gate already deleted, so the repair is to the measurement's ordering, not to the plan's declared files — do NOT report it as a coverage gap, and do NOT infer any recall figure for it.
- `warn` checks surface only when their message is actionable (e.g., the drifting `outline_only` / `references_only` sets are named).
- `info` checks do NOT surface here — the manifest-aware forwarding downgrade routes the reader to the **Manifest Decisions** section instead.
- `skip` checks do NOT surface — the check had nothing to judge (see `affected_files_recall`'s no-deliverable-declares-a-section branch).
- Presence of `metrics.md` is required only once `default:record-metrics` has had its turn. Absence has three causes, and the third is the most common: the step is **ordered after** the reading retrospective and has not run yet, OR the step was skipped, OR an earlier step crashed. Do NOT read absence as evidence of the second or third when `metrics_generated` reports `inconclusive` — that verdict states the producer has not had its turn (see [Producer ordering](#producer-ordering)), and the repair, if any, is to the measurement's ordering rather than to the run. Only a `fail` from this check substantiates "the step had its turn and produced nothing".

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
