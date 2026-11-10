envelope_version=1
sender_type=plan
sender_id=rb-lb-131-foreign-gate-default-branch
epic=live-blockers
kind=landing
created=2026-11-10T06:31:08Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-131-foreign-gate-default-branch
epic=live-blockers
pr=#1948
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=4
review_body_findings_handled=4
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present — the R5 pre-tool-use guard is active on opencode; it refused one call from this run (recorded below).

# PLAN-LB-131 landing — the foreign gate never takes the default branch as the change's branch, and a cleaned-up merged branch still reads merged

PR #1948 merged into `main` as `652d977cf48024e28b1ac3e0014c2d061a0ec5ec` (merge queue, merge_group run `42711330707` success). Worktree removed, branch pruned local and remote, main switched and pulled to the merge commit.

## 1. Deliverables

Order vocabulary: `test-first` = the test was written and seen failing against the unfixed code; `mutation-after` = the failing output came from mutating/reverting the committed fix; `none` = no failing output captured. Every Done-when below is **met**, all with `mutation-after` evidence.

**D1 — The default branch is never a change's branch, and a declaration wins over a checkout on it.** (`6731301e7`, formatting `9a963eba2`, lazy-read pin `88b0d5b44`)

| Done-when | Verdict | Test | Order | Failing run |
|---|---|---|---|---|
| undeclared + checkout `main` + default `main` → `error`, `unresolved[0].reason` starts `branch_is_default`, `landing_branches == {}` | met | `test_a_checkout_on_the_default_branch_is_never_a_change_branch` | mutation-after | `9a963eba2` mutated; job `382e33616fab476a88a5235a103c1167`; `.plan/local/plans/NO_PLAN/build-results/plan-marshall/python-2026-11-09-092634.log` (failed `blocked` vs `error`) |
| declared `docs/x` + checkout `main` + default `main` → `clear`, branch `docs/x` | met | `test_a_declaration_wins_over_a_checkout_on_the_default_branch` | mutation-after | same run (failed `error` vs `clear`) |
| default unreadable + undeclared → `default_branch_unreadable` | met | `test_an_unreadable_default_branch_without_a_declaration_fails_closed` | mutation-after | same run (failed `clear` vs `error`) |

The replacement and the two test edits the spec requires are in: `test_the_plan_id_branch_is_never_the_fallback` is gone (its `main: merged` answer is one the real verb cannot give), the disagreement test now uses checkout `fix/other`, and the three must-hold cases stayed green in the same mutated run.

**D2 — A declared branch whose local ref is gone is resolved from the remote and, failing that, from its merged PR.** (`e51abb655`, tip-SHA probe `5b12a384f`, cross-repo filter + tests `e2b91a044`)

| Done-when | Verdict | Test | Order | Failing run |
|---|---|---|---|---|
| local ref missing, `origin/X` present → tip matches, reads `merged` | met | `test_a_branch_whose_local_ref_is_gone_is_resolved_from_origin` | mutation-after | `e51abb655` mutated; job `a65c00d8fbf44e7090428b708d16e1e9`; `.plan/local/plans/NO_PLAN/build-results/plan-marshall/python-2026-11-09-095318.log` (4 failed, 227 passed) |
| both refs missing, `ls-remote` empty, listing `[MERGED]` → `merged` | met | `test_a_branch_gone_everywhere_reads_merged_from_the_merged_pr` | mutation-after | same run |
| both missing, empty listing → error `branch_absent` | met | `test_a_branch_gone_everywhere_without_a_pr_is_branch_absent` | mutation-after | same run |
| (fix round 2) the push probe asks the resolved tip, not the branch name | met | `test_the_push_probe_uses_the_resolved_tip_not_the_branch_name` | mutation-after | `4efa48793` mutated; job `1b1f613eee36412086f74471097adc51`; `.../python-2026-11-09-152306.log` (1 failed, 231 passed) |

The stale-tip and truncation-ceiling keep-holdings are green, and `test_a_branch_absent_locally_is_resolved_from_the_remote` covers the `ls-remote` arm.

**D3 — The documents state the branch rule once and in the present tense.** (`6dad1e799`)

| Done-when | Verdict | Test | Order | Failing run |
|---|---|---|---|---|
| a doc test asserts `archive-plan.md` states the default-branch rule once and carries no "still holds" wording | met | `test_the_standard_states_the_default_branch_rule_exactly_once`, `test_the_standard_carries_no_obsolete_rule_wording` | mutation-after | `6dad1e799` mutated (both documents reverted); job `dd4efdf56a4d4427860ac66d16d1d763`; `.../python-2026-11-09-102528.log` (4 failed) |
| the module docstring names no plain ``main`` as a change branch | met | `test_the_module_docstring_names_no_plain_main_as_a_change_branch` | mutation-after | same run |

