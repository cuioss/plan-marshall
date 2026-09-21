envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:48:46Z

# Script-failure cluster: manage-status invented verb `show` and invented flag `--get`

**Signal**: script-failure cluster (1 of 9 distinct failing notations on this plan)
**Notation**: `plan-marshall:manage-status:manage-status`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## Evidence — two rejections, five days apart

```text
[2026-08-30T10:15:37Z] [ERROR] manage-status show
  exit_code: 2 / reason: unknown_verb / rejected: show
  accepted: aggregate-confidence, archive, assert-step-recorded, ... read, route, ...

[2026-09-04T14:20:40Z] [ERROR] manage-status metadata --get phase_steps
  exit_code: 2 / reason: missing_required_flag / rejected: --field
  accepted: field, plan-id
```

Both are verb-paraphrase / flag-paraphrase: `show` for `read`, `--get` for `--field`. Both were self-corrected on the next call (`read` at `10:15:41`, `metadata --field` at `14:20:44`), so each cost one round-trip and no downstream corruption.

## The materially larger `manage-status` defect on this run

Separately, `manage-status list` reported five active plans **with a `location` column** (`current` / `worktree`), and `read` then returned `file_not_found` for both `location: worktree` rows. `list` performs cross-checkout discovery; `read` resolves cwd-relatively only, and neither offers the `--any-checkout` opt-in that `manage-findings` already ships on five read verbs. Any workflow that enumerates with `list` and reads per plan is structurally unable to complete for worktree-resident peers — on this run it blocked Gate 2 of the lesson-creation policy for 2 of 5 active plans and forced one high-confidence candidate to be **held rather than filed**.

## Already recorded — but in the wrong store

That second defect is written up as global lesson **`2026-09-04-14-009`** ("list resolves a worktree-resident plan that read then reports file_not_found"). It was filed by `plan-marshall:plan-retrospective`, which ran on this plan dispatched with `orchestrated=false`, so it landed in the **global** lessons store rather than this epic's inbox. It is recorded and not lost, but this epic will not drain it. Pointer supplied here so the epic can reconcile.

## Proposed rule (for orchestrator judgement)

Add `--any-checkout` to `manage-status read` / `metadata` and `manage-plan-documents request read`, resolving through the existing `git-workflow locate-plan-checkout` seam. Until then, `read`'s `file_not_found` for an id `list` just reported with `location: worktree` should name the checkout that holds it — `list` already knows the answer.

## Related already-active lessons

- `2026-09-03-11-004` — `manage-status read` declares only `--plan-id` and `--store`, never `--phase`
- `2026-08-30-16-001`, `2026-09-04-07-002` — main-anchored-vs-worktree resolution defects
