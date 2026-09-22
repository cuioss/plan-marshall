# Landing: PLAN-PR-025A — a refusal is recorded as a refusal (the record)

plan: PLAN-PR-025A · workstream: WS-01 · PR: **#1368** · merged: `31d42db871eb1ed6095868b42af85e8162ef4a8e`
plan_marshall_plan_id: `a-refusal-is-recorded-as-a-refusal-the-record`

## Corroboration — the paste was verified, not parroted

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1368 merged as `31d42db87` | **corroborated** | `ci pr view` → `state: merged`, `merge_commit_sha: 31d42db871…`; `git log` shows `31d42db87` on `main` |
| All 7 deliverables shipped, 23/23 finalize steps | **corroborated** as reported | The run's own step ledger; not independently re-derived |
| `ci pr view` returned a FALSE `auth_failed` | **corroborated, with a mechanism** | See § The `[FAILED]` headline |
| `merge_state=unknown` is a producer failure | ⛔ **CONTRADICTED — it is a CONTRACT defect** | See § The landing is incomplete |

## The `[FAILED]` headline was a false negative — and the mechanism is now known

The run's own reading was right: the plan succeeded and the template did its job on a bad
input. ⭐ **The producer defect is real, and first-party root-caused here** —
`ci_base.check_auth_cli` (`ci_base.py`:843-862):

```python
returncode, _, _ = run_fn(['auth', 'status'])
if returncode != 0:
    return False, login_message        # -> error_cause: auth_failed
```

⛔ **Any non-zero exit from `gh auth status` becomes `auth_failed`, and BOTH streams are
discarded** (`returncode, _, _`). `gh auth status` validates the token against the API, so a
transient network or API failure is indistinguishable from "not authenticated" — the probe
collapses *could-not-verify* into *not-authenticated*, and throws away the only evidence
(`stderr`) that would separate them. **This is the epic's own archetype: a signal reported on
the wrong axis, amplified by a correctly fail-closed consumer.**

⚠ **NOT reproducible today, and that is recorded rather than smoothed over.** Re-run at this
HEAD: `ci pr view --pr-number 1368` → `success`; the bare form → `no_pr_found` (correctly
discriminated); the `--plan-id` form → `worktree_resolution_failed` (the plan is archived). So
the *structural* misclassification is CONFIRMED from the code; the specific trigger on the day
is **HYPOTHESIS** and needs the matched control the finding proposes.

## The landing is incomplete — but the cause is not the producer

`inbox landing-check` → `complete: false`, `missing_keys: [merge_state]` — **the only missing
key**; every other required fact was supplied.

⛔⛔ **The run blamed `branch-cleanup` for recording none of its four `records_facts`. That is
not what the evidence shows.** A **successful** `ci pr view` against merged PR #1368 returns
`merge_state: unknown` — because GitHub stops reporting a mergeable state once a PR is merged.
⇒ **A post-merge landing structurally cannot supply a non-`unknown` `merge_state`**, so the
completeness contract as written makes *every* landing that reports after its own merge
permanently incomplete.

⭐ **This lands squarely on PLAN-PR-028 — "a landing message that cannot outrun its merge" — which
is exactly its subject**, and it sharpens D1's five-value `merge_state` vocabulary: the merged
case needs a value that is neither `n/a` nor `unknown`, or `unknown` must stop being
disqualifying at this key. Recorded there.

## Residue carried by the run, accepted as reported

- **Merge-FIFO deadlock** stalled the post-merge tail: `merge.lock` free while `merge_lock
  acquire` returned `blocked` with `waiting_count: 2`, and the blocked payload named
  `blocking_plan_id: null` — *the diagnostic named nobody*. Cleared by releasing the stale head
  (`detector-and-auditor-integrity`). ⇒ A vacuous-diagnostic instance; routed to
  `truthful-signals`.
- **`merge_commit_sha` correction**: switch-and-pull pulled 0 commits because `main` had already
  advanced to a sibling plan's landing, so the step as written would have recorded **another
  plan's commit** as this plan's. Caught in-run. ⇒ Real ordering hazard under concurrent
  landings; routed to `truthful-signals`.

## Cost

36h26m wall / 9h14m worked (n=5/6) · 9.88M tokens · **221.87M billing** · 2552 tool uses.
⛔ 6-finalize alone: 30h6m wall, 24h35m idle, 147.7M billing — **67% of the run's billing**, the
same finalize-dominance shape the epic already tracks. Not re-derived here.

## Reconciliation actions

- Row `PLAN-PR-025A` → `shipped`; `pr: 1368`; `landing: landings/PLAN-PR-025A.md`.
- 13 inbox messages drained (1 landing, 2 findings, 10 candidate-lessons).
- **PLAN-PR-025B is now UNBLOCKED** — its dependency was this plan's D1, which shipped.
