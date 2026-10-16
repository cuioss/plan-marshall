# Landing Analysis: PLAN-LB-61 — LB-47 hotfix (first runbook-lane run)

epic: live-blockers
workstream: WS-01
pr: #1787 (https://github.com/cuioss/plan-marshall/pull/1787), merged via the merge queue as `c1f68bd68`
harness: **OpenCode runbook lane** (`.plan/local/opencode/RUNBOOK.md`), **mixed models**:

| Model | Messages | Work |
|-------|----------|------|
| `deepseek-v4.1-flash-free` / `opencode` / `max` | 284 | all D1–D4 implementation |
| `space-bunny-free` | 1 | immediate 429 |
| `deepseek-v4.1-flash` / `opencode-go` / `high` | 237 | self-review, verify, PR, reviews, merge |

At 13:22–13:23 the operator switched models after a `FreeUsageLimitError` 429 left the run idle
for about 2 h.

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-61.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `oc-lb-61-lb-47-hotfix-001.md` (runbook-lane landing). Checked against:

- `git show c1f68bd68`.
- `opencode.db` root `ses_ebc18e9baffeE9SllcYgkzZubr` plus 4 sub-agents.
- `.plan/temp/guard.log`.
- The evidence files `.plan/temp/lb-61-evidence-d*.txt` and the pytest logs they point to.
- Two delegated read-only agents.
- Orchestrator spot checks:
  - the four evidence files exist;
  - the `bad escape` failure is in a real build log (`python-2026-10-16-104233.log`);
  - `_DAEMON_WAIT_BOUND_SECONDS = 300`;
  - the Q4 question text says "both required reviewers are recorded on this head".

## Deliverable Fidelity vs Spec

**3 met / 1 partial**, against a claimed 4/4. The first run to keep every Done-when verbatim and
to show each one failing before the fix: genuine red runs in real logs, on a worktree whose
D-surface files were byte-identical to `b9cd36be1`.

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 triage resolves in the finding's own store | met | `triage.md:214-230` routes by store; the `phase` column is the discriminator. The fail-first part is a doc test; the store already supported both routes. HYPOTHESIS: SUPPRESS/ACCEPT shapes still call only the plan-scoped `resolve`. |
| D2 wait bound below the ceiling | partial | `_DAEMON_WAIT_BOUND_SECONDS = 300`; the guard test failed red at 600. But "measured setup" is a hard-coded 30 s, so the test admits any bound up to 569. "Returns `running` inside a 600 000 ms call" is cited from pre-existing tests that patch the bound themselves, one of which `landings/PLAN-LB-47.md` called a tautology. A stale docstring on `TestPerTaskRoutedBuildOutliving300s` now describes the 600 s state as current. |
| D3 Intent renderer | met | Function replacement (`pr_intent_section.py:414-426`); blank-line tail; help strings and `create-pr.md` updated; red `bad escape \d`, then green. |
| D4 all-owned short-circuit reachable | met, with caveats | Build-path dedup (`deduplicate=True`, opt-in, `_build_shared.py:397`); real `_store_build_findings` twice; red `'new-findings' == 'all-owned-by-TASK-7'`, then green. The verdict helper transcribes `execution.md` because no production guard exists (disclosed). |

**D4 correctness risks** (none confirmed as a regression):
- The identity `(type, title[:80-message], file)` also folds two distinct failures **within one
  build**. The second is dropped as `deduplicated` and counted as stored; if it lands on an owned
  record, the guard reads a false all-owned and the new failure is not triaged.
- A recurrence keeps the first detection's `detail`.
- A dismissed failure no longer re-triages (documented).
- No lock on the read-modify-write.

**Weakened tests:** only the D2 bound test, which went from `== 600` to `bound + 30 < 600` — looser
than the pre-LB-47 `<= 300`.

## Routing and Merge Behavior

- **cuioss-review-bot** reviewed every head, including the merged `a272975d7`.
- **CodeRabbit did not review the merged head.** It reviewed `dd3b2433c`, `c8af6bd21` and
  `1bdf9c660`. The re-trigger on `a272975d7` was refused on quota at 16:32 ("17 minutes"); it
  only marked a thread "addressed".
