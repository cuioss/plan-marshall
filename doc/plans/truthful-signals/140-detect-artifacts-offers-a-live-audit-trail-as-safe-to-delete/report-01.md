# Run report — 140-detect-artifacts-offers-a-live-audit-trail-as-safe-to-delete (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/artifact-deletion-audit-trail-m4y1oz` (harness-assigned; kept as-is)    **PR:** [#1171](https://github.com/cuioss/plan-marshall/pull/1171)    **Outcome:** completed

## Skills loaded

Loaded by reading bundle-source paths (the `plan-marshall` plugin was not relied on):

- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `plan-marshall:persona-implementer` (production code — work identity)
- `pm-dev-python:pytest-testing` (Python tests)
- `cloud-plan-lane` (the governing contract, loaded first)

Conditional skills not loaded because unused: `pm-dev-python:python-core` standards (the change uses only `os`/`subprocess`, already imported; conventions were matched against the existing file), `pm-plugin-development:plugin-architecture` (no SKILL frontmatter/structure change — only prose in an existing SKILL.md), `pm-documents:ref-asciidoc` (no `.adoc` change), `plan-marshall:persona-security-expert` (not a security-domain change).

## The defect, re-established at HEAD (D1 — GATE)

D1 mutated nothing. It re-established the lead from source and derived the real exposure by running the **actual** `scan_artifacts`/`get_gitignored_files` from `git-workflow.py` against controlled temp git trees (diagnostics in scratch, not committed).

**Contract text (quoted from source).** The exclusion contract is stated in three places:
- `SKILL.md` (Step 3 "Clean Artifacts"): *"The script respects `.gitignore` by default — gitignored files are excluded since they cannot be accidentally committed."*
- `SKILL.md` (`detect-artifacts` reference): *"Files already covered by `.gitignore` are excluded by default since they cannot be accidentally committed."*
- `scan_artifacts` docstring: *"Files already covered by .gitignore are excluded by default…"*

So the HYPOTHESIS "documented as excluding gitignored files" is **CONFIRMED**.

**Classification behaviour (read by symbol, then reproduced).** `scan_artifacts` (git-workflow.py) builds `ignored = get_gitignored_files(root)` and, per walked file, does an **exact-string** membership test `if rel in ignored: continue`. `get_gitignored_files` returns the output of `git ls-files --others --ignored --exclude-standard`.

Empirical derivation (method stated):
- **Plain gitignored files and plain gitignored directories are enumerated individually** by `git ls-files` (git 2.43.0) and are correctly excluded — the exact-match honours them. So the naive "ignores gitignore entirely" reading is **false**, and a lesser plan would have wrongly refuted here.
- **A nested git worktree collapses.** `git ls-files --others --ignored --exclude-standard` run from an outer repo returns a **single trailing-slash entry** `.plan/local/worktrees/EXAMPLE-PLAN/` for a linked worktree — it does not enumerate the worktree's contents (git never descends across a repo boundary). `os.walk` **does** descend. The exact-match test then compares `'.plan/local/worktrees/EXAMPLE-PLAN/logs/work.log'` against `{'.plan/local/worktrees/EXAMPLE-PLAN/'}`, fails, and the file is classified **safe**.

**Exposure derived (not the inherited 111,433 figure).** Any file under a running plan's worktree at `.plan/local/worktrees/{plan}/**` that matches a safe/uncertain pattern is offered — the plan's own in-flight `logs/work.log` (its live audit trail; confirmed to be the semantic work log at `.plan/local/plans/{id}/logs/work.log` / worktree-relative `logs/`, "decisions, artifacts, progress"), plus `.mypy_cache/**`, `__pycache__/**`, `*.pyc`, etc. A built worktree is the 19.9 MB / 111k-entry blast radius: a full checkout's caches. Secondary exposure: when the scan root is **not** a git repo, `get_gitignored_files` returns an empty set and nothing is excluded at all.

**STOP CONDITION not triggered** — the contract *is* stated and the classification does *not* honour it (the worktree/collapsed-directory case leaks). The defect is confirmed, not refuted, so the plan proceeded.

## Direction chosen (D2)

**(a) Honour the documented contract — genuinely exclude gitignored paths.** Rationale: the docs already promise exclusion; the gap was an exact-match test that ignored git's collapsed *directory* entries. Making the match prefix-aware (exclude every path beneath a git-reported ignored directory) makes the implementation actually match the documented contract, without narrowing the docs to a data-loss path — the explicitly-rejected (b)-without-liveness outcome is avoided entirely. The documentation was additionally clarified (not narrowed) to state the nested-repo/worktree behaviour so contract and implementation agree in both directions (the plan's Goal).

