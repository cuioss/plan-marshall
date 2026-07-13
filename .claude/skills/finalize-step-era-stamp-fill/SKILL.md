---
lane:
  class: derived-state
  cost_size: XS
name: finalize-step-era-stamp-fill
description: Finalize-phase project-local step that resolves the PR-PENDING era-stamp sentinel in audit.py (and its test mirror) to the real PR number in lock-step, committing and pushing the correction before the merge gate
user-invocable: false
mode: script-executor
allowed-tools: Bash, Write
order: 21
default_on: false
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
mutates_source: true
---

# Finalize Step — Era-Stamp Fill (project-local)

Project-local executor for `project:finalize-step-era-stamp-fill`. Resolves the
`PR-PENDING` era-stamp sentinel in the `audit-archived-plan-retrospectives`
`CHECK_ERA` map to this plan's real PR number, rewriting `audit.py` and its
`test_audit.py` mirror in lock-step and pushing the correction onto the feature
branch **before the merge gate** so it rides the PR.

This step is **project-local** (like `project:finalize-step-sync-plugin-cache`)
because the `CHECK_ERA` map is a meta-project-only artifact. Consumer projects have
no `audit.py`, so they never get this step seeded.

`mutates_source: true` — this step edits source at runtime and pushes it. It is the
concrete reference implementation of the general pre-merge source-edit contract in
[`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md`](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md):
a finalize step that edits source MUST run before the branch is merged so the edit
is pushable and covered by CI.

## Why PR-PENDING (the guessed-number defect it fixes)

A roadmap plan that reworks a check's mechanics stamps that check's `CHECK_ERA`
boundary to its OWN PR number — but the PR number is not known until `create-pr`
runs at finalize. The prior fragile convention was a prose instruction to hand-edit
the number after merge, which is unpushable on `main` and was silently reverted or
guessed — the guessed-PR-number / post-merge-unpushable era-stamp defect. The
`PR-PENDING` sentinel is a
provably-invalid PR token: this step resolves it deterministically from the real
`{pr_number}` the dispatcher already threads to finalize steps, and pushes the
correction pre-merge so it rides the PR and is CI-covered.

## Ordering

```
default:create-pr (20) →
project:finalize-step-era-stamp-fill (21) →
default:ci-verify (22) →
… →
default:branch-cleanup (70, MERGE)
```

`order: 21` places this step immediately after `create-pr` (so `{pr_number}` is
available) and before `ci-verify` (so the pushed correction is covered by the CI
run and merges with the branch).

## Inputs

- `{plan_id}` — required. Used for the `mark-step-done` call (Step 4); not passed
  to the `era_stamp_fill.py` executor itself (mirrors `finalize-step-deploy-target`
  and `finalize-step-sync-plugin-cache`, whose backing scripts likewise take no
  `--plan-id`).
- `{pr_number}` — required. The real PR number, threaded to finalize steps by the
  dispatcher (as it is for `ci-verify`). Accepts `NNN` or `#NNN`.
- `{worktree_path}` — the feature-branch worktree root the `audit.py` + test mirror
  are resolved against. Under the cwd-pinned model this is the current worktree;
  pass `.` when cwd is already the worktree.

## Execution

Inline-only — this step does NOT delegate to a Task agent. The fill is a fast,
deterministic Python script. It is invoked **directly** (not through the executor)
because it runs at order 21, before the finalize executor-regeneration step (order
85) would add its mapping — mirroring how `finalize-step-sync-plugin-cache` invokes
`sync.py` directly.

### 1. Invoke the fill executor

```bash
python3 .claude/skills/finalize-step-era-stamp-fill/scripts/era_stamp_fill.py run \
  --pr-number {pr_number} --worktree-path {worktree_path}
```

The script returns a flat TOON document. On the `status: success` path it carries
`filled_count`, `skipped` (`true` | `false`), and the normalized `pr_number`
(`#NNN`); on the `status: error` path it carries only `status` and a `message`
(the `filled_count` / `skipped` / `pr_number` fields are omitted). See the Step 2
table below for the per-outcome field set. It rewrites `"PR-PENDING"` →
`"#{pr_number}"` in both `audit.py` and `test_audit.py` in lock-step; it matches
only the double-quoted map-value form, so prose mentions and an already-resolved
concrete `"#NNN"` are never touched.

### 2. Parse the result

| Field | Meaning |
|-------|---------|
| `status: success`, `skipped: true` | No `PR-PENDING` token present — clean no-op. Record `outcome=done`; SKIP the commit/push (Step 3). |
| `status: success`, `skipped: false` | The sentinel was resolved in `filled_count` places across the two files. Proceed to commit + push (Step 3). |
| `status: error` | Bad `pr-number` or a missing target file. Record `outcome=failed` and surface `message`. |

### 3. Commit and push the correction (only when `skipped: false`)

The correction MUST land on the feature branch before the merge gate. Commit the two
edited files and push to the branch's upstream (the same push seam the `push` step
uses):

```bash
git -C {worktree_path} add .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py test/plan-marshall/audit-archived-plan-retrospectives/test_audit.py
```

```bash
git -C {worktree_path} commit -F {commit_message_file}
```

Compose the commit message to a temp file under `.plan/temp/` with the Write tool
first (multi-line messages never go through a shell argument); a conventional
subject such as `chore(audit): resolve PR-PENDING era stamp to #{pr_number}` is
appropriate.

```bash
git -C {worktree_path} push
```

### 4. Mark step complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize \
  --step project:finalize-step-era-stamp-fill \
  --outcome {done|failed} \
  --display-detail "{display_detail}"
```

`{display_detail}` shapes:

- `skipped: true` → `"no PR-PENDING sentinel — nothing to fill"`.
- `skipped: false` → `"resolved PR-PENDING to #{pr_number} ({filled_count} sites), pushed pre-merge"`.
- `status: error` → surface the script's `message` verbatim.

## Error Handling

| Scenario | Action |
|----------|--------|
| No `PR-PENDING` token (`skipped: true`) | Clean no-op — `mark-step-done --outcome done` so the `phase_steps_complete` handshake counts the step |
| `status: error` (bad pr-number / missing file) | `mark-step-done --outcome failed` surfacing the script `message`; the sentinel remains for an operator to resolve |
| `git push` fails | Record `outcome=failed` and surface the push failure — the correction must ride the PR, so a failed push is a real finalize failure, not a silent skip |

## Canonical invocations

The canonical argparse surface for the backing executor `era_stamp_fill.py`.

### era_stamp_fill — run

```bash
python3 .claude/skills/finalize-step-era-stamp-fill/scripts/era_stamp_fill.py run \
  --pr-number PR_NUMBER [--worktree-path WORKTREE_PATH]
```

## Related

- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md) — the general pre-merge source-edit contract this step is the reference implementation of
- [.claude/skills/finalize-step-sync-plugin-cache/SKILL.md](../finalize-step-sync-plugin-cache/SKILL.md) — sibling project-local inline `script-executor` finalize step
- [.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py](../audit-archived-plan-retrospectives/scripts/audit.py) — the `CHECK_ERA` map whose `PR-PENDING` sentinel this step resolves
- [marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md](../../../marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md) — finalize phase that invokes this step
