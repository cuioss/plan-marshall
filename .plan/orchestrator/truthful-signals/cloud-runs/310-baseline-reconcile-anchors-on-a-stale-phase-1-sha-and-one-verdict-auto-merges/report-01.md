# Run report — 310-baseline-reconcile-anchors-on-a-stale-phase-1-sha (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/baseline-reconcile-anchors-stale-q9exzm` (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (first action, the working contract).
- `plan-marshall:ref-code-quality` (+ `standards/error-handling.md` — the fail-closed classifier discipline is load-bearing here).
- `pm-plugin-development:plugin-script-architecture`.

Read directly from the bundle tree by path (the `plan-marshall` plugin notation was not relied on). Domain skills for Python production code + tests and workflow docs were satisfied by reading the surface directly; no skill was un-loadable by both routes.

## Deliverables

The surface: `_cmd_baseline_reconcile.py` (the resolver, upstream/in-flight listings, focused-reconcile path), `git-workflow.py` (`cmd_branch_sync_state`), and the finalize/refine/git docs that consume them, plus tests.

- **D0 — GATE (enumerate consumers + side-effects; mutates nothing).** Done.
  - **READ sites of the anchor:** the anchor (`status.metadata.worktree_sha`) had exactly one git-SHA reader in this surface — `_resolve_baseline_sha` in `_cmd_baseline_reconcile.py`, whose value fed BOTH `_list_upstream_commits` (`{anchor}..origin/{base}`) and `_list_in_flight_files` (`{anchor}..HEAD`). The other `worktree_sha` matches in the tree (`manage-tasks` freshness, `manage-change-ledger`, `script-shared/worktree_sha.py`) are a **different** concept — a working-tree content-currency hash via `compute_worktree_sha`, not the init-time git SHA — and are not consumers of this anchor.
  - **MUTATE-on-verdict sites:** the focused-reconcile path ran a real `git merge origin/{base} --no-edit` on `classification == overlap_no_content_conflict` (moving the branch ref). That was the only ref-moving side effect. (`_maybe_auto_update_stale_base_branch` writes `references.json`, and `add_qgate_finding` writes the findings store — neither moves a branch ref; left unchanged.)
  - **Sibling-field coupling:** the plan flagged `worktree_sha` as a field a sibling plan found recording the wrong tree. The consumer **inherited** the coupling (it read the field directly). **D1 removes the read entirely**, so this consumer is now **independent** of the field — the cleanest resolution of "two plans reading one field." No re-grounding against the sibling plan is owed because there is no longer a value dependency.
  - **Historical blast radius:** how often the auto-merge fired on a stale verdict is **NOT KNOWABLE from this clone** — the run artifacts live under `.plan/`, which is git-ignored and absent here. Stated as the plan permits ("not knowable" is an acceptable answer). The defect was live for an unknown number of plans.

- **D1 — Anchor on `merge-base(HEAD, origin/{base})`, recomputed per call.** Done. `_resolve_baseline_sha` removed; `_resolve_merge_base` added and called on every invocation (no caching). Both the upstream and in-flight listings now anchor on the merge-base. No range is computed from a stored SHA. Skips fail-closed (`merge_base_unresolved`) when no common ancestor exists.

- **D2 — The probe is non-mutating on every path.** Done. The real-merge focused-reconcile block is removed; classification is fully determined by the non-mutating `git merge-tree` (write-tree) plus the file-set overlap. `auto_reconciled`/`merge_commit_sha`/`merge_failure_paths` are gone; `auto_reconcilable` (a capability signal, not a claim a merge happened) replaces `auto_reconciled`. **Dependency made explicit, not silently broken:** the `auto_reconcilable`/`overlap_no_content_conflict` consumers — `finalize-step-sync-baseline.md`, `branch-cleanup.md`, and phase-2-refine `refine-workflow-detail.md`/`SKILL.md` — now state that the reconcile is deferred to the rebase steps that already run (`worktree-rebase-to` at phase-6, `sync-with-main` at phase-5). Those finalize steps already performed their own rebase and never depended on the probe's merge.

- **D3 — Fail-loud guards.** Done. HEAD is captured (`_resolve_head`) before the probe and re-read after the classification/emission; a change returns `status: error, error: probe_mutated_head` with `head_before`/`head_after`, taking precedence over every other outcome. Verified to FIRE by a test that injects a mid-probe ref move.

- **D4 — Verdicts reconcilable; ambiguous verdict must not route to a destructive action.** Done, both halves.
  - Two calls in one run against one unchanged state now agree (per-call merge-base + no mutation) — pinned by D5(a)/(d).
  - `cmd_branch_sync_state` no longer collapses a missing tracking ref into `no_remote` → RE-FIRE (which resurrected a merged-and-deleted branch, since a `done` push record implies the branch was pushed, so an absent ref means it was deleted after merge). It disambiguates via ancestor-of-base containment (`remote_absent_landed`) and DECLINES on the indistinguishable case (`remote_absent_unverified` — never-pushed vs squash-merged-and-deleted). The finalize push-barrier consumer (`phase-6-finalize/SKILL.md`) now re-fires ONLY on `ahead`; both ref-absent verdicts SKIP/decline. Recovery-path design is deliberately out of scope (per the plan) — the verb declines rather than resurrecting.

