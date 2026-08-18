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
| Checkout-context stability of `config_hash` (worktree-vs-main resolution of `marshal.json`), deferred to plan 310 | **Closed by plan 310 with an explicit no-work verdict** (corrected during adversarial review — an earlier draft of this row read "Still open", which mistook an unchanged line of code for an unanswered question). The code fact stands: `get_marshal_path` → `get_tracked_config_dir` (`file_ops.py:1274-1292`) is still cwd-relative, and `7612c3a7` changed `_invariants.py`, `_handshake_commands.py` and `marketplace_paths.py` but not `file_ops.get_tracked_config_dir`. But plan 310 **took up the hand-off and adjudicated it**: `doc/plans/code-intelligence-substrate/310-…/report-01.md:46-52` — "`config_hash` deserves a named verdict because the predecessor plan (`truthful-signals/290-…`) explicitly deferred its 'whole-checkout stability' here. **Verdict: not a member of this population.** Its name makes no main claim, and its cwd-relative `marshal.json` read is the ADR-002 rule rather than a mislabel" — restated at `:690-694` as "No work is owed on it." Out of scope here either way, so not a gap against this plan |
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
  previously only a same-phase write did. **Re-swept during adversarial review with a broader
  pattern** than the original caller trace: every `config['plan']` writer in the `manage-config`
  scripts was enumerated (`_cmd_effort.py:737`/`:779`/`:902`, `_cmd_finalize_steps.py:127`/`:336`,
  `_cmd_quality_phases.py:343`–`:525`, `_cmd_skill_domains.py:931`, `_cmd_steps_sort.py:83`), then
  every documented invocation of the verbs that reach them (`plan phase-N set` / `set-steps` /
  `add-step` / `remove-step` / `set-max-iterations` / `set-step` / `set-domain-step`, `effort`,
  `finalize-steps`, `steps-sort`, `sync-defaults`) was located across `marketplace/bundles/`. Every
  hit is in `manage-config`'s own `SKILL.md` / `standards/`, or in `marshall-steward`
  (`references/menu-configuration.md`, `wizard-flow.md`, `upgrade-flow.md`) — the configuration
  wizard, not a plan run. **No phase workflow (`phase-1-init` … `phase-6-finalize`) and no
  `plan-orchestrator` surface writes under `plan.*`.** Coverage caveat, stated so the negative is
  honest: this sweep covers *documented* invocations under `marketplace/bundles/`; a caller
  constructing the command dynamically in Python would not appear in it. Downgraded from "unverified"
  to "swept, no mid-run writer found, with the sweep's coverage named" — not to "cleared".

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every gap (G1–G4), every clean-pass row, both "swept, clean" claims, and every stated
figure. By these means:

- **Functions executed, not read.** The **pre-fix** `_capture_config_hash` body was reconstructed
  verbatim from `git show b2982e75` and run in-process against this repository's real
  `.plan/execute-script.py` and `.plan/marshal.json`. It returned three *distinct, non-`None`*
  values — `1-init` → `93acf2ec06e7525e`, `5-execute` → `c7935ba60629440a`, `6-finalize` →
  `be9e8282403378dc` — against the shipped body's `1c86cdcf6ffad590` at all three. This settles the
  D0 refutation by execution of the disputed function itself, not by execution of the CLI it calls.
- **CLI re-run.** `plan phase-5-execute get --audit-plan-id …` through the executor → **exit 0**,
  TOON payload; the same call direct against `manage-config.py` with the full marketplace
  `PYTHONPATH` → **exit 2, "unrecognized arguments: --audit-plan-id"**. Divergence reproduced.
- **Mechanism confirmed at its own source, and at the run's commit.**
  `extract_audit_plan_id` (`execute-script.py.template:1221-1253`, call site `:1417`) strips the
  flag unconditionally for every notation; the identical code is present at `b2982e75^`
  (`git show b2982e75^:…template | grep -n audit-plan-id` → `:11`, `:793`, `:1245`, `:1416`,
  `:1488`), so it held during the run.
- **Mutations (3).** Each preceded by `git diff --quiet -- <path>` (exit 0), each file byte-copied to
  the scratchpad first and restored from those bytes, never via git; `git diff --quiet` exit 0 after
  each restore. (1) `_invariants.py:1537` re-scoped to `…get('plan',{}).get(f'phase-{_phase}',{})` →
  `test_capture_config_hash_stable_across_phases` RED with `assert '1d5a717211d94465' ==
  '845f280d404d3099'`, **reproducing this document's recorded values exactly**. (2)
  `summarize-invariants.py:275` with `'config_hash'` added to `excluded` →
  `TestDetectDrift::test_config_hash_change_is_drift` RED, 30 others green. (3) **New:**
  `_invariants.py:1535-1536` (the non-dict guard) deleted → `test_invariants_behavior.py` +
  `test_lifecycle_handshake_e2e.py` + `test_invariants.py` = **168 passed**, proving G2's gap by
  mutation rather than by grep.
