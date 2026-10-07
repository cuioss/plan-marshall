# Run report — 290-config-hash-cannot-fail-usefully (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/main-sha-worktree-config-hash-mrscwi` (harness-assigned, kept as-is)    **PR:** [#1205](https://github.com/cuioss/plan-marshall/pull/1205)    **Outcome:** completed (auto-merge armed SQUASH; landing delegated to the merge queue)

Scope note: this plan is narrowed to the **`config_hash` half**. The `main_sha` half is
owned in full by `doc/plans/code-intelligence-substrate/310-main-sha-records-the-pinned-cwd.md`
and is explicitly out of scope — no `main_sha`, resolver, or population-sweep work was done here.

## Skills loaded

- `plan-marshall:ref-code-quality` (always) — read via bundle path.
- `pm-plugin-development:plugin-script-architecture` (always) — read via bundle path.
- `plan-marshall:persona-implementer` (production code work identity) — read via bundle path.
- `pm-dev-python:python-core` (Python production code) — read via bundle path.
- `pm-dev-python:pytest-testing` (Python tests) — read via bundle path.

All obtained by reading the bundle `SKILL.md` path (the `plan-marshall` plugin route was not
attempted; the bundle-path route always works in a fresh clone). No skill was unobtainable.

## Deliverables

### D0 — GATE: confirm the config-hash capture by symbol, and derive its inputs

`_capture_config_hash` (`marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:1311`).

**Inputs consumed:** `plan_id`, `phase` (only to build the config key `phase-{phase}`), and the
stdout of the subprocess
`manage-config plan phase-{phase} get --audit-plan-id {plan_id}` (run via `_run_script`).

