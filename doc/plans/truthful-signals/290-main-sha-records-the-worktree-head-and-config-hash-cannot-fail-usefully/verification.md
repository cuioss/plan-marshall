# Verification — 290-main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully

**Verified against:** commit `a2fd69eecaad4e2b5e5572e68583c06be8744f6e`   **Landed as:** PR #1205, commit `b2982e75dc8e1c87fd60d44cd176f36be859babe`   **Verdict:** implemented-with-gaps

## Method

Read `plan.md` and `report-01.md` in full. Located the landed commit via
`git log --oneline --all --grep '#1205'` → `b2982e75`; read the full diff
(`git show --stat -M --name-status b2982e75`, then per-file diffs for `_invariants.py`,
`phase-handshake.md`, `invariant-check-summary.md`).

Files opened at HEAD:

- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py`
  (`_capture_config_hash` :1495-1537, `_hash_dict` :490, `_run_script` :467-487,
  `INVARIANTS` registry :1665, blocking-scope map :1774 and its rationale comment :1710-1715,
  `capture_all` :1868-1897)
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_commands.py`
  (`_diffs` :467-512, `cmd_verify` :515-641)
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/summarize-invariants.py`
  (`_CORE_INVARIANTS` :49-56, `detect_drift` :267-302)
- `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py`
  (`get_tracked_config_dir` :1274-1292, `get_marshal_path` :1307-1309)
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py`
  (`_add_phase_subparser` :70-108, plan-noun wiring :306-314, `--audit-plan-id` declarations
  :389 and :420)
- `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template`
  (usage line :11, `extract_audit_plan_id` :1222-1254, call site :1417)
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/argparse_surface.py`
  (`UNIVERSAL_FLAG_ARITY` rationale :200-252)
- `marketplace/bundles/plan-marshall/skills/plan-marshall/references/phase-handshake.md` (:133)
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/invariant-check-summary.md` (:17)
- `test/plan-marshall/plan-marshall/test_invariants_behavior.py` (:1-27, :199-303)
- `test/plan-marshall/plan-marshall/test_lifecycle_handshake_e2e.py` (:15-30, :100-120, :160-175)
- `test/plan-marshall/plan-retrospective/test_summarize_invariants_behavior.py` (:229-262)

Tests run (all from repo root, `-o addopts="" -q`):

- `test_invariants_behavior.py` → **47 passed**
- `test_summarize_invariants_behavior.py` + `test_lifecycle_handshake_e2e.py`
  + `test_phase_handshake_capture_verify.py` → **77 passed**

Functions executed (not merely read):

- `_capture_config_hash('p', {}, phase)` against the repository's real `.plan/marshal.json` for
  `1-init` / `5-execute` / `6-finalize` → **`1c86cdcf6ffad590` three times** (phase-independence
  demonstrated on real input, not a fixture).
- The **pre-fix** capture command through the executor:
  `python3 .plan/execute-script.py plan-marshall:manage-config:manage-config plan phase-5-execute get --audit-plan-id VERIFY-290`
  → **exit 0**, parseable TOON payload. Same command run against `manage-config.py` **directly**
  (bypassing the executor) → **exit 2, "unrecognized arguments: --audit-plan-id"**. The divergence
  is the evidence for the report-accuracy finding below.
- `manage-config plan phase-1-init get --audit-plan-id …` through the executor → exit 0, a payload
  that differs from the `phase-5-execute` payload (confirming the phase-scoping defect the fix
  addresses).

Mutations applied (each preceded by `git diff --quiet -- <path>`, exit 0 = clean; each file
snapshotted to the scratchpad first and restored from those bytes, never via git):

1. `_invariants.py:1537` — `_hash_dict(config.get('plan', {}))` → `…get(f'phase-{_phase}', {})`
   (re-introducing phase scoping). `test_capture_config_hash_stable_across_phases` went **RED**
   (`assert '1d5a717211d94465' == '845f280d404d3099'`); the other four config_hash tests stayed
   green. Restored; `git diff --quiet` exit 0.