## Deliverables

| Deliverable | Done | Where |
|---|---|---|
| **D1** — re-establish defect at HEAD, derive exposure | ✅ | This report § "The defect". Contract quoted; behaviour reproduced with the real functions; exposure derived with method stated. |
| **D2** — decide direction + record why | ✅ | Direction (a), rationale above. Commit `ee780ed`. |
| **D3** — a running plan's own artifacts never offered (independent of gitignore) | ✅ | `scan_artifacts` now prunes nested git repositories/worktrees during traversal (`_is_nested_git_boundary`). A running plan runs in a linked worktree under `.plan/local/worktrees/{plan}/`; its checkout is never traversed, so its live artifacts are never offered — and this holds with `respect_gitignore=False` (pinned by `test_worklog_excluded_independent_of_gitignore`). Liveness signal used: the **structural nested-repo boundary** (`.git` present), a reliable superset of "a currently-running plan's own checkout"; a lock/status-based signal was considered and rejected as more fragile and unreachable from `scan_artifacts` (which takes no plan-id). |
| **D4** — find the callers; latent vs active | ✅ | Derived below. **Latent.** |
| **D5** — three tests, each verified red pre-fix | ✅ | § Findings / § Build gate. All three seen red first. |

**Commits:**
- `104b984` — chore: establish plan directory (git mv → `plan.md`).
- `ee780ed` — fix: the implementation + tests + SKILL.md doc alignment.

## D4 — caller set (derived, not sampled)

**Query:** ripgrep `detect-artifacts|detect_artifacts|scan_artifacts` across the tracked source tree (the complete caller population; `.plan/` is git-ignored runtime state, not a source caller). **Six hits:**

1. `git-workflow.py` — the implementation itself.
2. `test_git_workflow.py` — tests.
3. `test/conftest.py` — a docstring example of the `/nonexistent` sentinel (`cmd_detect_artifacts(root='/nonexistent/path')`).
4. `workflow-integration-git/SKILL.md` — Step 3 "Clean Artifacts", the **only** behavioural consumer: *"For safe artifacts, delete them."*
5. `persona-plan-marshall-agent/standards/argument-naming.md` — a canonical-forms documentation table.
6. The plan file itself.

**Verdict: the defect is LATENT, not active.** No script, hook, or finalize step pipes the `safe` list into an unattended deletion — the only consumer is the agent-followed commit workflow. It is still a real hazard: an agent following the documented "for safe artifacts, delete them" instruction deletes whatever `safe` contains, which pre-fix included a running plan's worktree logs. Latency lowers the severity from "already firing" to "one careless clean-artifacts step away", which is why the fix is a correctness fix rather than an incident response.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` verdict: **Python changed** (`git-workflow.py`, `test_git_workflow.py`) → build gate takes its full path.

`./pw verify plan-marshall` (scoped — the entire diff lives in the `plan-marshall` bundle and its test dir): **`15982 passed, 1 skipped`**, quality-gate "All checks passed!", SPDX-header check passed. No `errors[]`. The single skip is a pre-existing environment-guarded test, not introduced by this change (the strict-no-skip gate is CI-opt-in; a local scoped run does not set it).

## Findings

Every finding with source and disposition. A finding is recorded per instance.

**Verification sub-agent (pre-PR):** dispatched (independent `general-purpose`, read-only). Verdict: **all D1–D5 deliverables PASS, no code defects.** It independently re-derived the git-collapse mechanism (its own `git ls-files` experiments on git 2.43.0), re-derived the D4 caller set, and reasoned each D5 test's pre-fix path. Three findings, each dispositioned:

| # | Finding | Severity | Disposition |
|---|---|---|---|
| F1 | The new SKILL.md prose ("a running plan's own worktree is *never scanned*", attributing `work.log` protection to boundary-pruning) overstates: in the documented finalize path the plan's worktree can *be* the scan root and *is* scanned, with `work.log` protected there by `.gitignore`, not by boundary-pruning. Boundary-pruning applies only to a worktree *nested below* the scan root. | low–moderate (doc precision) | **FIXED** (commit `f09eb37`). Reworded both SKILL.md spots and the `scan_artifacts` docstring to scope the skip to *nested* worktrees below the scan root and to attribute both mechanisms correctly (gitignore when the worktree is the scan root; pruning when nested). Re-verified by the sub-agent. This is precisely the misleading-signal class this epic targets, so it was fixed, not waived. |
| F2 | `_is_nested_git_boundary` treats any directory containing a `.git` entry — including a pathological stray file literally named `.git` — as a boundary to skip. | nit | **REJECTED (with reason).** The stray-`.git`-file case is pathological and this is exactly how git itself special-cases `.git`; adding heuristics to distinguish a real gitlink from a stray file would add complexity and its own failure modes for a case that does not occur in practice. Consistent-with-git behaviour is the right default. |
| F3 | `standards/artifact-patterns.json` `_note` describes `skip_dirs` as the traversal-skip and does not mention the new nested-boundary skip ("incomplete, not false"). | low (doc completeness) | **REJECTED (with reason).** The `_note` documents the JSON's *config fields* (what `skip_dirs`/`safe_patterns`/`uncertain_patterns` mean), not the full traversal algorithm. The nested-repo skip is a code behaviour whose contract now lives in the `scan_artifacts` docstring and SKILL.md, where behavioural contracts belong. Coupling the config-schema note to traversal internals would invite the same drift this epic warns against. |