- **D5 — Tests, each seen red pre-fix.** Done. See § Findings for the red-first evidence.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (three `.py` files: `_cmd_baseline_reconcile.py`, `git-workflow.py`, and two test modules), so the build gate took its **full path**.

- `./pw quality-gate` — clean: `issues[0]`, coverage COMPLETE (mypy production [396 files], ruff, SPDX headers, plugin-doctor marketplace-wide — the doc/SKILL.md structural lint passed).
- `./pw module-tests` (whole tree) — **19463 passed, 14 skipped, 0 failed** (510s). Includes `test_real_marketplace_quality_gate_has_zero_findings`, confirming the doc edits are structurally clean.

## Findings

**Red-first evidence (D5 + the behaviour-changing test updates).** With the two SOURCE files stashed to their pre-fix state and the new/updated tests run against them, **11 tests failed** (the exact deliverable tests) while 110 unchanged tests stayed green:

- D5(a)+(d) `test_two_calls_after_reconcile_agree_zero_upstream_no_overlap` — pre-fix the 2nd call reported 1 upstream + `overlap_no_content_conflict`, contradicting the 1st call's `no_overlap` on a 0-behind branch.
- D5(b) `test_in_flight_set_excludes_files_the_plan_never_touched` — pre-fix folded the merged-in upstream file into the in-flight set.
- D5(c) `test_merge_base_recomputed_not_read_from_stored_status` — pre-fix read the poisoned stored SHA and reported 0 upstream.
- D5(e) `test_classify_only_never_moves_head_on_every_classification` — pre-fix moved HEAD on `overlap_no_content_conflict`.
- D3 `test_d3_guard_fires_when_probe_moves_head` — pre-fix had no guard.
- `test_classification_overlap_no_content_conflict_is_non_mutating` (rewrite), the two `auto_reconcilable` field-rename updates, and the three branch-sync-state D4 tests (`remote_absent_unverified`, `remote_absent_landed`, and the barrier-mapping rewrite) all failed pre-fix.

After restoring the fix, all 121 scoped tests pass (one intermediate tmp_path-collision fix in the barrier-mapping test), and the whole-tree suite is green.

**Verification sub-agent (independent, read-only) — 1 finding, fixed.**

- **Real finding — `git-workflow.py` CLI `--help` still advertised the removed `no_remote` state** (the module docstring and SKILL.md were updated, but the second copy in the live argparse `help=` registration was missed). Same truthful-signals defect class the plan fixes. **Fixed** in commit `51e4c55` (help now lists `remote_absent_landed`/`remote_absent_unverified`); self-verified by grep (no `no_remote` state token survives anywhere in the bundle except the unrelated legitimate probe skip-reason `_cmd_baseline_reconcile.py:386`) and a re-run of the marketplace-wide `quality-gate`. A full re-dispatch was judged disproportionate for a mechanical doc-string fix already fully characterised by the agent and identical in form to the already-verified docstring/SKILL edits.
- **Consistency nit (not a defect) — `finalize-step-sync-baseline.md`** omitted the "`auto_reconcilable` is always true for `overlap_no_content_conflict`" note that `branch-cleanup.md` carries. **Fixed** in `51e4c55` for parity (the rule already yielded correct results).
- **Everything else verified clean by the agent**, each with evidence: all six deliverables satisfied from code+tests; `auto_reconciled`/`merge_failure_paths`/`baseline_drift_reconcile_failed` are zero-occurrence in the bundle; the surviving `merge_commit_sha` hits are the legitimate `references.merge_commit_sha` landing field; no stale "focused reconcile"/"performs a merge"/"init-time SHA anchor" prose survives. The only item not verifiable from the diff alone was D0's run-report enumeration — its code-state evidence is confirmed clean, and the enumeration itself is § Deliverables D0 above in this committed report.

**CI + PR review.** No actionable review comment was produced on any of the three surfaces (issue comments, review summaries, inline threads) — both external review bots returned quota refusals rather than findings, and the repo's own `review / review` workflow concluded green with no comments. So there was **nothing to fix or reply to**; the independent pre-PR verification (above) is the substantive code review for this change, and its one finding was fixed.

CI check-runs on head `51e4c55`: `verify / gate` success, `review / review` success, `dependency-review` success, `generate-check` success, `Sourcery review` skipped, `auto-merge` skipped; `verify / verify` was the required build check. See § Contract check for its terminal state at hand-off.

## Reviewer participation

Population derived from configuration — the `author_login` of each `automatic-review/standards/{bot_kind}.md` registry doc (`coderabbit.md`, `sourcery.md`, `pr-agent.md`); not transcribed.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Issue-comment body "PR Reviewer Guide 🔍" on head `51e4c55`: "PR contains tests", "No security concerns identified", "No major issues detected" — an explicit clean review over the diff. No findings, nothing to action. |
| `coderabbitai` | `rate-limited` | Issue comment: "Review limit reached … you've reached your PR review limit … Next review available in: 105 minutes." Engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Review-summary body: "you have reached your weekly rate limit of 500000 diff characters." Engaged but did not review this diff. |