**Per-head test runs on pushed heads:** `6dad1e799` module-tests (33107 passed, 1 environmental failure on the target-tree precondition); `4efa48793` focused filters green; `5b12a384f` full `verify` green (33110); `e2b91a044` full `verify` green (33117); `a97f662bb` (post base-merge) full `verify` green (33135).

## 2. Personas and skills

- `persona-implementer` — the three production-code changes (`foreign_pr_gate.py`, `_github_pr.py`, `ci_base.py` docstring).
- `persona-module-tester` — every unit test added or changed.
- `persona-documenter` — D3's standards/module-docstring/comment edits.
- `persona-code-reviewer` — all three self-review rounds and the triage of every CodeRabbit finding.
- Domain skills per deliverable: **none named** by the spec, so `skills: none named` for D1–D3. No surface drift: every touched path is in the spec's Expected Surface.

## 3. Hypotheses

- D1 — *the CI abstraction has a verb that returns a repository's default branch*: **refuted**. `ci.py` exposes `pr`, `checks`, `issue`, `branch` (`delete` only), `repo` (`merge-queue`, `label`, `file`) and `org`; no routed-checkout default-branch verb (round 3 notes `org list-repos` reports a per-repo `default_branch`, which is not a checkout read). The gate reads git, as the spec's fallback describes.
- D1 — *`git ls-remote --symref origin HEAD` is available without credentials*: **confirmed** (`ref: refs/heads/main\tHEAD`; `refs/remotes/origin/HEAD` answers `origin/main`).
- D2 — *the GitLab landing-state handler resolves the tip the same way and has the same gap*: **refuted**. No landing-state verb or handler exists in `workflow-integration-gitlab`; recorded unchanged for that reason.
- D1/D2 OBSERVED claims all confirmed at the cited lines.

## 4. Findings

- **Self-review round 1** (7): api-contract.md stale (fixed), SKILL.md stale (fixed), CLI tests ran real git through the unconditional default read (fixed by the lazy read), no timeout on `_default_branch` (fixed: 60 s + `TimeoutExpired → None`), module docstring seam list (fixed), OPEN-before-MERGED precedence (kept fail-closed and documented), `deliverable-template.md` "one condition" framing (fixed). Open: none.
- **Self-review round 2** (4 new): N1 push probe used the short branch name (fixed in `5b12a384f`), N2 branch-absent wording said "no PR head" (fixed), N3 "fresh clone" docstring claim (fixed), N4 laziness not pinned (test added). All four fixed before the merge.
- **Self-review round 3** (post-merge verification, the limit): all four round-2 items **FIXED-CORRECT**; three deliverables met; five new low items **open** (see Residue).
- **CodeRabbit** (reviewed `5b12a384f`): `finding: coderabbit inline inline-1 — declined` (the spec fixes the local-then-remote resolution order; a stale local ref makes the gate block, never clear); `finding: coderabbit inline inline-2 — e2b91a044` (cross-repository PR filter); `finding: coderabbit nitpick nitpick-1 — e2b91a044`; `finding: coderabbit nitpick nitpick-2 — e2b91a044`. Both threads replied and resolved.
- **CI**: green on every head after the environment was reclaimed; no CI finding required a change.

## 5. Reviewers

| Reviewer | Role | Result | Head | History |
|---|---|---|---|---|
| coderabbit | required, quota-limited | **reviewed** `5b12a384f`; refused on `e2b91a044` and `a97f662bb` | review on `5b12a384f`, PR merged at `a97f662bb` (via its merge commit) | triggered 17:56 (refused, limit), waited 90 min, re-triggered 19:54 → reviewed 20:02; re-triggered after the fix push 20:25 (refused, 28 min), after the base merge 22:21 (refused, 56 min) |
| sourcery | optional, quota-limited | refused | — | triggered 17:56; refuses until ~2026-11-12 (250k diff-character budget) — does not gate |

**Standing review authorization (quota-limited reviewer).** All four conditions held on the merge head: a qualifying review exists (formal review on `5b12a384f`, its summary comment carries `final_review_risk_coverage` with `sourceCommitId=coveredCommitId=5b12a384f`, `kind=reviewed`); every finding from it is handled (2 inline — one fixed, one answered with a stated reason — and 2 nitpicks fixed, both threads resolved); it was re-triggered once after the last push (`a97f662bb`) and the refusal is recorded; and every other gate condition held on that head (`verify` green 33135, CI green, `review-gate` true).

## 6. Operator questions