**D5 tests — each seen RED first (pre-fix), then GREEN post-fix:**

| Test | Pre-fix result | Evidence |
|---|---|---|
| `test_live_plan_worklog_never_offered_as_safe` (D5b) | RED | `safe` contained `.plan/local/worktrees/EXAMPLE-PLAN/logs/work.log` — the running plan's own audit log offered for deletion. |
| `test_gitignored_worktree_contents_excluded_per_contract` (D5a) | RED | `.mypy_cache/...` and `module/__pycache__/foo.pyc` (gitignored, under the worktree) offered. |
| `test_exposure_derivation_nonempty_and_excludes_live_member` (D5c) | RED | Positive-population + negative in one test: pre-fix the negative (`work.log` absent from safe) failed while the control `scratch.temp` was correctly safe — proving the scan examined a populated tree, so the negative is non-vacuous. |
| `test_worklog_excluded_independent_of_gitignore` (D3 independence) | RED | With `respect_gitignore=False`, `nested-wt/logs/work.log` was offered — proving the leak is not merely a gitignore artefact. |
| `TestIgnoreExclusionHelpers::*` (6 unit tests) | RED (AttributeError) | Helpers did not exist pre-fix; they pin the prefix-aware exclusion and boundary detection deterministically. |

Post-fix: the 10 new tests pass; the full `test_git_workflow.py` (95 tests) passes with no regression.

## Reviewer participation

Expected reviewer population, derived from `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` `author_login` values (cross-named by `.github/workflows/pr-agent.yml`):

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Published a "PR Reviewer Guide" review artifact against the diff: *"PR contains tests / No security concerns identified / No major issues detected"* — an explicit nothing-to-report over this diff. |
| `coderabbitai` | `rate-limited` | Published **only** a refusal notice: *"Review limit reached … you've reached your PR review limit, so we couldn't start this review. Next review available in: 59 minutes."* It engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Published **only** a refusal notice (review body, COMMENTED state): *"you have reached your weekly rate limit of 500000 diff characters."* Its `Sourcery review` check concluded `skipped`. |

**Coverage: 1 of 3.** Inline review-thread surface: **0 threads** (read explicitly — not inferred from the conversation view). Both comment surfaces read; no actionable comment on either (the two rate-limit notices need no reply; the one review reported nothing to action), so condition 2 (every comment handled) holds against a genuinely empty actionable set.

**§ Step 8 condition-4 shortfall disclosure (fired):** "Review coverage: 1 of 3 — `cuioss-review-bot` reviewed with no findings; `coderabbitai` rate-limited (window reopens in ~59 min); `sourcery-ai` rate-limited (weekly 500k-diff-char quota)." Per the contract this is a **disclosure, not a block** — rate limits are routine and outside our control, and the merge is gated only on conditions 1–3. The independent pre-PR verification sub-agent (§ Findings) provided the substantive review coverage this diff received.

## Cost