**Coverage: 1 of 3** registry reviewers produced a review body — the repo's own `cuioss-review-bot` reviewed clean; `coderabbitai` and `sourcery-ai` are both rate-limited. The § Step 8 shortfall disclosure **fired** (see below). This is disclosed, not blocked — rate limits are routine and outside our control. Substantive review was additionally performed by the independent pre-PR verification sub-agent (which found and drove the fix of one real defect); it is not a registry reviewer, so it does not count toward the N-of-M.

## Cost

- **Tokens:** not available to the agent in this session (the harness does not expose a per-session token count here).
- **Wall-clock:** dominated by two `./pw` invocations (quality-gate + whole-tree module-tests ≈ 8.5 min) plus scoped red/green pytest runs.
- **Population:** this single Claude Code cloud session's usage. **Not comparable** to a plan-marshall `metrics.toon` total (that counts an orchestrator-plus-agent dispatch tree under a per-task billing boundary this interactive session does not share).

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named in § Skills loaded (read by bundle path; plugin notation not relied on). |
| 2 Branch | Done — harness-assigned `claude/baseline-reconcile-anchors-stale-q9exzm` kept as-is (recorded as **harness-assigned**), pushed to origin before any work. |
| 3 Plan directory | Done — `…/310-…/plan.md` exists via `git mv`; it opens with the first-instruction block (verified before the move). |
| 4 Implement | Done — commits carry the `Co-Authored-By: Claude` trailer; deliverables D0–D5 addressed. |
| 4 Per-commit gate | Done — every `*.py`-touching commit was preceded by a clean `./pw quality-gate` (`issues[0]`, coverage COMPLETE). |
| 4 Pushed | Done — no unpushed commit remains. |
| 5 Build gate | Done — Python-change verdict positive; full path taken; `quality-gate` clean + whole-tree `module-tests` 19463 passed / 0 failed. |
| 6 Verification sub-agent | Done — one finding, fixed (`git-workflow.py` CLI help); dispositions in § Findings. |
| 7 PR cycle | Done — PR #1206; all three comment surfaces read; no actionable comment (2 rate-limit notices + 1 clean review guide). |
| 8 Merge gate | Conditions 2 (comments handled), 3 (this report is the last pre-merge commit), and 4 (shortfall disclosed) **met**. Condition 1 (required `verify / verify`) was **in_progress** when this report was committed. Auto-merge (SQUASH) is armed the moment `verify` concludes green; the repo's **merge queue is the final enforcer** of the required-green gate, so arming defers required-ness to the queue. See § Residue / the closing status for the arm outcome and the landing. GitHub access path: **GitHub MCP server**. Branch form: **harness-assigned**. |
| 8 Bridge | Done — no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | Done — this table. |
| 9 What have we learned | Below — a contract-change proposal, presented to the operator, not self-applied. |

A cloud run **never owes** a `/sync-plugin-cache` (machine-local build step) — none performed or recorded.

## What have we learned (Step 9)

**Proposal (evidence from THIS run) — the lane's post-PR self-wake affordances were not merely approval-gated here; they were absent.** Both `subscribe_pr_activity` and `send_later` returned **"No such tool available"** in this cloud session — the `claude-code-remote` MCP server was not connected at all. The § "Cloud session affordances" table describes these as tools that "may be **approval-gated**", and the "Manual read-polling" paragraph assumes the session "stays active" or is "re-entered by any means". Neither held: there was no wakeup mechanism, and a turn cannot wait out an ~8-minute `verify` build (foreground `sleep` is blocked; Bash cannot poll GitHub). The consequence: when the agent reaches the merge gate with the required check still `in_progress`, it can neither block-until-green nor schedule a re-check — so a fully-ready PR can stall at the gate.

Proposed contract clarification (to present, not self-apply): the lane should name the **"no self-wake at all"** case distinctly from "approval-gated", and state the intended completion for it — either (a) arm auto-merge with the required check still `in_progress`, explicitly relying on the merge queue to enforce the required-green gate before the actual merge (the queue already does this), recorded as arm-and-hand-off; or (b) end at "PR open, required check pending, landing delegated to the orchestrator's collect", recorded as a **complete** outcome rather than partial. Today the letter of condition 1 ("BLOCKED → wait") and the arm-and-hand-off text ("armed a **green** PR") together leave this exact situation without a sanctioned terminal action. **Operator decision recorded in the closing status.**

## Residue

- **The arm-once-green step is the only remaining action.** Everything else is complete and pushed. `verify / verify` is expected green (the identical whole-tree suite passed locally, 19463/0). The closing status records whether this session armed auto-merge (verify concluded green in-session) or handed the arm/landing off.
- No code, test, or doc residue — all deliverables landed in commits on this branch.
