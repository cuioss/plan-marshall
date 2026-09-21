> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-054`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-058: `no_remote` conflates "never pushed" with "merged and deleted" — and the documented response to it is destructive

epic: truthful-signals
workstream: WS-01

## Objective

The `push` step's re-entry decision is **parity-driven**: it consults `branch-sync-state` and re-fires on
`ahead` or `no_remote`. ⛔ **`no_remote` has two mutually exclusive causes, and the documented response
is correct for one and DESTRUCTIVE for the other.**

## OBSERVED — first-party in a consumer repo (API-Sheriff PR #149), relayed by the operator

That plan's PR **had already merged** in a prior session (squash `ba5ef56`) which never recorded
`branch-cleanup` as done. Finalize resumed mid-pipeline.

- `push`'s re-entry probe returned **`no_remote`**.
- The contract reads that as *"local commits aren't on origin — re-push."*
- ⛔ **But the remote branch was gone because of DELETE-ON-MERGE, not because the push failed.**
- ⇒ **Re-pushing would have RESURRECTED A MERGED BRANCH.**

⭐ The agent **skipped it with a logged decision rather than following the rule literally** — i.e. **the
contract was saved by an agent declining to obey it.** ⛔ *A rule that must be disobeyed to be safe is a
defect, not a judgement call*, and the next executor may follow it.

## The mechanism, verified first-party in OUR tree

`workflow-integration-git/SKILL.md:446`:

> `no_remote` — `origin/{branch}` does not resolve locally (**branch never pushed**). `remote_sha` is
> omitted.

⇒ **The state's own documentation asserts the cause.** It is a **pure local read** —
`git rev-parse HEAD` vs `git rev-parse origin/{branch}`, **no fetch** (`SKILL.md:433`, `git-workflow.py:966`).

⛔⛔ **A missing local tracking ref cannot distinguish:**

| Cause | Correct response |
|---|---|
| never pushed | **re-push** |
| pushed, merged, branch deleted on merge | ⛔ **do NOT push — the work is already on main** |
| pushed, then the local ref was pruned (`git fetch --prune`, worktree churn) | do not push |

⇒ **One state, three causes, and the documented remedy is destructive for two of them.**

⭐⭐ **This is the epic's archetype with a WRITE attached** — like `PLAN-TRUTH-054`'s auto-merging
verdict: not merely a wrong read, but a wrong read whose prescribed action mutates the remote.

## ⚠ Why the resumed-finalize case is not exotic

⛔ **It is the normal shape of a recovered run.** A session that dies after the merge and before
`branch-cleanup` leaves exactly this state, and `PLAN-TRUTH-050`'s evidence shows post-merge finalize
tails are long and multi-session. ⇒ **The dangerous path is reached by the ordinary recovery flow, not
by an unusual one.**

## Deliverables

1. **D0 — GATE: derive the causes of `no_remote` and every consumer of the state.** ⛔ **Both
   directions**: every caller that branches on `no_remote`, and every condition that produces it.
   ⚠ **`baseline-reconcile` also emits a `reason: no_remote`** (`_cmd_baseline_reconcile.py:349`) —
   **confirm whether it is the same predicate or a different one sharing a name**; two producers for one
   token is `PLAN-TRUTH-049`'s shape.
2. **D1 — split the state so the destructive branch is unreachable by accident.** ⭐ The discriminator is
   cheap and already available locally: **is the plan's HEAD an ancestor of `origin/{base}`?** If the
   work is already on main, the branch's absence is a *consequence of success*, not a push failure.
   ⛔ **Prefer a distinct state name over a boolean flag** — a new value forces every consumer to
   branch, a flag lets them keep reading the old one.
3. **D2 — the push barrier fails CLOSED on an ambiguous probe.** If the cause cannot be established, the
   step must **decline and report**, never push. ⚠ **Confirm no legitimate flow depends on the current
   permissive re-push** before enforcing it.
4. **D3 — tests, each verified to FAIL pre-fix.** (a) **The live fixture**: merged PR + deleted remote
   branch + local commits ⇒ `push` does **not** re-push. (b) A genuinely never-pushed branch still
   re-pushes. (c) An ambiguous probe declines rather than acting. (d) The D0 consumer population is
   asserted non-empty.

⚠ Four deliverables, deliberately small. ⛔ **Do NOT widen into the whole re-entry contract** — the
`ahead`/`synced` branches are working as designed.

## Claim Labels

- **OBSERVED (this orchestrator, first-party, read from our source)**: `branch-sync-state` is a pure
  local read with no fetch (`SKILL.md:433`, `git-workflow.py:966`); `no_remote`'s documented meaning as
  *"branch never pushed"* (`SKILL.md:446`); the `ahead`/`no_remote` → re-fire rule
  (`phase-6-finalize/SKILL.md:547`, `:659`, `standards/push.md:115`); a second `no_remote` string in
  `_cmd_baseline_reconcile.py:349`.
- **REPORTED (consumer repo, first-party to them)**: the merged-then-`no_remote` sequence on PR #149 and
  the logged decision to skip. ⚠ **Not reproducible from this checkout** — but ⭐ **the mechanism is fully
  established from our own source**, so the report supplies the incident, not the diagnosis.
- ⛔ **NOT ESTABLISHED**: whether any run has actually re-pushed a merged branch. ⚠ **The only observed
  instance was saved by an agent declining the rule.** D0 should say whether prior occurrences are
  detectable at all — **and if they are not, say so** rather than implying none happened.
- **HYPOTHESIS**: the ancestor-of-`origin/{base}` check is a sufficient discriminator. ⚠ Cheap and local,
  **but unverified against the pruned-ref case** — a pruned local ref on an unmerged branch would still
  read `no_remote` and is genuinely a re-push. **D1 must handle all three causes, not two.**

## Expected Surface

- **OBSERVED**: `workflow-integration-git/scripts/git-workflow.py` — `branch-sync-state`
- **OBSERVED**: `phase-6-finalize/SKILL.md` Step 3 item 1 (the re-entry branch) and `standards/push.md`
- **HYPOTHESIS**: `workflow-integration-git/scripts/_cmd_baseline_reconcile.py` — the second `no_remote`

## Dependencies and Sequencing

- ⚠ **Same file as `PLAN-TRUTH-054`** (`_cmd_baseline_reconcile.py`, if D0 confirms the shared token) and
  the same *wrong-read-that-writes* class. ⛔ **SERIALIZE; evaluate absorption at outline** — 054 already
  owns a stale-anchor defect in that file.
- ⚠ Adjacent to `PLAN-TRUTH-050` — resumed/multi-session finalize tails are the condition that reaches
  this path. **Cite, do not merge.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-058-no-remote-conflates-never-pushed-with-merged-and-deleted-and-the-documented-response-is-destructive.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