1. "The build gate cannot reach green: /tmp has 0 free inodes …" — options {Reclaim /tmp then retry verify | Retry now anyway | Stop as blocked} → **selected "Reclaim /tmp, then I retry verify"**.
2. "/tmp still reports only ~4550 free inodes …" — options {It is reclaimed now — retry verify | Retry anyway with what is free | Stop as blocked} → **selected "Retry anyway with what is free"**.
3. "The retry failed the same way: 32813 passed, 169 failed, all ENOSPC …" — options {Open the PR now; CI is the green evidence | Wait for a real reclaim, then retry | Stop as blocked} → **free text: "FS is fixed now"** (no option selected; I retried `verify`, the step already authorised, and it went green).
4. "Self-review round 3 … five new low-severity items …" — options {Record them as residue, close the run | Fix O1/O2 in a follow-up PR | Stop; report budget-exhausted} → **selected "Record them as residue, close the run"**.

Free-text messages: "FS is fixed now" (item 3 above). No model or effort switch occurred.

## 7. Rule check

- **Guard: present** (opencode, R5 pre-tool-use). One refusal from this run: `2026-11-09T20:08:57.215Z | rule=R5 | session=ses_e4080d023ffe76RyaAQkwhwlsg | python3 .plan/execute-tool-tmp --pr-number 0` — an accidental malformed invocation (not a route around the executor); it was not retried and the intended call was issued through `ci pr prepare-comment` / `ci pr thread-reply`. That single line is the run's whole guard-log footprint for its session tree; the counts below come from the run's own actions, not from the log.
- Shell file operations issued by the run: **none** (read-class included) — file reads/searches went through Glob/Grep/Read; `df -h` / `df -i` were the only non-git shell commands, used as environment diagnostics.
- Routed builds: **22**, all `mechanism=daemon_longpoll`, no fallback, no launch-fault retry, no killed job. Every build through the executor's build command with `--project-dir` on the worktree.
- Operator messages: 4 questions (all answered by a selected option except item 3, which was free text) — see § 6.
- **Executor skew:** `not_applicable` — a source checkout, where the executor maps this checkout's own scripts; recorded, not asked about.
- **Spec read:** `spec_source=ledger_worktree`; no `spec_differ` marker (the main checkout holds no second copy).
- Sub-agent use: three self-review dispatches (rounds 1–3), report-only; no self-review round was cut short by a restart.

## 8. Build server

Setup preflight: **ready** (registered, daemon `v1`). All 22 builds ran `daemon_longpoll`; none fell back, none was retried after a launch fault, none was killed. Most of the wall-clock cost was queue time behind other sessions' jobs (1015 s, 566 s, 981 s, 1114 s, 1251 s, 1436 s, 1526 s, 1980 s observed), not build duration. No `runtime_stamp_reason` was reported.

Environment note for the build gate: four `verify` attempts failed **only** on `/tmp` inode exhaustion (`OSError: [Errno 28]`, 0–4.5k free inodes of 1048576) in modules this plan does not touch (`tools-script-executor`, `manage-architecture`, `platform-runtime`, `runbook-lane`), with 32813–33108 tests passing; after the operator reclaimed the filesystem, `verify` was green on `5b12a384f` (33110), `e2b91a044` (33117) and `a97f662bb` (33135). One earlier `module-tests` run also hit a transient target-tree generation precondition (`target/claude` plugin.json missing at equality-check time, tree complete afterwards) that did not recur.

## 9. Residue

Recorded as open at the operator's choice (round-3 items, all outside the Done-whens; the PR is merged and the branch pruned):

- **O1 (low)** `_github_pr.py` OPEN-arm error message says "…and no PR head, yet an OPEN PR names it as its head" — self-contradictory; same defect class as N2, one-line reword.
- **O2 (low)** `_branch_tip_sha` docstring says the remote arms help after refs were deleted "locally and on the remote"; once the remote-tracking ref is pruned, the PR listing is what classifies (the next paragraph says so).
- **O3a–d (low, test strength)** no fixture supplies `isCrossRepository: false`; the timeout test pins the `TimeoutExpired` branch but not the 60 s bound; the laziness test does not assert the population is non-empty; the unreadable-remote test asserts only the absence of `branch_absent`.
- **O4 (low, PR body)** the merged PR body says the CI abstraction has no default-branch verb at all; `ci org list-repos` does report a per-repo `default_branch`. The design conclusion (no routed-checkout verb) holds.
- **O5 (informational)** in the `ls-remote` arm the tip may not exist as a local object, so `git branch -r --contains <sha>` would error rather than report `pushed_no_pr`; unreachable in the target state, and fail-closed.
- Sourcery remains quota-blocked until ~2026-11-12 (optional reviewer, no gate).