- **Tokens:** not available to the agent in this session (a single interactive Claude Code cloud session; the harness does not surface a per-run token count here).
- **Wall-clock:** run started ~the time this session opened; the dominant cost was one `./pw verify plan-marshall` (~6m39s build + suite).
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary — a boundary a single interactive cloud session does not share. No comparable number is presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | ✅ Named in § Skills loaded (read by bundle path; `plan-marshall` plugin not relied on). |
| 2 Branch on `origin` | ✅ `claude/artifact-deletion-audit-trail-m4y1oz` (harness-assigned, kept as-is) — pushed to `origin` before any edit (it was absent from the remote at start; `git ls-remote` verified, then pushed). |
| 3 Plan directory | ✅ `doc/plans/truthful-signals/140-…/plan.md` exists and opens with the first-instruction block (present in the handed file — no repair needed). |
| 4 Implement | ✅ Deliverables addressed; every commit carries the `Co-Authored-By: Claude` trailer and no "Generated with Claude Code" footer. |
| 4 Per-commit gate | ✅ Each `*.py`-touching commit was preceded by a clean gate: fix commit `ee780ed` by `./pw verify plan-marshall` (15982 passed, quality-gate "All checks passed!"); F1 commit `f09eb37` by `./pw quality-gate plan-marshall` (mypy "no issues found in 274 files", ruff "All checks passed!", SPDX passed). |
| 4 Pushed | ✅ No unpushed commit remained at each stage; branch pushed after every commit. |
| 5 Build gate | ✅ Python changed → full path taken; `./pw verify plan-marshall` clean. |
| 6 Verification sub-agent | ✅ Dispatched, findings + dispositions in § Findings; F1 fixed and re-verified. |
| 7 PR cycle | ✅ PR [#1171](https://github.com/cuioss/plan-marshall/pull/1171); both comment surfaces read; every comment dispositioned (no actionable items). |
| 8 Merge gate | Conditions 2 (comments handled) and 3 (report finalized) met at report-commit time; condition 1 (required `verify` check) confirmed green on the final head immediately before arming; auto-merge then armed. Condition-4 shortfall (1-of-3 coverage) disclosed. The merge commit is recorded to the operator, not embedded here. |
| 8 Bridge | ✅ No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome for the collect step. |
| 9 This check | ✅ This table. |
| 9 What have we learned | ✅ Below — one proposal, presented to the operator. |

**GitHub access path used:** the GitHub MCP server (the cloud path). **Branch form:** harness-assigned `claude/*`, kept as-is. **`/sync-plugin-cache`:** not owed — a cloud run never performs or owes it (machine-local build step).

## What have we learned (Step 9)

**Proposed contract change (presented to the operator; NOT self-approved, NOT shipped in this PR).**

**Evidence from this run.** The lane's build-gate wording (§ Step 4 per-commit gate and § Step 5) instructs: *"Open the `log_file` it names and confirm `total_issues: 0` and an empty `errors[]`."* That `log_file` / `total_issues` / `errors[]` vocabulary is the **plan-marshall executor's TOON output contract** (`CLAUDE.md` § Build Commands: "read the result TOON `status`/`errors[]`"). But the lane supersedes the executor and runs `./pw` **directly**, and `./pw quality-gate` / `./pw verify` do **not** emit a named `log_file` or a `total_issues`/`errors[]` structure — they stream raw tool output ending in `ruff … All checks passed!`, `mypy … Success: no issues found in N source files`, `SPDX-header check passed`, and a pytest `N passed, M skipped` summary. A run following the instruction literally would look for a `log_file` and fields that the direct-`./pw` path never produces. I confirmed cleanliness from the actual lines instead, which is the lane-appropriate signal — but the contract's wording does not match what its own prescribed command emits.

**Concrete proposed edit.** In `cloud-plan-lane/SKILL.md` § Step 4 ("Gate before committing") and § Step 5 ("Read the output, not the exit code"), replace the executor-flavoured *"open the `log_file` it names and confirm `total_issues: 0` and an empty `errors[]`"* with direct-`./pw` guidance: confirm the quality-gate lines report all checks passed (`ruff … All checks passed!`, `mypy … no issues found`, `SPDX-header check passed`) **and** the pytest summary reports `0 failed` / `0 errors`, reading the output rather than the exit code (the "wrapper can exit 0 on failure" caution stays). Keep the executor-path phrasing only where the generated executor is actually available.

**Status:** presented to the operator in the run's closing message; pending approval. On approval it ships as its own `chore(cloud-plan-lane):` PR (a skill change, reviewed as code — no `skip-bot-review`), not folded into this plan's PR.

No other contract change is proposed: every other step's artifact was produced as written, and the run exercised the branch/PR/merge/report flow without further friction.

## Residue

- **Non-git-root secondary exposure:** when `detect-artifacts` is run with a `--root` that is not inside a git repository, `get_gitignored_files` returns an empty set and no gitignore exclusion occurs. This is out of scope for this plan (a *running plan* is always inside a git repo) and is left as a documented best-effort limitation (`get_gitignored_files` already degrades to an empty set on non-repo/`git`-unavailable). Not fixed here.
- **Worktree teardown timeout** (plan's out-of-scope item): D1's derived surface did not reach the `worktree-remove` timeout mechanism, so it was correctly left out.
- **Plugin cache sync:** a cloud run neither performs nor owes `/sync-plugin-cache` (machine-local build step).
