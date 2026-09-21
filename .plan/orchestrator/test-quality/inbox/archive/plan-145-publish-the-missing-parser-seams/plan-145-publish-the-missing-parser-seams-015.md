envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:49:21Z

# Script-failure cluster: manage-references get without --field, and the plan_creation_sha that is never written

**Signal**: script-failure cluster (1 of 9 distinct failing notations on this plan)
**Notation**: `plan-marshall:manage-references:manage-references`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## Evidence — the rejection

```text
[2026-09-04T14:28:17Z] [ERROR] plan-marshall:manage-references:manage-references get (0.00s)
  exit_code: 2
  args: get --plan-id plan-145-publish-the-missing-parser-seams
  stdout: status: error / error: invalid_invocation
          reason: missing_required_flag / rejected: --field
          accepted: field, plan-id
```

Same shape as the `manage-config` cluster on this plan: the habitual `--plan-id` supplied alone, the discriminating flag omitted. Corrected within nine seconds.

## Evidence — the substantive defect behind the same notation

The corrected call then returned a real gap:

```text
manage-references get --plan-id ... --field plan_creation_sha
  -> status: error / error: field_not_found
```

`references.json` carries no `plan_creation_sha`, so `scope_creep_check` returned `could_not_look` with reason `no_baseline_sha` — the check ran, compared nothing, and produced no finding. Reading its output without reading the `could_not_look` discriminator is exactly the fail-open this project has already closed in `manage-lessons list-stalled`, `restore-from-plan`, `manage-findings`, and `check-outline-vs-shipped`.

On this plan the omission was benign (realized footprint 3 files against 2 declared), but **nothing in the run established that** — the guard simply had no baseline commit.

A related gap on the same file: `affected_files` held 2 paths while the merged commit touched 3 (`test/plan-marshall/script-shared/test_conftest_loader_contract.py` was never appended), so `files_modified: 2` understates every derived metrics denominator by ~1.5x.

## Already recorded — but in the wrong store

Written up as global lesson **`2026-09-04-14-007`**. Filed by `plan-marshall:plan-retrospective` dispatched with `orchestrated=false`, so it landed in the **global** lessons store rather than this epic's inbox. Recorded and not lost, but this epic will not drain it. Pointer supplied here.

## Proposed rule (for orchestrator judgement)

1. Write `plan_creation_sha` into `references.json` at `1-init`, recording the `main_sha` the plan was created against — the value is already captured in the phase-1 handshake invariants, so this is a persist, not a new measurement.
2. Surface `scope_creep_check`'s `could_not_look` verdict in the finalize output rather than folding it into a clean pass.
3. Append the realized footprint to `affected_files` so the metrics denominators match the shipped change.

## Related already-active lessons

- `2026-08-25-09-001` — capture the realized footprint at branch-cleanup before the worktree is removed (reinforced this run)
- `2026-08-25-09-010` — `compute-footprint` diffs against local main, inflating the footprint after an upstream landing
