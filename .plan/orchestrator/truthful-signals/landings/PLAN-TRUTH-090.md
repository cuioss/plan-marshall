# Landing — PLAN-TRUTH-090 (PR #1371)

**Plan**: `git-artifact-scanning-and-destructive-recovery`
**PR**: #1371 · **merge commit**: `8bc4a68f6` · **state**: merged (corroborated via `ci pr view`)
✅ **CLOSED 2026-08-31 on a deferred finalize re-entry.** Corroborated first-party: only the main worktree remains (`git worktree list`), the plan dir is at `archived-plans/2026-08-31-git-artifact-scanning-and-destructive-recovery`, and `manage-status list` returns no live plan. **The single-copy-state hazard is cleared.** The re-entry ran the deferred tail only — move-back (2 logs folded), `realized_footprint` captured (21 files) before removal, worktree-remove (213,021 scratch entries), branch delete, ref prune, archive.

⛔⛔ **THE RE-ENTRY REPORT'S HEADER SAYS "9 deliverable(s) shipped, all green" AND THAT IS A REGRESSION IN THE RECORD, NOT NEW EVIDENCE.** The first report said *"9 shipped, 2 reported PARTIAL"* and named them: TASK-015/016/019 carry no executed red-first evidence. **The re-entry executed no deliverable** — it ran move-back, worktree-remove and archive. Nothing it did could have converted a hand-traced RED-before into an observed one. ⇒ **The PARTIAL debt STANDS**; "all green" is the renderer summarising a completed step list, and reading it as a deliverable verdict would retire a disclosure the plan itself volunteered.

## Deliverable fidelity — 9 shipped, 2 reported PARTIAL

⭐ **The PARTIAL disclosure is the most valuable thing in this report.** TASK-015/016/019 carry **no executed red-first evidence** — the surface is orchestrator-tier, so the RED-before half is **hand-traced rather than observed**. The run put this in the PR body and the landing message rather than letting 9-of-9 stand.

⛔ That is exactly the property `PLAN-TRUTH-116` ("a test or fixture that cannot fail") exists to protect: a test whose red state was never witnessed is not evidence that the fix works, and a plan reporting it as shipped would be a false green. **Do not treat these two deliverables as closed.** They are recorded here as open verification debt against the shipped code.

## ⛔⛔ The blocker that deferred archive is NOT PRESENT NOW

The run reported: *"blocked by a stale merge-lock waiter at the FIFO head with no holder. `release --require-stale` evicts stale holders only; no verb covers a stale waiter."*

**Checked first-party from the main checkout:**

| Probe | Result |
|---|---|
| `merge_lock check --plan-id git-artifact-scanning-and-destructive-recovery` | **`status: free`** |
| `.plan/local/merge-queue.json` → `waiting` | **`[]` — the FIFO queue is EMPTY** |

⇒ **Nothing is blocking the re-run NOW.** ⛔ **Read only that much from this table** — see the retraction immediately below for why it does not license any claim about whether the plan was blocked when it looked. For reference, `merge_lock.py`:118-125 documents `_locks_core.holder_is_dead` and states that *"the same predicate prunes dead FIFO-queue entries so a crashed waiter's entry never blocks the front indefinitely"* — a real mechanism, but **not** evidence that the plan's observation was mistaken.

⛔⛔ **CORRECTION, 2026-08-31 — THIS SECTION'S ORIGINAL VERDICT WAS WRONG AND IS RETRACTED.**

The original text called the plan's conclusion an archetype error ("looked for a VERB, found none,
concluded STUCK"). **The inbox drain refuted that.** `review-apparatus-022` item 3 records the same
state from the other side, first-party: **`merge.lock` was FREE while `merge_lock acquire` returned
`blocked` with `waiting_count: 2` and `blocking_plan_id: null`.** The FIFO head was held by
`detector-and-auditor-integrity` with no session polling it, and clearing that entry released it.

⇒ **`check` and `acquire` DISAGREE — `check` reads the mutex, only `acquire` sees the FIFO queue.**
This orchestrator probed with `check`, saw `free`, and concluded nothing was blocking. **The plan was
looking at a real blocked state whose own diagnostic named nobody.** The plan was right; the probe was
wrong.

⭐ What survives unchanged: the queue is empty NOW (`waiting: []`), the FIFO head has since cleared,
and **the re-run is unblocked**. The operational conclusion held for the wrong reason — which is
exactly the failure this epic exists to catch, committed here by its own orchestrator with the
instrument-choice error that produced it (the fifth such error in that session).

⚠ **The earlier "honest limit" is now SETTLED, not open**: the drain supplied the missing half. The entry was real and was cleared after the observation — it was never the never-blocking case.

## Owed — and it is a real re-run, not a formality

```text
/plan-marshall action=finalize plan=git-artifact-scanning-and-destructive-recovery
```

⛔ **The worktree is RETAINED and holds the only copy of plan state.** Until move-back and archive complete, that state exists in exactly one place. Do not remove the worktree by hand — the leaf-validator-yield precedent shows a hand worktree-remove loses the plan directory outright.