2. `summarize-invariants.py:275` — added `'config_hash'` to `detect_drift`'s `excluded` set.
   `TestDetectDrift::test_config_hash_change_is_drift` went **RED**. Restored; `git diff --quiet`
   exit 0.

Both D2 controls are therefore non-vacuous. No other file was modified.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: confirm the config-hash capture by symbol, derive its inputs, classify handle-vs-cwd resolution, check the hand-off condition | Computation read and reported; every input named; capture classified | Yes | **No** — one of the two "empirically confirmed" defects is refuted by execution | Partly | Yes | Symbol correctly located (`_capture_config_hash`, old `_invariants.py:1311`, new `:1495`). Inputs named. Classification (cwd-relative via `get_marshal_path` → `get_tracked_config_dir`, `file_ops.py:1274-1292`) confirmed correct. **Defect #1 ("capture is dead, exit 2, `None` at every boundary") is FALSE** — the executor strips `--audit-plan-id` before dispatch (`execute-script.py.template:11`, `extract_audit_plan_id` :1222, call site :1417); the exact pre-fix command through `.plan/execute-script.py` exits **0**. Hand-off condition correctly evaluated as not triggered (no resolver is touched by the fix; `git show --stat b2982e75` shows no `file_ops.py` / `marketplace_paths.py` change) |
| D1 | Settle the stability question; make context-independent OR rename; never suppress | A determination is recorded | Yes | Yes | Yes | Yes | Determination recorded in report § D1 ("the four drifts were not real; phase-scoped value fed to a cross-phase detector"). Independently corroborated: `manage-config plan phase-1-init get` and `plan phase-5-execute get` return different payloads → different hashes by construction. Fix at `_invariants.py:1528-1537` hashes `marshal.json`'s phase-independent `plan` section. Nothing suppressed — `config_hash` is still in `INVARIANTS` (:1665), still `blocking_at_every_boundary` (:1774), still absent from `detect_drift`'s `excluded` (`summarize-invariants.py:275`) |
| D2(a) | Same config hashed from two contexts → same value; verified RED pre-fix | Passes, seen red first | Yes | Yes | Yes | Yes | `test_capture_config_hash_stable_across_phases` (`test_invariants_behavior.py:250-277`) passes; mutation 1 above drives it RED. Also demonstrated on the real `marshal.json`: identical hash `1c86cdcf6ffad590` at three phases |
| D2(b) | A genuine config change still drifts (the anti-silencing control); verified RED pre-fix | Passes, seen red first | Yes | Yes | Yes | Yes | `test_capture_config_hash_drifts_on_genuine_config_change` (`:279-303`) passes. Detector-level lock `TestDetectDrift::test_config_hash_change_is_drift` (`test_summarize_invariants_behavior.py:244-255`) passes and goes RED under mutation 2 |
| D2 (supporting) | Contract tests rewritten for the new read: absent / unreadable / non-dict / plan-section | Documented in the test module docstring | Partly | **No** | n/a | **No** | Three of the four named branches have tests (`:219`, `:231`, `:240`). The **non-dict** branch (`_invariants.py:1535-1536`) has **no test** — `grep -n "non_dict\|non-dict\|not_dict"` in `test_invariants_behavior.py` returns only the unrelated `test_hash_dict_handles_non_dict_payload` (:103). The module docstring at `:17` names it anyway |

### D0 — the "dead capture" claim is refuted

`report-01.md` § D0 states, as one of "two compounding defects (both empirically confirmed)", that
the pre-fix capture was dead: `manage-config plan phase-5-execute get --audit-plan-id X` "exits
**code 2**", `_run_script` returns `None`, "the signal is permanently absent (this epic's exact
archetype)". The docstring shipped in production repeats it verbatim
(`_invariants.py:1514-1518`), as does the test-module comment
(`test_invariants_behavior.py:203-206`) and the landed commit body of `b2982e75`.

