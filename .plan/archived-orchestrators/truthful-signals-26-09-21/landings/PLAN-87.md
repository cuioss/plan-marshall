# Landing Analysis: PLAN-87 — YAML Infrastructure Paths Classify Beyond `unknown`

epic: truthful-signals
workstream: WS-01
pr: 1024

> Merged as `817062688`. Cross-repo origin: raised by API-Sheriff's `plan-25-benchmark-suite-completion`,
> launched over-cap as a recorded one-off. 4/4 shipped. 3h20m worked / **24h4m wall** / 2.8M tokens.

## What shipped — and the spec's own options were all rejected

⭐ **D1's gate resolved against ALL THREE options the spec offered**, and the operator confirmed a
fourth. This is the verify-first contract working exactly as intended: the staged options were
hypotheses, and the gate killed them.

- **Option 1 (give `pm-dev-oci` the Axis-B API) was STRUCTURALLY IMPOSSIBLE**, not merely undesirable:
  `discover_build_extensions()` reads a **hard-coded tuple scoped to plan-marshall's own skills root**,
  so a `pm-dev-oci` Axis-B class *would never be found*. ADR-004 had already rejected it on other
  grounds. ⚠ **The spec presented option 1 as the leading candidate** — worth remembering when judging
  how much weight a staged option list deserves.
- **Option 3 (a CI/infra domain)** would have stamped `build_class=verify` on CI-workflow edits,
  triggering a **full reactor verify per workflow change**.
- **What shipped instead:** ADR-004's third amendment — **Axis-B absence ≠ classification absence** —
  plus Stage-3 **owner-less infra-config recognition** in the aggregator, symmetric with the already-
  blessed extension-agnostic *documentation* recognition. The fix completes an existing mechanism
  rather than adding a domain.

Also shipped: Axis-B attribution corrections across 5 contract docs, and route-set /
completeness-denominator non-regression assertions — the guard against the D2 hard constraint
(`config` routes must not enlarge the completeness denominator) that the spec required.

## ⭐ The review saga is the most valuable output, and it settled PLAN-92's open question

**16h32m of the 24h wall time was 6-finalize, almost all bot-review waits.** What was learned:

1. ✅ **U1 IS SETTLED — a force-push DOES trigger a review.** *"The pre-merge force-push was a
   new-commits event, which triggered a real review."* CodeRabbit then produced a nitpick and PR-Agent a
   genuine clean verdict, after both had refused. `SKILL.md:161`'s "debounced or skipped on a
   force-push" caveat is not what governs. **PLAN-92 D4's rebase-and-push primary path is confirmed.**
2. ⭐ **The governing rule: CodeRabbit reviews on EVENTS, not timers.** So **sleeping alone accomplishes
   nothing** — the sleep is a precondition for an event, never an action in itself.
3. ⛔ **A premature trigger comment is actively harmful.** Manual `@coderabbitai review` retries *"each
   consumed an attempt and reset the window — 58 min → 2 min → 59 min."* This **supersedes** the earlier
   reading that a premature trigger merely no-ops, and turns "never trigger before the ETA" into a hard
   cost-avoidance rule.
4. ⚠ **#1021's refusal-recognition caught NEITHER phrasing** while `automatic-review` reported
   `0 comment(s) found` — reading as reviewed-and-clean. **This contests the credit PLAN-92 currently
   gives #1021's generic recognizer**; D1 must re-verify against the real bodies from #1024 and #1032.

All four routed into **PLAN-92**, which now carries the corrected D4 sequence: *wait out the window →
generate a new-commits event → verify a review landed*, with the comment as a fallback that may fire
**only after** the window elapses.

## Three defects, all logged

- ⛔ **`fetch_findings` stored a comment authored by `cuioss-oliver` despite
  `--enabled-bots coderabbit,sourcery,pr-agent`.** Under `pre_merge_comment_barrier: fail_into_loopback`
  that is an **infinite loop** — triage replies, the barrier re-fetches the reply, loops back. Broken
  only by manually suppressing the finding. → **PLAN-92 as new defect 6.** ⚠ It interacts with decision
  7: ingesting an *unclassified bot's* findings must not extend to **our own replies** — "a bot we have
  not classified" and "not a bot at all" are different cases.
- **The orchestrator's pinned cwd silently reverted to the main checkout across background-job
  boundaries**, so the next leaf inherited main and created an **orphan plan dir**. Lesson
  `2026-07-28-11-001`. Harness/infra class — matches the standing UNOWNED-INFRA watch.
- **`references.affected_files` under-tracked by one file** (`manage-config/data-model.md`), caught by
  plugin-doctor — the same under-tracking class PLAN-61 owns.

## Two judgment calls — both defensible, one worth watching

- **A duplicated `_real_build_extensions()` test helper was accepted rather than fixed**, flagged
  independently by `finalize-step-simplify` **and** CodeRabbit. Rationale: the repo has no shared
  test-conftest convention, so deduping an 8-line helper meant inventing cross-suite test
  infrastructure. **Reasonable** — but two independent reviewers converging is a signal, and the
  *absence of a conftest convention* is the real finding. Recorded as a watch, not a plan.
- **`worktree-remove --force` was used against the standard's never-force rule**, after verifying zero
  untracked files and that the only changes were the timed-out removal's own deletions of files present
  on main. ⚠ **Correct call, wrong precedent risk:** #1023 faced the same timeout and chose the opposite
  (restore the deleted files, retry non-force). **Two runs, two different resolutions, both defensible**
  — the standard should say which is preferred rather than leaving it to per-run judgement.

## Reconciliation

- [x] `status` → shipped; `pr` = 1024; `landing` = landings/PLAN-87.md
- [x] Review findings routed into PLAN-92 (U1 settled, D4 reframed, defect 6 added)
- [x] Inbox checked — PLAN-87 wrote no messages
- [ ] `plan_marshall_plan_id` — not reported; left empty rather than guessed
- ⚠ **Downstream still owed by the operator:** API-Sheriff's `plan-25` resumes only after this is
  **released and reinstalled** there. A merged fix that is not installed unblocks nothing.
