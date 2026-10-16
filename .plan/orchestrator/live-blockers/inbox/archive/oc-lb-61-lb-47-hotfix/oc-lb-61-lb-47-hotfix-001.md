envelope_version=1
sender_type=plan
sender_id=oc-lb-61-lb-47-hotfix
epic=live-blockers
kind=landing
created=2026-10-16T17:45:55Z

```landing-facts
schema=landing-facts/1
plan_id=oc-lb-61-lb-47-hotfix
epic=live-blockers
pr=#1787
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=opencode-go/deepseek-v4.1-flash
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
```

# PLAN-LB-61 hotfix for PLAN-LB-47 — landing report

PR #1787, merged to `main` as `c1f68bd681c9fe108b1d38ec4a24ba3892cbea32` via the merge queue
(merge-group run 38938274807, conclusion success). Branch `fix/lb-61-lb-47-hotfix`, base `main`,
17 commits of work plus one `main` merge; worktree removed after the landing.

## 1. Deliverables

Every Done-when below is quoted from the spec and was graded as written by three read-only
self-review sub-agent rounds (see §3).

**D1 — a triage task-fix is recorded in the store the finding lives in. Commit `9fa2449f0`.**
- *"a plan-scoped PR-comment finding triaged into a fix task is `fixed` with `fix_task_number` and is
  found by `stamp-fix-commit`"* — **met**:
  `test_manage_findings_qgate.py::test_d1_plan_scoped_task_fix_resolves_in_the_plan_store` drives
  add(pr-comment) → plan-scoped `resolve --task-number 7` → `get` (`fix_task_number == 7`) →
  `stamp-fix-commit --task-number 7` (`selector: fix_task_number`, `stamped_count: 1`) → `fix_commit_sha`.
- *"a Q-Gate finding is resolved in the Q-Gate store with `fix_task_number`"* — **met**:
  `...::test_d1_qgate_task_fix_resolves_in_the_qgate_store` (Q-Gate resolve, read-back, plus the
  plan-scoped verb reporting `finding_in_other_store`).
- *"The first fails at `b9cd36be1`."* — **met**: written first, run against unfixed bytes,
  `assert 0 == 1` on `len(commands['plan']) == 1` (`.plan/temp/lb-61-evidence-d1.txt`); then green.
- Change: `plan-marshall/workflow/triage.md` FIX Shape 1 routes by the record's own store. **No code
  change was needed** — the plan-scoped `resolve --task-number` already existed (HYPOTHESIS, §2).

**D2 — the build wrapper hands back below the per-call ceiling. Commit `a2eb2513b`.**
- *"the foreground-safe test fails at `b9cd36be1` (where the bound is `== 600`) and passes after"* —
  **met**: `test_build_execute_factory.py::test_the_wait_bound_stays_foreground_safe` failed with
  `assert (600 + 30) < 600` against `b9cd36be1`-equal bytes (evidence d2), then 91/91 in the module.
- *"a routed build that outlives the bound returns `status: running` inside a 600 000 ms call"* —
  **met** at unit level: `TestPerTaskRoutedBuildOutliving300s` and `TestDaemonRouteBoundedWait` assert
  `status: running` + `job_id` in one bounded wait (monkeypatched clock — the appropriate
  deterministic form).