The report says the claim was "empirically verified by invoking the real script with the
marketplace PYTHONPATH" — i.e. by invoking `manage-config.py` **directly**. That is not the path
`_capture_config_hash` used. `_run_script` (`_invariants.py:467-487`) builds
`['python3', '<repo>/.plan/execute-script.py', *args]`, and the executor **consumes and strips**
`--audit-plan-id` before the target script's argparse ever runs — documented at
`execute-script.py.template:11` ("stripped before passing to script"), implemented in
`extract_audit_plan_id` (`:1222-1254`) and applied at `:1417`, and independently asserted in
`argparse_surface.py:213-215` ("injected and consumed by the executor wrapper BEFORE the target
script's argparse runs"). The same stripping is present in the template at `b2982e75^`, so it held
at the moment of the run.

Executed at HEAD: the direct invocation exits **2**; the executor invocation exits **0** and
returns the phase config as TOON. The pre-fix capture was therefore **alive and returning a
phase-scoped hash** — which is also the only reading consistent with the plan's own observation of
*four distinct recorded hash values* across four boundaries. A capture returning `None` at every
boundary would have produced no values and no drift at all; defect #1 and the plan's evidence are
mutually exclusive, and the run did not notice.

This does not invalidate the fix: defect #2 (phase-scoped value compared cross-phase) is real,
confirmed by execution, and is what the shipped change corrects. What is wrong is the recorded
diagnosis, now embedded in a production docstring. See gaps G1 and G4.

### D2 (supporting) — a documented branch with no test

`test_invariants_behavior.py:17` claims the suite covers "the absent / unreadable / non-dict /
plan-section branches". The `non-dict` guard is `_invariants.py:1535-1536`
(`if not isinstance(config, dict): return None`) and no test writes a non-dict `marshal.json`
(e.g. a top-level JSON array). This bullet is itself the "Fixed" disposition the run recorded for
sub-agent finding D2-1, so the correction introduced a fresh inaccuracy. See gap G2.

## Report accuracy

Contradicted by the tree:

1. **"The capture is dead in current code … exits code 2 … the signal is permanently absent."**
   Refuted by execution — see D0 above. The executor strips the flag; the pre-fix command exits 0.
2. **"that flag exists only on the `build-decision` / `build-map` nouns."** At `b2982e75` and at
   HEAD, `--audit-plan-id` is declared exactly twice in `manage-config.py` — `:389` under
   `build-decision` and `:420` under `sync-defaults`. `build-map` declares none
   (`git show b2982e75:…/manage-config.py | grep -n audit-plan-id` → `389`, `420`). See gap G4.
3. **Build gate: "`_invariants.py` and two test files changed."** The landed diff carries **three**
   test files (`test_invariants_behavior.py`, `test_lifecycle_handshake_e2e.py`,
   `test_summarize_invariants_behavior.py`). The report itself explains the third as added after
   sub-agent review, so this is an internally reconcilable staleness rather than a false claim; no
   gap filed.

Re-derived and found accurate:

- `_capture_config_hash` at pre-fix `_invariants.py:1311` — matches the diff hunk `@@ -1308,25`.
- `detect_drift` at `summarize-invariants.py:267` — exact at HEAD.
- `config_hash` **not** in `detect_drift`'s `excluded` set (`:275`: `main_dirty`, `worktree_dirty`,
  `qgate_open_count`, `unfinished_tasks_count`) — confirmed, and locked by a test that goes red
  when violated.
- "the full config_hash block was seen 5 failed pre-fix, 5 passed post-fix" — there are exactly
  **5** config_hash tests in `test_invariants_behavior.py` (`:219`, `:231`, `:240`, `:250`, `:279`);
  `-k config_hash` collects 5.