**Classification — the config *value* is not cwd-derived, but the config *file* is located by a
cwd-relative resolver.** The pre-fix capture addressed the config by the phase key and `plan_id`
(reaching `_repo_root()` only transitively, to set the subprocess cwd). The shipped capture reads
`marshal.json` via `get_marshal_path()` → `get_tracked_config_dir()` → `_find_plan_root_from_cwd()`,
which is **cwd-relative** — the *same class* of resolution the sibling defect turns on (in a worktree
it would read `<worktree>/.plan/marshal.json`, not main's). The reason the captured value is
checkout-stable in practice is **not** that it resolves against an explicit handle — it is that
`marshal.json` is git-tracked and typically unchanged on-branch, so its content is identical across
checkouts. The plan's own evidence confirms this for the observed incident: the 4/4 drift was "over a
footprint with **no config file at all**", so `marshal.json` was identical across all four boundaries
and the drift came purely from the per-phase key, not from worktree-vs-main resolution.
*(This corrects the run's initial "resolves against an explicit handle" wording, which described the
pre-fix subprocess path — flagged as finding D0-1 by the verification sub-agent.)*

**Hand-off condition: NOT triggered.** Fixing `config_hash` does **not** touch, modify, or depend on
*fixing* the worktree-vs-main root resolver that the sibling plan (310) owns — the fix removes the
per-phase key and leaves every resolver (`_repo_root`, `get_base_dir`, `get_tracked_config_dir`,
`_find_plan_root_from_cwd`) untouched. The in-scope defect (phase-key → 4/4 spurious drift) is
resolver-independent, so there is no "fix the resolver twice" collision. The residual checkout-context
stability of `marshal.json` remains the sibling plan's concern (see Residue). Proceeding here.

**Two compounding defects found (both empirically confirmed):**

1. **The capture is dead in current code.** The `plan` noun's `get` verb does **not** accept
   `--audit-plan-id` (that flag exists only on the `build-decision` / `build-map` nouns). Running
   `manage-config plan phase-5-execute get --audit-plan-id X` exits **code 2** ("unrecognized
   arguments"), so `_run_script` returns `None` and `_capture_config_hash` returns `None` at every
   boundary — the signal is permanently absent (this epic's exact archetype). Empirically verified by
   invoking the real script with the marketplace PYTHONPATH.
2. **The value is phase-scoped but compared cross-phase.** `_capture_config_hash` hashes the config
   for key `phase-{phase}` — a *different key at every phase*. The retrospective summarizer's
   `detect_drift` (`summarize-invariants.py:267`) compares each invariant's value **between
   consecutive phases**, and `config_hash` is **not** in its `excluded` set. So comparing phase-1's
   hash to phase-2's hash compares different config subtrees → it "drifts" at every boundary **by
   construction**, carrying zero information. This is the "fires at 4/4 and cannot fail usefully"
   the plan observed.

### D1 — Determination (recorded either way, per the plan)

**The four observed drifts were NOT real configuration changes.** They are an artifact of feeding a
**phase-scoped** hash into a **cross-phase** drift detector. Corroboration from the code itself: the
blocking-classification comment at `_invariants.py:1502-1507` already declares `config_hash`
describes "plan-internal state that **should remain stable across every boundary**." The phase-scoped
implementation violated its own stated intent.

**Fix (make it context-independent, per the plan's preferred "fixed so it can discriminate"
outcome):** `_capture_config_hash` now hashes the **phase-independent** `plan` section of
`marshal.json` (read directly, in-process). The same configuration therefore hashes to the same value
at every boundary, so:

- the cross-phase `detect_drift` scan reports a drift **only** when the config genuinely changed;
- the same-phase `cmd_verify` re-verify still blocks on a real mid-phase change
  (`blocking_at_every_boundary` classification retained);
- the `--audit-plan-id` breakage is removed entirely (no subprocess involved).

The field keeps its name `config_hash` (now accurate: a fingerprint of the plan's configuration —
no rename, no `handshakes.toon` schema churn). Suppression was never on the table (out of scope).

### D2 — Tests, each verified to FAIL pre-fix

All in `test/plan-marshall/plan-marshall/test_invariants_behavior.py` unless noted. Each of the two
required controls was run RED against the current implementation, then GREEN after the fix (the full
config_hash block was seen `5 failed` pre-fix, `5 passed` post-fix — the failing assertions are
quoted below):

- **(a) context-stability** — `test_capture_config_hash_stable_across_phases`: the same config hashed
  at `1-init` and `5-execute` must be equal. Pre-fix RED on `assert at_init == at_execute`
  (`'ca1f86cbb4eff823' == 'cf7a8a48e0e8766a'` — the old phase-scoped hashes differ per phase);
  post-fix GREEN.
- **(b) genuine-change-still-drifts (the control against silencing)** —
  `test_capture_config_hash_drifts_on_genuine_config_change`: a genuine `marshal.json` change must
  change the hash. Pre-fix RED on `assert before != after`
  (`'34852a9e3c835d7e' != '34852a9e3c835d7e'` — the old subprocess capture ignored the marshal
  change); post-fix GREEN. The sub-agent independently re-ran both reds against `origin/main` and
  confirmed they fail for the right reasons (non-vacuous).
- Supporting contract tests rewritten for the new read: `..._none_when_marshal_absent`,
  `..._none_when_marshal_unreadable` (fail-closed), `..._hashes_plan_section`.
- **Supplementary regression lock (added after sub-agent review, not a red-then-green test):**
  `test/plan-marshall/plan-retrospective/test_summarize_invariants_behavior.py::TestDetectDrift::test_config_hash_change_is_drift`
  asserts a changed `config_hash` across phases surfaces a drift entry — locking `config_hash` out of
  `detect_drift`'s `excluded` set so the phase-independence fix cannot later degrade into silencing
  the cross-phase signal. (The same-phase blocking path is already guarded by the pre-existing
  `test_verify_drift_config_hash`.)

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **`_invariants.py` and two test files changed
→ Python change → full path taken.** `./pw verify` reported **`=== verify: SUCCESS ===`**:
`19458 passed, 14 skipped`, coverage `COMPLETE` over mypy(production, 396 files), ruff, SPDX headers,
plugin-doctor (marketplace-wide), mypy(test, 724 files), and whole-tree module-tests. The per-commit
`./pw quality-gate` also reported `total_issues: 0`. The 14 skips are environment guards (the
reference-platform strict-no-skip gate is opt-in and not set in this session).

## Findings

| Source | Description | Disposition |
|---|---|---|
| Verification sub-agent — D0-1 | Report's initial D0 classification ("resolves against an explicit handle") described the pre-fix subprocess path; the shipped capture reads `marshal.json` via a cwd-relative resolver. | **Fixed** — D0 classification above rewritten to be accurate; hand-off conclusion unchanged (still not triggered). |
| Verification sub-agent — D2-1 | `test_invariants_behavior.py:17` module-docstring bullet still described the deleted subprocess branches (unreachable/parseable/unparseable). | **Fixed** — bullet rewritten to the new absent/unreadable/non-dict/plan-section branches. |
| Verification sub-agent — D2b proxy note | D2(b) asserted only at the capture level; a future addition of `config_hash` to `detect_drift`'s `excluded` set would silence the cross-phase signal while D2(b) still passed. | **Fixed** — added the detector-level regression lock `test_config_hash_change_is_drift` (above). |
| Verification sub-agent — R-1 | Report's D2 and Build-gate sections were unpopulated placeholders. | **Fixed** — both sections populated (above). |
| Verification sub-agent — verdict | Change substantively meets all three deliverables; no undeclared collateral; D0 hand-off conclusion correct; no other stale `config_hash` prose in the tree. | Accepted — no code change required. |
| CI — `verify / conclusion` (required) | Concluded `success` on head `b89fb37`; the full check set (`verify / verify`, `verify / gate`, `dependency-review`, `review / review`, `generate-check`) is green, `mergeable_state: clean`. | No action — required check green. |
| PR review — `cuioss-review-bot` | Clean `## PR Reviewer Guide 🔍`: no security concerns, no major issues, PR contains tests. No finding to action. | No action — clean review. |
| PR review — `coderabbitai` | Refusal notice ("Review limit reached") in place of a review; no finding carried. | No action — refusal, not a finding (§ Reviewer participation). |
| PR review — `sourcery-ai` | Refusal notice ("weekly rate limit of 500000 diff characters") in place of a review; no finding carried. | No action — refusal, not a finding (§ Reviewer participation). |

All three inline-review-thread surfaces read empty (`get_review_comments` → `totalCount: 0`); the
review-summary surface (`get_reviews`) and issue-comment surface (`get_comments`) were both read (§
Reviewer participation). No reviewer produced an actionable finding, so nothing was fixed, rejected,
or deferred from CI/PR review.

## Reviewer participation

Expected reviewer population **derived from configuration** — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(`coderabbit.md`, `pr-agent.md`, `sourcery.md`), cross-named by `.github/workflows/pr-agent.yml`.
M = 3. Each verdict is read from the stored comment bodies, not from a check state.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` (pr-agent) | `reviewed` | Posted its `## PR Reviewer Guide 🔍` issue comment (id `5278870121`) over this diff: "🔒 No security concerns identified", "⚡ No major issues detected", "🧪 PR contains tests" — an explicit clean review, no findings to action. |
| `coderabbitai` (coderabbit) | `rate-limited` | Posted **only** its "Review limit reached" refusal notice (id `5278862141`) in place of a review — "you've reached your PR review limit … Next review available in: 112 minutes". Class `awaitable_window` (rolling window, reopens on its own); commit-status `CodeRabbit` context is `success`/"Review rate limited". Engaged but did not review this diff. |
| `sourcery-ai` (sourcery) | `rate-limited` | Posted **only** a `COMMENTED` review (id `4925755119`) carrying its refusal — "you have reached your weekly rate limit of 500000 diff characters". Class `hard_quota` (weekly diff-character quota, cause=quota); does not reopen by waiting. Engaged but did not review this diff. |

**Coverage: 1 of 3 reviewed.** The § Step 8 shortfall disclosure fired before arming auto-merge:
"Review coverage 1 of 3 — `cuioss-review-bot` reviewed clean; `coderabbitai` rate-limited (rolling
window, reopens ~112 min); `sourcery-ai` rate-limited (weekly diff-character quota)." Both rate
limits are routine and outside our control, so per § Step 8 condition 4 (disclose-not-block) the
shortfall changed only what the run **said**, not whether it merged.

## Cost

- **Tokens:** not available to the agent in this session — the Claude Code cloud harness does not
  surface a per-run token total to the agent.
- **Wall-clock:** not precisely available. Derivable GitHub anchors only: PR #1205 opened
  `2026-08-13T10:02:55Z`; the first `verify` run concluded `10:13:58Z` (~11 min build). The run
  spanned an initial implementation session plus this resumed review/merge session; no single
  authoritative start/end timestamp is exposed to the agent.
- **Population:** these anchors count one interactive Claude Code cloud session's GitHub-observable
  timestamps. They are **NOT comparable** to a plan-marshall `metrics.toon` total, which counts the
  orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary — a boundary
  this single interactive cloud session does not share. No comparable figure can be produced here.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named in § Skills loaded; all obtained via bundle path. |
| 2 Branch | Done — harness-assigned `claude/main-sha-worktree-config-hash-mrscwi`, published on `origin`, kept as-is (no rename, no prefix). |
| 3 Plan directory | Done — `doc/plans/truthful-signals/290-…/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | Done — 3 implementation commits carry the `Co-Authored-By: Claude` trailer; D0–D2 addressed. |
| 4 Per-commit gate | Done — the `*.py`-touching commit was preceded by a clean `./pw quality-gate` (`total_issues: 0`). |
| 4 Pushed | Done — no unpushed commit remains after each push. |
| 5 Build gate | Done — Python change (`_invariants.py` + tests) → `./pw verify` green (`=== verify: SUCCESS ===`, 19458 passed). |
| 6 Verification sub-agent | Done — findings D0-1, D2-1, D2b-proxy, R-1 all fixed (§ Findings). |
| 7 PR cycle | Done — PR #1205; all three comment surfaces read; every comment dispositioned (2 rate-limit refusals + 1 clean guide; no actionable findings; no inline threads). |
| 8 Merge gate | Conditions 1–3 met; 1-of-3 coverage disclosed (condition 4); auto-merge armed (SQUASH). Session cannot block-until-landed (§ Cloud session affordances), so the landing is delegated to the merge queue / orchestrator collect — completed, not partial. |
| 8 Bridge | No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; report carries the PR number + per-deliverable outcome the orchestrator collects. |
| 9 This check | This table. |
| 9 What have we learned | Recorded below. |

**GitHub access path:** GitHub MCP server (the cloud path).
**Branch form:** harness-assigned (`claude/*`), kept as-is.
**Plugin cache sync:** not owed — `/sync-plugin-cache` is a machine-local build step a cloud run
never performs or owes (§ Scope and precedence).

## What have we learned (Step 9)

**None proposed.** This resumed session exercised Steps 7–9 (PR review cycle + merge gate) end to
end and the contract described the environment accurately: the three comment surfaces were read as
specified (`get_comments`, `get_reviews`, `get_review_comments`), the reviewer population derived
cleanly from the three registry docs, the MCP `mergeable_state: clean` mapping held (§ Step 8
condition 1), and the merge-queue arm-and-hand-off completion covered the case where the session
cannot block-until-landed. No step was ambiguous in practice and no command failed as written, so
there is no run-produced evidence for a contract change — speculative edits are excluded by the
step's own rule.

## Residue

- The **checkout-context** stability of `config_hash` (worktree-vs-main resolution of `marshal.json`
  when a plan edits `marshal.json` on its branch) is **not** addressed here — it is the resolver
  defect owned by the sibling plan (310). This fix addresses only the phase-context defect, which is
  the one the plan observed.
- Out-of-scope siblings recorded, not fixed: the `.plan/` path-exemption in the dirty-path filter,
  and the wrong-commit-recorded-confidently instance in baseline reconciliation.