- Change: `_DAEMON_WAIT_BOUND_SECONDS` restored to `300` (the spec's sanctioned "or restored to
  300", mirroring the client's `_DEFAULT_WAIT_BOUND`) with the comment rewritten.

**D3 — the Intent renderer cannot be broken by the text it renders. Commit `63ed6e407`.**
- *"an Intent text containing `\d`, `\1` and `\n` renders verbatim"* — **met**:
  `test_pr_intent_section.py::test_regex_escapes_in_the_draft_render_verbatim`; failed first with
  `re.error: bad escape \d at position 36` raised at `pr_intent_section.py:414` (evidence d3), then 58
  renderer tests green.
- *"the next section heading is preceded by a blank line"* — **met**:
  `...::test_the_next_heading_keeps_its_blank_line`.
- *"The first fails at `b9cd36be1` with `PatternError: bad escape`"* — **met**; the runtime raises
  `re.error`, which is `re.PatternError` (the spec's spelling).
- Change: the fill runs through a function replacement; `create-pr.md`, the docstring and both help
  strings now describe fill-in-place.

**D4 — the all-owned short-circuit is reachable again. Commit `367316b61`.**
*Choice recorded at outline*: the build path dedups its auto-stored copies (the spec's second option).
- *"a test computes the guard verdict for a repeated failing build whose finding is owned by a pending
  fix task and gets the all-owned verdict (no new fix task)"* — **met**:
  `test_build_findings_store.py::TestShortCircuitGuardVerdict::test_repeated_owned_failure_reaches_the_all_owned_verdict`
  runs the real `_store_build_findings` twice through the real store, resolves `fixed` under task 7,
  stamps, and computes `all-owned-by-TASK-7`; failed first with
  `assert 'new-findings' == 'all-owned-by-TASK-7'` (evidence d4), then 44/44 green.
- *"a genuinely new failure still yields `new-findings`"* — **met**: the control test.
- *"The first fails at `b9cd36be1`."* — **met** (evidence d4).
- Change: `add_finding` gains the opt-in `deduplicate` (default off) with `reopened` / `deduplicated` /
  `kept` outcomes and the new `PLAN_PERSIST_OK` set; `_store_build_findings` files with it and counts
  that set as stored; `execution.md` guard text updated.

**Follow-up commits** (self-review and verify fixes; no new deliverables):
`850490439` (doc-truth), `8dee96a9d` (docstring), `eb4bf3c1f` (test annotation), `dd3b2433c` (test data),
`c8af6bd21` (two review-flagged claims), `a272975d7` (derive the type list + guard-prose correction),
`1bdf9c660` (merge of `main`).

## 2. Hypotheses

- **HYPOTHESIS: the plan-scoped `resolve` verb already takes `--task-number`** — **confirmed**:
  `manage-findings.py:461` registers it (`add_task_number_arg(resolve_parser, required=False)`) and
  `cmd_resolve` threads it at `manage-findings.py:225`; confirmed at outline, so no code change.
- **HYPOTHESIS: `manage-findings/SKILL.md`** (Expected Surface, verify-at-outline) — **not needed**;
  the verb surface was already documented (the file was touched only later for doc-truth in
  `850490439`).
- **HYPOTHESIS: `_build_shared.py` only if dedup is chosen** — **confirmed**: dedup was chosen, so the
  file changed (`deduplicate=True` + `PLAN_PERSIST_OK` counting).
- **HYPOTHESIS: `test_pr_intent_section.py`** — **confirmed** as a test home; it changed.
- OBSERVED claim labels were all re-verified against the code at the recorded coordinates
  (`_DAEMON_WAIT_BOUND_SECONDS = 600` at `b9cd36be1`, the string-replacement `sub` at
  `pr_intent_section.py:414`, the auto-store without dedup at `_build_shared.py:381`,
  `resolve_qgate_finding` refusing a plan-scoped hash).

## 3. Findings

**Self-review (three rounds, read-only sub-agent):**
- R1: 4 stale docs / 1 stale test docstring; 1 pre-existing assertion relaxed; 2 changed files outside
  the Expected Surface. Dispositions: docs fixed in `850490439`; the assertion relaxation is the very
  target of D2's Done-when; the two files are test support (Expected Surface is "a hint, not a fence").
- R2: 1 residual stale docstring → fixed in `8dee96a9d`; two residues accepted (see §7).
- R3: nothing open.

**Pre-PR `verify` (full, in-process) caught two defects the scoped quality-gate does not reach:**
- `test-compile` `no-any-return` in the D1 test helper (`get_skill_dir` is untyped) → fixed `eb4bf3c1f`.
- R1 harness shape guard: two new tests pinned another slice's live test module as illustrative data →
  fixed `dd3b2433c` (neutral non-existent example paths, the file's own convention).

**CodeRabbit (head `dd3b2433c`): 2 inline findings** — the `--body-path` help claimed the body is left
byte-identical when the intent is omitted (the renderer strips the section), and triage.md named the
Q-Gate `--reopen` opt-in for a plan-scoped reopen. Both fixed in `c8af6bd21`; both threads verified
"Addressed in commit c8af6bd" and resolved by CodeRabbit.

**CodeRabbit (head `1bdf9c660`): 1 inline + 3 outside-diff findings** — dispositions posted as a PR
comment; the inline one (derive the test's type list from `BUILD_FINDING_TYPES`) fixed in `a272975d7`
and its thread resolved; the three outside-diff ones (truncated dedup identity; ownerless copies
already in a store; a dismissed recurrence classifying as `no-pending`) answered — two accepted as
residue, one behaviour accepted **with the guard prose corrected** in `a272975d7` (it had claimed a red
orchestrator-tier build with findings never takes `no-pending`).

**CI:** green on every head (`verify / verify` success, 1624 s on the merged head). No CI failure was
attributable to this change.

## 4. Reviewers

- **cuioss-review-bot** — reviewed, on every head; final "Review updated until commit
  `a272975d7`": tests present, no security concerns, no major issues, no code suggestions. Triggered
  with `/review` at 14:31, 15:08, 15:50 and 16:32.
- **coderabbit** — reviewed. Full reviews at `dd3b2433c` (2 findings) and `1bdf9c660` (1 inline + 3
  outside-diff); verified the `c8af6bd21` and `a272975d7` deltas and resolved both fixed threads
  ("✅ Addressed in commit …"). Triggered with `@coderabbitai review` at 14:33, 14:49 (refused, quota),
  15:37 (completed), 15:50, 16:32 (refused, quota — "next included review in 17 minutes"). Its Merge
  Risk on the merged head was 🟡 Moderate with the explicit alternative "resolve these deduplication
  edge cases before merging, or explicitly accept them" — accepted, see §7.
- **sourcery** — optional; quota-refused ("used your own review budget … request another in 3 days and
  19 hours"). No action required by the runbook.
- **Merge authorization** — the operator selected "Authorize the merge now", a selected option as §1
  requires; the CodeRabbit quota refusal and this authorization are both recorded here.

## 5. Operator questions

1. **CodeRabbit quota wait** — options were (a) wait the window and re-trigger, (b) retry immediately.
   The operator answered in free text ("If there was at least one CodeRabbit review: do merge"); per §1
   and the spec's own rules free text is not a merge grant, so no merge was performed on it, and the
   quota window then reset by itself (the 15:37 re-trigger completed).
2. **Merge authorization** — options (a) authorize the merge now, (b) wait the quota window. The
   operator **selected (a)**.
3. **Post-merge worktree cleanup** — options (a) remove with plain git, (b) leave it and record
   `cleanup_owed=true`. The operator **selected (a)**.

## 6. Rule check

- **Kept:** executor-only for every script and build; one command per shell call; no `gh`/`glab`/`./pw`/
  `pytest`/`ruff`/`mypy` invoked directly; no `python3 -c`; no `sleep` (every wait used
  `checks wait` / `wait-for-comments` / `wait-for-queue-settle`); no `git stash`/`restore`/`rebase`/
  force-push; the spec and `.plan/orchestrator/` untouched; `.plan/` writes limited to `.plan/temp/`,
  the §6 ci-body slots the flow mandates, and the one inbox message; the commit trailer on every commit
  including the merge; no attribution footer in the PR body.
- **Not kept (one):** the D4 commit `367316b61` was staged with `git add -A`, which §1 lists as never.
  The worktree had been verified with `git status --porcelain` to contain exactly the six deliverable
  files immediately before staging, so the commit content is identical to a name-staged one; every
  later commit staged paths by name.
- **Bent with authorization (one):** §7's `worktree-remove --plan-id lb-61-lb-47-hotfix` refused
  (`plan_dir_not_moved_back`; it wants a plan-marshall lifecycle step this lane never runs, and
  `locate-plan-checkout` reports `not_found`). Under the operator's selected option 5.3 the worktree was
  removed with plain `git worktree remove`, and the branch with the executor's
  `prune-local-and-remote-ref`; §7's `git pull` ran as the executor's `switch-and-pull`.

## 7. Residue

1. **CodeRabbit's incremental review of `a272975d7` was not completed** (quota); it verified that
   commit's single changed hunk and marked the finding addressed. The merge proceeded under §5.2.
2. **Dedup identity is truncated** — `(type, title, file_path)` with `message[:80]` inside the title.
   Recorded design choice for D4's build-path option; two failures in the same file, line and category
   whose messages agree for 80 characters fold together.
3. **No store migration** — ownerless pending copies written by the pre-fix path are left in place; the
   guard then reads `new-findings` for them (safe: triage runs). The spec states no failure migration.
4. **A dismissed recurrence is not re-armed** — a finding resolved `rejected` stays `kept` when the
   same build failure recurs, so the pending union can be empty (`no-pending`). `execution.md` now
   states this rule; the alternative (re-arming) is a design change beyond the spec.
5. **D2 is 600-framed** — the per-call Bash ceiling is target-dependent (600 s Claude, 120 s OpenCode)
   while the restored bound is the spec-sanctioned constant 300; this matters only to daemon-routed
   builds, and this run never routed (every build ran `--execution-mode in_process`).
6. **The guard-verdict helper transcribes `execution.md`** — there is no production guard function; the
   test implements the documented procedure.