- The corroborating blocking-classification comment declaring `config_hash` "should remain stable
  across every boundary" exists (report cited pre-fix `:1502-1507`; at HEAD `:1710-1715`).
- `blocking_at_every_boundary` retained for `config_hash` (`_invariants.py:1774`).
- "no other stale `config_hash` prose in the tree" — re-derived by grepping `config_hash` across
  `marketplace/`, `test/`, `doc/`, `.claude/`: the two reference docs were updated in the landed
  diff and every remaining hit is a column name, a fixture value, or accurate new prose.
- Test-count claim `19458 passed, 14 skipped` from `./pw verify` — not re-derived (see below).

## Out-of-scope compliance

Compliant. The landed diff (`git show --stat -M b2982e75`) touches exactly 8 paths: the plan-file
rename to `plan.md` (R100), the new `report-01.md`, `_invariants.py`, two reference docs, and three
test files. Specifically:

- **No `main_sha` work.** No resolver (`_repo_root`, `get_base_dir`, `get_tracked_config_dir`,
  `_find_plan_root_from_cwd`), no capture-time ancestor assertion, no population sweep. The
  main-scoped-field work landed separately as `7612c3a7` (PR #1286, plan
  `code-intelligence-substrate/310-main-sha-records-the-pinned-cwd`), after this plan.
- **No suppression.** `config_hash` remains registered, blocking at every boundary, and outside
  `detect_drift`'s exclusion set — each verified by reading the symbol and by mutation.
- **The `.plan/` path-exemption sibling** was recorded, not fixed here — correct.
- No undeclared collateral change.

## Residue carried forward

| Residue declared in report-01.md | Status in today's tree |
|---|---|
| Checkout-context stability of `config_hash` (worktree-vs-main resolution of `marshal.json`), deferred to plan 310 | **Still open.** `get_marshal_path` → `get_tracked_config_dir` (`file_ops.py:1274-1292`) is still cwd-relative; `7612c3a7` (plan 310) changed `_invariants.py`, `_handshake_commands.py` and `marketplace_paths.py` but not `file_ops.get_tracked_config_dir`. Correctly declared as out of scope here, so not a gap against this plan |
| `.plan/` path-exemption hole in the dirty-path filter (record, do not fix) | **Closed by later work.** `_invariants.py:618-657` now drops a `.plan/` path only when it is *not* git-tracked; landed as `77fd1156` (PR #1217, "exempt on trackedness, not path prefix") |
| Wrong-commit-recorded-confidently instance in baseline reconciliation | Not re-examined — out of this plan's surface and cited, not merged, as the plan directed |

## What could NOT be verified

- **The original incident data.** The four recorded `config_hash` values, the `main_sha` whose only
  containing ref was the feature branch, and the emitted drift warning all live in `.plan/`
  (git-ignored). The plan itself flagged this. The *mechanism* was verified from source and by
  execution instead; the incident record was not.
- **`./pw verify` totals** (`19458 passed, 14 skipped`, coverage `COMPLETE`). Not re-run — a
  full-tree verify is far outside this check's budget. The targeted suites (124 tests across four
  files) all pass at HEAD.
- **PR/CI-surface claims** (check conclusions, reviewer comment ids, `mergeable_state: clean`, the
  1-of-3 reviewer coverage). Not re-derived from GitHub.
- **New false-positive surface from widening the hash.** The fix hashes the whole `plan` section
  rather than one phase's subtree, so any mid-run write anywhere under `plan.*` (e.g. `plan.effort`,
  `plan.phase-6-finalize.steps`) now drifts a `blocking_at_every_boundary` invariant where
  previously only a same-phase write did. The writers I checked (`manage-config effort
  apply-preset`, `steps-sort`) are reachable only from the `marshall-steward` configuration wizard,
  not from a plan run, so I found no concrete mid-run writer — but I did not trace every caller, so
  this is recorded as unverified rather than cleared.