- **Every figure re-derived.** `test_invariants_behavior.py` → **47 passed**; `-k config_hash` →
  **5 passed, 42 deselected**; the three-file set → **77 passed** (124 total, as stated).
  `_capture_config_hash` at `:1495`; docstring defect-(2) at `:1514-1518`; "fail-closed" at
  `:1524-1526`; non-dict guard at `:1535-1536`; `_hash_dict(config.get('plan',{}))` at `:1537`;
  `_run_script` `:467-487`; `capture_all` `:1868-1897` with the `None`-skip at `:1893-1894`;
  `INVARIANTS` `:1665`; blocking map `:1774`; classification comment `:1710-1715` (pre-fix
  `:1502-1507`); `_diffs` `:467-512` with the `''`-skip at `:495-498`; `detect_drift` `:267`,
  `excluded` `:275` (contents confirmed, `config_hash` absent); `argparse_surface.py:213-215`;
  `--audit-plan-id` at `manage-config.py:389` (`build-decision`) and `:420` (`sync-defaults`),
  identical at `b2982e75`. Landed diff = **8 paths** (rename counted once). No source file changed
  between `a2fd69ee` and today's HEAD (`git diff --name-only` returns only `doc/plans/` files), so
  every line number above is current.
- **Both "swept, clean" claims re-run with broader patterns.** (a) The stale-prose sweep was
  re-run not on `config_hash` but on the *phrasings of the false claim* —
  `never fired at all|signal that never fired|does not accept|noun does not accept|exited non-zero|unrecognized arguments`
  across `marketplace/ test/ doc/ .claude/`. The only production carriers of the refuted claim
  remain `_invariants.py:1515-1517` and `test_invariants_behavior.py:203-204`; every other hit is
  unrelated. The `config_hash` sweep was also re-run and confirms `phase-handshake.md:133` and
  `invariant-check-summary.md:17` are accurate and that `test_lifecycle_handshake_e2e.py:22`/`:108`
  do **not** repeat the dead-capture claim. (b) The "no mid-run writer" sweep was widened from two
  named verbs to all nine `config['plan']` writers and every documented invocation of the verbs that
  reach them — see § What could NOT be verified for the result and its coverage caveat.
