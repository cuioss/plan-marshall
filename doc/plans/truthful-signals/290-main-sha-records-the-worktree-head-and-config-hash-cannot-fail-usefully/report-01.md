# Run report — 290-config-hash-cannot-fail-usefully (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/main-sha-worktree-config-hash-mrscwi` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

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

An empty CI/PR-review row set below reflects that the PR has not yet been opened; populated after
Step 7.

## Reviewer participation

_(populated after the PR review cycle)_

## Cost

_(populated at close)_

## Contract check (Step 9)

_(populated at close)_

## What have we learned (Step 9)

_(populated at close)_

## Residue

- The **checkout-context** stability of `config_hash` (worktree-vs-main resolution of `marshal.json`
  when a plan edits `marshal.json` on its branch) is **not** addressed here — it is the resolver
  defect owned by the sibling plan (310). This fix addresses only the phase-context defect, which is
  the one the plan observed.
- Out-of-scope siblings recorded, not fixed: the `.plan/` path-exemption in the dirty-path filter,
  and the wrong-commit-recorded-confidently instance in baseline reconciliation.