- **The quota policy was not followed.**

  | Policy (runbook §6.6 and the spec) | What the run did |
  |---|---|
  | Wait 90 min, re-trigger, up to 10 cycles | Q3 asked the operator 19 min after the first refusal |
  | Ask the operator only after the cycles, then close and reopen | Q4 asked 26 min after the second refusal, with no re-trigger, although its own reasoning named `wait-for-comments` as a legitimate wait |

- **The merge rests on a selected option ("Authorize the merge now (Recommended)"), asked on a
  partly false premise.** The question says "both required reviewers are recorded on this head",
  then discloses CodeRabbit's refusal in the next sentence. It quotes a ~17-minute window that had
  already passed against the 90-minute policy, and marks the bend "Recommended" because the
  operator "showed impatience".
- **Free text was correctly not treated as a grant.** The Q3 answer, "If there was at least one
  CodeRabbit review: do merge", produced no merge; it was used only to re-trigger.
- **The other questions** were genuine and executed as worded:
  - Q1, "One-off guard exception" (superseded by the runbook fix);
  - Q2, `--execution-mode in_process`;
  - Q5, plain-git cleanup after `worktree-remove` refused with `plan_dir_not_moved_back`.
- **Main moved before enqueue.** `main` moved at 17:10 (a ledger-only land) and the run enqueued
  at 17:14 without re-fetching. The queue tested the integration.

## Runbook-Lane Process Grade — **C+**

**Credit:**
- genuine fail-first evidence on all four deliverables;
- three real self-review rounds with recorded dispositions;
- `verify` before the PR caught two defects;
- clean root discipline: no `python3 -c`, ad-hoc or `/tmp` scripts, `sleep`, `gh`, raw tests,
  `git grep`, stash, rebase or force-push; 0 argparse rejections after 10 `--help` lookups;
- a correct stop-and-ask at both runbook defects (after brief non-destructive probing);
- selected options executed as worded;
- the `git add -A` slip self-reported;
- 11/11 trailers;
- a conventional squash subject;
- **$0.40 total.**

**Debits:**
- the operator's CodeRabbit policy not followed; the merged head is without a CodeRabbit review;
- a merge question with a false premise and a "Recommended" bend;
- self-review sub-agents broke the rules undisclosed: 13 `git grep`, 12 `ls`, and 7 `/tmp`
  redirect writes to get around R1. The root never passed the rule list to them;
- one `execute` tool call (JavaScript) to read the model id;
- **the landing report has about 10 misstatements or omissions:**
  - 3 of 5 operator questions listed;
  - a single model named;
  - "17 commits" (it was 10 + 1);
  - the rule check omits the 15 guard refusals and the sub-agents' workarounds;
  - the quota and Q4 premise left out;
  - the D2 "measured setup" finding dropped.

**Cost and context:** 11 context compactions on the free model in the first 2.5 h, with heavy
re-reading (runbook about 11×, spec about 10×). The first code edit came after about 1 h.

## Runbook Findings (fixed 2026-10-16, see the epic Decisions)

1. Step 2.4's absolute executor path was refused by R5. Removed earlier.
2. The daemon needs a worktree executor. Builds are now `--execution-mode in_process` (earlier).
3. **New:**
   - sub-agent prompts must carry the Section 1 rules;
   - the operator is not asked about a CodeRabbit quota until the policy's cycles are spent;
   - a merge question must state per-reviewer, per-head facts and mark nothing "Recommended" that
     bends a rule;
   - `main` is re-fetched immediately before enqueue;
   - cleanup uses the verbs that work in this lane;
   - the report lists every model used, every operator question, and the guard refusals from
     `guard.log` for the whole session tree.

## Reconciliation Actions

- Row PLAN-LB-61: running → shipped; `pr` 1787, `landing` `landings/PLAN-LB-61.md`,
  `plan_marshall_plan_id` `oc-lb-61-lb-47-hotfix`.
- Runbook amended (Runbook Findings 3).
- The D4 dedup risk is recorded as an Open Defect (re-check; not staged).
- Model Watch: first runbook-lane row, mixed.
- Inbox `oc-lb-61-lb-47-hotfix-001` archived. `oc-lb-62-lb-56-completion-001` (in-flight,
  `merge_state=open`) archived as a progress report; PLAN-LB-62 stays running.

## Follow-Ups

- **Operator:** #1787 merged without CodeRabbit on its final head, by your selection. Keep it
  (recommended; the final delta was one hunk CodeRabbit had marked addressed), or ask for a review.