## Reviewer coverage — the merge did not clear it

**No CodeRabbit review object covers `b9506f81a`.** The PR merged under an explicit operator HEAD-bound override. `automatic-review` reports 9 findings → 2 loop-backs → 0 pending, and `review-retrospective` reports 3 reviewers with **1 producing findings**.

⛔ Read precisely: *findings were filed and fixed* is not *the merge candidate was reviewed*. This is the R95/R104 false-green in the merge path, appearing again — recorded, not re-litigated. The `merge-queue.json` `rate_windows.coderabbit` entry corroborates the mechanism: `pr_number: 1371`, `attempts: 2`, no holder.

⭐ Contrast with `-109` one day earlier, where waiting out the same reviewer recovered 5 findings that 5 self-review passes had missed. **Same reviewer, same week, opposite decisions, and the two outcomes are the evidence base for `review-apparatus`'s wait-vs-override question.** Routed there.

## Cost

4h34m worked / **35h5m wall — 87% idle**, 6.2M tokens, **143M billing-weighted**, finalize alone about half.

⛔ Third consecutive landing where finalize dominates both idle and billing (`-113`: 14h18m idle, 54.5% billing; this one: 87% idle overall). That is `PLAN-TRUTH-107`'s subject measured a third time; the frequency question is settled and needs no further measurement.

## Reconciliation actions

- Row `running → shipped` — the MERGE is real. ⛔ The two PARTIAL deliverables and the unfinished finalize are recorded here and in the resume anchor; `shipped` names the landing, never the plan's completeness.
- `pr: 1371`, `landing` stamped.
- `PLAN-TRUTH-089`, `-097`, `-099`, `-100`, `-104`, `-106`, `-107` lose their collision with this plan — **`-100` is finally unblocked**, after its collider moved from `-113` to `-090` (R142).
- ⚠ `deploy-target` emitted **v0.1.1570**, contributing to a nine-version pin gap (`0.1.1571` vs `0.1.1562`). ✅ **REPAIRED by the operator 2026-08-31** — the gate now passes at `0.1.1571`, verified four ways.


## The deferred re-entry (2026-08-31) — two deviations and one new defect

### ⭐⭐ Deviation 1 — `merge_commit_sha` would have stamped ANOTHER PLAN'S COMMIT, and this is the SECOND independent instance

`branch-cleanup` prescribes recording `rev-parse HEAD`, which silently assumes the **synchronous** path where HEAD *is* the landing commit. On this deferred re-entry `main` had advanced to `7845a4b9a` (sibling PR #1370). The run recorded this plan's own landing commit `8bc4a68f6` instead, **corroborated against `ci pr view`'s `merge_commit_sha`**.

⭐⭐⭐ **This is `review-apparatus-022` item 4, independently reproduced.** That message — drained into `PLAN-TRUTH-111` hours before this re-entry ran — reported the same hazard from PLAN-PR-025A's landing, where switch-and-pull pulled 0 commits because main had already advanced to a sibling's landing. ⇒ **n = 2, two epics, two plans, same mechanism.** It fails **silently**: the stamped sha is well-formed and wrong, and it seeds the footprint fallback with another plan's diff. ⛔ **It appears ONLY under concurrent or deferred landings** — precisely the regime this epic now runs in at N=3.

### Deviation 2 — `prune-local-and-remote-ref` returned `branch_delete_failed`

`worktree-remove` had already deleted the local branch, so the verb failed on its first half and **never reached the remote half**. The run pruned the stale `refs/remotes/origin/feature/…` with the targeted single-ref deletion the standard sanctions. ⭐ A two-step verb whose first step failing skips the second, where the two steps are independent.

### ⛔ New defect `4cb145` (bug, non-blocking) — worktree-remove does not reconcile the metadata it invalidates

After a **successful** removal, `get-worktree-path` still reports `worktree_state: materialized` at the deleted path. Two live consequences were observed, and the first is the more dangerous:

- **`ci --plan-id … pr view` returns `error_cause: auth_failed`** — ⛔ **a FALSE cause.** `gh auth status` shows two logged-in accounts and the same call with `--project-dir` succeeds. A stale-metadata failure is reported as an authentication failure, sending a reader to fix credentials that are fine.
- `phase_handshake verify` refuses with `worktree_unresolved`.

⭐ It also **refutes `branch-cleanup.md` line 80's claim** that `--plan-id` *"keeps working post-removal"* — that sentence relies on a `use_worktree=false` fallback which removal never sets.

⚠ **Cross-epic note:** `review-apparatus` records the `ci pr view` `auth_failed` misclassification among the items it KEPT. This defect supplies its **root cause** — it is not an auth problem at all. Worth telling them; the two records are the same symptom from opposite ends.

### ⚠ The cost figures under-report and the report says so

`record-metrics` had already run before the deferral, and the pipeline forbids re-running it post-archive — so the 4h34m / 35h5m / 6.2M / 143M figures **exclude this re-entry session entirely**. The run disclosed this rather than letting the totals stand unqualified. ⛔ Any per-plan cost comparison using `-090` must treat its total as a **floor**, not a measurement.