- **Cited commits verified.** `77fd1156` = "fix(finalize): .plan/ dirty-source guards exempt on
  trackedness, not path prefix (#1217)"; `7612c3a7` = "fix(phase-handshake): read main-scoped columns
  from main, not the pinned cwd (#1286)", and its `--name-only` list confirms `file_ops.py` untouched.
  Plan 310's report was read directly (`:38-52`, `:685-694`).
- **G1's "actionably misleading" claim tested.** The cited call sites were opened:
  `planning.md:117`/`:193`, `planning-outline.md:183`/`:342`/`:591`, `q-gate-validation.md:57` and
  seven more in that file all pass `--audit-plan-id` to `manage-config plan phase-N get`. Tree-wide,
  `--audit-plan-id` appears on 122 documented lines under `marketplace/`, 28 of them within three
  lines of a `manage-config` notation. "Dozens" is supported.

**NOT re-checked.** `./pw verify` totals (`19458 passed, 14 skipped`, coverage `COMPLETE`) — still
not re-run. The GitHub/CI surface (check conclusions, comment ids, `mergeable_state`, the 1-of-3
reviewer coverage) — not re-derived. The original `.plan/` incident record (the four hash values,
the `main_sha` whose only containing ref was the feature branch, the emitted drift warning) —
still unreachable, as the plan itself flagged. The `main_sha` half and the baseline-reconciliation
sibling — out of scope by the plan's own boundary, deliberately not examined.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| Verdict `implemented-with-gaps` | Rows support it | **upheld** | D0/D1/D2(a)/D2(b) are all *implemented*; every defect is documentation accuracy or one missing test. No deliverable is unimplemented, so `partially-implemented` would be wrong. The "D2 (supporting)" row is a self-added contract-test row, not a plan deliverable |
| D0 row — "dead capture" refuted | `high`-value refutation of the report's defect #1 | **upheld, strengthened** | Refuted a second and stronger way: the pre-fix function body itself executed and returned three distinct non-`None` hashes. Reading the callee is no longer load-bearing |
| D0 row — hand-off not triggered | No resolver touched by the fix | **upheld** | `git show --stat b2982e75` shows no `file_ops.py`/`marketplace_paths.py` change; and plan 310, which owns the resolver, independently ruled `config_hash` "not a member of this population" |
| D1 row — clean pass | Determination recorded, nothing suppressed | **upheld** | `config_hash` present in `INVARIANTS:1665`, `blocking_at_every_boundary` at `:1774`, absent from `excluded` at `summarize-invariants.py:275` — each read at HEAD, and the last one locked by mutation 2 |
| D2(a) row — clean pass | Passes, non-vacuous | **upheld** | Mutation 1 re-applied independently; RED with the exact hash pair this document recorded |
| D2(b) row — clean pass | Passes, non-vacuous, anti-silencing | **upheld** | Capture-level test read (it writes two genuinely different `marshal.json` bodies — not a stub assertion); detector-level lock re-driven RED by mutation 2 |
| D2 (supporting) row — non-dict branch untested | Grep found no test | **upheld, strengthened** | Proven by mutation instead of by grep: guard deleted, 168 tests still pass |
| G1 | Refuted dead-capture claim shipped in docstring + test comment; `high` | **upheld** (line ref narrowed, Done-when made mechanical) | Severity `high` kept after challenge: it is not a sentence nobody acts on — it declares 28 documented, working call sites broken. `stale-statement` already carries `high` on four gaps elsewhere in this epic, so the taxonomy permits it. `test_invariants_behavior.py` ref narrowed `:203-206` → `:203-204` (`:205-206` state the *true* defect) |
| G2 | Non-dict `marshal.json` branch advertised but untested; `medium` | **rewritten** (severity unchanged) | Gap real and now mutation-proven. Its **rationale was fabricated**: "would hash `{}`" is impossible — no non-dict JSON top level has `.get`, so the guardless capture raises `AttributeError` out of `capture_all`. Rewritten |
| G3 | `None` return wrongly called "fail-closed"; `low` | **rewritten** (severity unchanged) | Gap real: `capture_all:1893-1894` skips, `_diffs:495-498` skips, so the *boundary* does not block. But "no diagnostic" is **false** — `config_hash` ∈ `_CORE_INVARIANTS` (`summarize-invariants.py:49-56`) and a blank column raises a severity-`error` finding (`:341-350`), test-locked at `test_summarize_invariants_behavior.py:276-292`. Narrowed to "post-hoc, not absent" |
| G4 | `--audit-plan-id` is on `build-decision` + `sync-defaults`, not `build-map`; `low` | **upheld** | `manage-config.py:389` under `p_bd` (`build-decision`), `:420` under `p_sync` (`sync-defaults`); byte-identical at `b2982e75`; parser context read at `:375-423` |
| G5 | *(new)* `build-decision --audit-plan-id` is unreachable through the executor; `medium` | **added** | Executed: via the executor `--audit-plan-id` → `status: error` naming that very flag; the `--plan-id` control → `status: success`. The executor strips it unconditionally, so `_cmd_build_map.py:160`'s fallback is dead and `manage-config/SKILL.md:1428`'s "accepted as an alias" is false |
| Residue row — `config_hash` checkout stability | "Still open" | **corrected** | Plan 310 explicitly adjudicated the hand-off: "Verdict: not a member of this population … No work is owed on it" (`310-…/report-01.md:46-52`, `:690-694`). An unchanged line of code is not an unanswered question |
| "New false-positive surface" | Recorded as unverified | **re-swept, narrowed** | All nine `config['plan']` writers enumerated and all documented invocations located: every one is `manage-config`'s own docs or `marshall-steward`. No phase workflow or orchestrator surface writes under `plan.*`. Coverage caveat named |

**Documents corrected.** *gaps.md*: open items `4` → **5**; **G5 added** (new, `medium`, executed
evidence); **G2** and **G3** rationales rewritten where they asserted an unrun mechanism; **G1**'s
test-file line range narrowed to `:203-204`, its corroboration-from-incident-data clause labelled as
the weaker evidence it is, and its Done-when replaced with a mechanical zero-hit grep; **G3**'s
Done-when replaced with a grep plus a three-direction content requirement; a `## Refuted during
adversarial review` section added recording the two refuted clauses and the one weakened one — no
gap was refuted in whole. *verification.md*: the `config_hash`-checkout-stability residue row
corrected from "Still open" to closed-by-verdict; the "new false-positive surface" item promoted
from unverified to swept-with-named-coverage; this section appended. Nothing was renumbered; the
verdict is unchanged.

**Residual doubt — where a third reviewer should start.** (1) **G5's blast radius.** I confirmed
`build-decision --audit-plan-id` fails through the executor, but I did not enumerate the consumer
sites ADR-004 names as calling the sole build/no-build authority (`pre_push_quality_gate_inactive`,
`pre-commit-verify-freshness`, the phase-5 verify surfaces) to see whether any passes
`--audit-plan-id` in practice. If one does, G5 is `high`, not `medium` — a real gate failing to
`unknown` and, per ADR-009, spuriously building. (2) **Whether the executor stripping is itself the
defect.** `argparse_surface.py:213-215` asserts no target parser may declare `audit-plan-id`, yet
`manage-config.py` declares it twice and `plugin-doctor` passed the tree. Something that should have
caught this did not, and I did not look for the check. (3) **The `./pw verify` totals**, still
carried on the report's word alone across two reviews now.
