# Land Verb Workflow

Workflow doc for the `land` verb: bring the shared orchestrator ledger worktree's state onto the base branch through ONE pull request that carries every epic's pending ledger writes, then replay the worktree onto the new base without discarding anything written while the PR was in flight. The ledger landing model this verb implements is owned by [`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger landing model](../../persona-plan-orchestrator/standards/orchestration-model.md#ledger-landing-model); when this doc and the standard disagree, the standard wins.

`land` operates on the store as a whole, so it takes no epic slug. It needs `orchestrator.use_worktree` on: with the knob off there is no shared worktree, the ledger lives on the checkout the session runs in, and it reaches the base branch with the plan that changed it.

`{store_checkout}` throughout this doc is the `store_checkout` that `land status` reports in Step 1 — the same store checkout `orchestrator resolve-path` returns. Every git operation the four `land` script verbs perform targets it as `git -C {store_checkout}`; this workflow runs no ledger git command of its own.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `requeue` | No | `requeue=true` permits re-enqueueing a PR the merge queue ejected. Absent or any other value, an ejected PR ends the run with outcome `dequeued`. |

The verb is invoked as `/plan-orchestrator land` or `/plan-orchestrator land requeue=true`. There is no epic argument.

## Prohibitions

- Never remove the shared ledger worktree, and never recreate it. The land cycle ends with the same tree continuing on the new base.
- Never stamp a landing from the `ci pr merge-queue` return. That return reports one enqueue call; the landed state is read from the PR itself (`pr_state: merged` and its `merge_commit_sha`).
- Never use `ci pr landing-state`. It classifies a branch, and the land's head branch is deleted and re-created across cycles; the land reads its PR by number through `ci pr queue-state`.
- Never pick the PR from the branch's PR history. The PR that carries the land is the one `land status` reports as `bound_pr`; the only fallback is the open-PR listing in Step 2, which considers open PRs alone.
- Never route the land through the plan pre-merge barrier or the review-bot steps. Those belong to the plan lifecycle; the land PR carries ledger files only.
- Never use `ci pr merge` or `ci pr safe-merge`. The land merges through the merge queue (`ci pr merge-queue`) and nothing else.
- Never force-push. The single forced remote operation in the whole cycle is the lease-guarded delete of the landed head branch that `land resync` performs itself.
- Never re-enqueue a dequeued PR without `requeue=true`.
- Never write to the ledger after the snapshot on behalf of the land. The land records its own state in two local-only git refs; it adds no queue row, no landing record, no anchor move and no log entry to any epic.

## The ci calls

`land` is the one sanctioned write-side use of `plan-marshall:tools-integration-ci:ci` in the orchestrator (see the [small-ops carve-out](../../persona-plan-orchestrator/standards/orchestration-model.md#small-ops-carve-out)). Every call below is written exactly as the live `--help` accepts it:

- The read verbs (`pr queue-state`, `pr list`, `checks wait`, `pr wait-for-queue-settle`) and `pr merge-queue` declare no verb-level `--plan-id`. A `--plan-id` or `--project-dir` for them is a router flag and goes BEFORE the first verb token; this workflow passes neither.
- The body-consumer verbs (`pr prepare-body`, `pr create`) declare a required `--plan-id` AFTER the verb. The land is bound to no plan, so both take `--plan-id NO_PLAN`.
- Every long wait passes an explicit `--timeout 540` and is run synchronously with a Bash timeout of 600000ms, so the wait returns its own verdict inside the tool call.

## Workflow

### Step 1: Read where the tree stands

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator land status
```

The payload fields and their value sets are in [`SKILL.md` § Canonical invocations → land status](../SKILL.md#land-status). Route on them in this order:

| Observation | Action |
|-------------|--------|
| `status: error` with `land_requires_use_worktree` | STOP. Report the refusal; there is nothing to land through this verb. |
| `status: error` with a seam refusal code (`ledger_cutover_refused`, `ledger_drift_unevaluable`, `base_ref_unresolvable`, `orchestrator_worktree_create_failed`, `orchestrator_worktree_wrong_branch`) or `land_guard_timeout` | STOP. Report the code and its message verbatim; nothing was changed. |
| `pushed_marker` is set | A land is in flight. Go to Step 2. |
| `pushed_marker` is null, `remote_branch: present`, `remote_branch_contained: false` | STOP with outcome `remote_branch_diverged` — the remote head branch holds work the local tree lacks, and a push would be rejected. |
| `pushed_marker` is null and `remote_branch` or `remote_branch_contained` is `unknown` | STOP with outcome `indeterminate` — the remote could not be read. |
| `pushed_marker` is null otherwise | Go to Step 3. |

`remote_branch_contained: true` beside `remote_branch: absent` is the ordinary start of a cycle: an absent branch holds nothing the local tree lacks.

### Step 2: Resume an in-flight land

Reached only when `pushed_marker` is set. Route on `bound_pr`, never on the branch's PR history.

**`bound_pr_conflict` is present.** More than one binding ref exists, so `bound_pr` is null without the land being unbound. STOP with outcome `indeterminate`, naming the listed PR numbers. The repair is `land bind --pr-number N` for the PR that carries the land — it removes every other binding.

**`bound_pr` is a number.** Read the PR:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr queue-state \
  --pr-number {bound_pr}
```

| Observation | Action |
|-------------|--------|
| `status: error` (`pr_read_failed`) | STOP with outcome `indeterminate`. |
| `pr_state: merged` | Go to Step 8 with the payload's `merge_commit_sha`. A null `merge_commit_sha` beside `merged` is outcome `indeterminate`. |
| `pr_state: closed` | Treat the land as unbound and continue with the unbound branch below. |
| `pr_state: open`, and `in_queue` or `auto_merge_armed` is `indeterminate` | STOP with outcome `indeterminate`. A membership that could not be observed is not evidence that the PR is outside the queue. |
| `pr_state: open`, and `in_queue: true` or `auto_merge_armed: true` | Go to Step 7. |
| `pr_state: open`, `in_queue: false`, `auto_merge_armed: false` | Apply the ejection gate below. |

**Ejection gate** — for an open PR that is neither queued nor armed, read `merge_group_run` from the same payload:

| `merge_group_run` | Action |
|-------------------|--------|
| `found: true`, `status: completed`, `conclusion` other than `success` | The merge queue ejected the PR. STOP with outcome `dequeued` — unless the verb was invoked with `requeue=true`, in which case go to Step 5. |
| `found: indeterminate` | STOP with outcome `indeterminate`. |
| anything else (`found: false`, a run still in progress, a run that concluded `success`) | The PR was never ejected. Go to Step 5. |

**The land is unbound** (`bound_pr` is null with no conflict, or the bound PR is closed). List the open PRs on the land's head branch:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr list \
  --head chore/orchestrator-ledger --state open
```

| Open PRs listed | Action |
|-----------------|--------|
| exactly one | Bind it with `land bind --pr-number N` (the Step 4 command), then re-enter this step with that number as `bound_pr`. |
| none | Re-push the in-flight land with the extend form of Step 3's command, then go to Step 4. |
| more than one, or a failed or truncated listing | STOP with outcome `indeterminate`. |

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator land snapshot --extend
```

Only `--state open` is ever listed. A merged or closed PR found any other way is never adopted as the land's PR.

### Step 3: Snapshot the ledger

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator land snapshot
```

The verb stages and records the pending ledger paths at `{store_checkout}`, pushes the result to `chore/orchestrator-ledger` without force, and writes the pushed marker. Route on the return:

| Return | Action |
|--------|--------|
| `outcome: pushed` | Keep `title`, `body` and `head_sha`. Go to Step 4. |
| `outcome: nothing_to_land` | STOP with outcome `nothing_to_land`. |
| `outcome: in_flight` | Another session started a land between Step 1 and now. Go to Step 2 with the returned `bound_pr`. |
| `error: ledger_push_rejected` | STOP with outcome `remote_branch_diverged`. The snapshot is kept locally at `{store_checkout}` and no land is recorded; the payload's `remote_branch` and `remote_branch_contained` say what the remote holds. |
| any other `status: error` (`ledger_commit_failed`, `land_ref_write_failed`, `land_guard_timeout`) | STOP with outcome `indeterminate`, reporting the code. |

Writes that reach the ledger after this step are not part of this land. They stay in the worktree, `land resync` replays them onto the new base in Step 8, and the next `land` carries them.

### Step 4: Open the PR and bind it

Allocate the body file:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body \
  --plan-id NO_PLAN
```

Write the snapshot's `body` verbatim to the returned path with the `Write` tool. The body carries no attribution footer and none is added.

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create \
  --plan-id NO_PLAN --head chore/orchestrator-ledger --title "{title}"
```

`{title}` is the snapshot's `title`. When Step 2 reached this step through `land snapshot --extend`, the title and body come from that call's return.

Bind the PR the create call returned:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator land bind \
  --pr-number {pr_number}
```

`outcome: bound` continues to Step 5. A failed create, or a bind returning `no_land_in_flight` or `land_ref_write_failed`, is outcome `indeterminate`.

### Step 5: Wait for the PR checks

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks wait \
  --pr-number {pr_number} --timeout 540 --dispatch inline
```

Route on the live envelope fields, never on a guessed status value:

| Observation | Action |
|-------------|--------|
| `final_status` reports a failure | STOP with outcome `ci_failed`. |
| `wait_outcome: deadline_exceeded` | STOP with outcome `timeout`. There is no `status: timeout` value to match on. |
| `status: error` | STOP with outcome `indeterminate`. |
| the checks completed green | Go to Step 6. |

The field vocabulary is owned by [`tools-integration-ci/SKILL.md`](../../tools-integration-ci/SKILL.md); it is not restated here.

### Step 6: Enqueue

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge-queue \
  --pr-number {pr_number}
```

A `status: error` return is outcome `indeterminate`. Any other return continues to Step 7 — the enqueue return says the call was accepted, never that the PR landed.

### Step 7: Wait for the queue to settle

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-queue-settle \
  --pr-number {pr_number} --timeout 540
```

| `settle` | Action |
|----------|--------|
| `merged` | Go to Step 8 with `final.merge_commit_sha`. |
| `dequeued` | STOP with outcome `dequeued`. `final.merge_group_run` names the run that failed the merge group. |
| `closed` | STOP with outcome `closed_unmerged`. |
| `timeout` | STOP with outcome `timeout`. The land stays in flight; a later `/plan-orchestrator land` resumes it in Step 2. |
| — (`status: error`) | STOP with outcome `indeterminate`. |

`dequeued` is terminal and distinct from `timeout`: the first means the queue ejected the PR, the second that the wait's budget ran out while the PR was still in flight.

⚠ **Unverified assumption.** `dequeued` — here and in the Step 2 ejection gate — rests on matching a merge-group workflow run to the PR by its head branch, assumed to be named `gh-readonly-queue/{base}/pr-{n}-{sha}`. That naming has not been verified against a live merge queue. If a live queue names the branch differently, no run is matched, an ejected PR is not recognised as ejected, and this step reports `timeout` where `dequeued` was the fact.

### Step 8: Resync the worktree

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator land resync \
  --pr-number {pr_number} --merge-commit-sha {merge_commit_sha}
```

`outcome: resynced` is outcome `landed`. The return also reports, without failing the land, `main_fast_forward` (`done` / `failed`), `remote_branch_cleanup` (`deleted` / `already_absent` / `kept_diverged` / `failed`), `replayed_commits`, `carried_uncommitted` and `already_resynced`; relay any value other than `done` and `deleted` / `already_absent` to the operator.

Every `status: error` return is outcome `resync_failed`. The PR has merged, so nothing is lost; what remains is closing the cycle locally. The remedy depends on the code:

| `error` | State left behind | Remedy |
|---------|-------------------|--------|
| `no_land_in_flight` | No pushed marker exists | Nothing to resync; a prior run already closed the cycle. |
| `invalid_merge_commit_sha` | Untouched | Re-run `/plan-orchestrator land`; Step 2 reads the SHA from the PR. |
| `base_fetch_failed` | Untouched | Restore network access, then re-run `/plan-orchestrator land`. |
| `merge_commit_not_on_base` | Untouched | The SHA is not on the fetched base. Re-run `/plan-orchestrator land` so Step 2 re-reads it from the PR. |
| `resync_content_unevaluable` | Untouched | Git could not measure what the land changed. Report the payload's `stderr`; the operator repairs the repository state before a re-run. |
| `resync_content_mismatch` | Untouched; `mismatched_paths` lists the paths | The landed content differs from what was pushed. The operator compares each listed path at `{store_checkout}` against the base before anything is replayed. |
| `resync_conflict` | The replay was aborted, both land refs are kept, `head_restored` says whether the tree is back where it was. The payload's `main_fast_forward` and `remote_branch_cleanup` report steps that ran BEFORE the replay — the primary checkout may already be fast-forwarded and the remote head branch already deleted | The operator replays the tree onto the base by hand at `git -C {store_checkout}`, then re-runs `/plan-orchestrator land`: Step 2 reads the PR as merged, and the resync recognises the already-replayed tree and closes the cycle. |
| `land_guard_timeout` | Untouched | Another session holds the land guard. Re-run `/plan-orchestrator land`. |

The verb echoes `--pr-number` into its return and does not compare it against the binding ref; the number this step passes is the one Step 2 or Step 4 established.

### Step 9: Report

Report exactly ONE outcome from the closed set, with the evidence that established it (the PR number, the landing SHA, the error code, or the observation string of the read that decided it):

| Outcome | Established by |
|---------|----------------|
| `landed` | Step 8 returned `outcome: resynced` |
| `nothing_to_land` | Step 3 returned `outcome: nothing_to_land` |
| `ci_failed` | Step 5 read a failed `final_status` |
| `dequeued` | Step 7 `settle: dequeued`, or the Step 2 ejection gate without `requeue=true` |
| `closed_unmerged` | Step 7 `settle: closed` |
| `timeout` | Step 5 `wait_outcome: deadline_exceeded`, or Step 7 `settle: timeout` |
| `indeterminate` | A read or a step the land needed returned no verdict |
| `resync_failed` | Step 8 returned `status: error` |
| `remote_branch_diverged` | Step 1 read an uncontained remote branch, or Step 3 returned `ledger_push_rejected` |

A refusal in Step 1 (`land_requires_use_worktree`, a seam refusal) is reported as that refusal and carries no outcome: the land never started.

## Output

```toon
status: success | error
display_detail: "ledger land: {outcome}"
outcome: landed | nothing_to_land | ci_failed | dequeued | closed_unmerged | timeout | indeterminate | resync_failed | remote_branch_diverged
pr_number: {pr_number or null}
merge_commit_sha: {merge_commit_sha or null}
```

`status` is `success` for `landed` and `nothing_to_land` and `error` for every other outcome. `display_detail` is composed by this workflow and is ≤80 chars, ASCII, no trailing period.
