# Verification — 190-frozen-manifest-diverges-from-live-config

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Landed as:** `d2e94b4` — *"fix(finalize): reconcile the frozen manifest against live config; refresh the executor after a rebase (#1236)"*, 23 files, +2115/−50 (re-derived via `git show --numstat --format="" d2e94b4`)
**Overall verdict:** CONFIRMED WITH GAPS

Every deliverable is present in the tree and does substantially what the plan asked. **One gap is
high:** D3's on-disk post-assertion — the round-1 F7 fix that was supposed to tie
`executor_regenerated` to reality rather than to an exit code — checks only that *an* executor is in
the slot, and the rebase population always has one there, so a generation that wrote nothing is
reported as a successful refresh over the stale file it failed to replace (gap G15, measured). Two
further gaps are scope limits inside D2 that neither the code nor its documentation names: the
reconciliation cannot fire for external (`project:` / `bundle:skill`) steps at all, and its backfill
direction bypasses every composer pre-filter, ceremony gate, and lane-resolution pass. D3 carries a
second, narrower defect: a "never raises" contract that is only partially implemented. The run
report's factual claims about the code hold; three of its bookkeeping counts do not.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE: re-ground all four defects | All four CONFIRMED live; one asserted absence half-refuted | Two spot-checked directly against the `d2e94b4^` blobs and both hold; the refutation is recorded and visibly reshaped D2 | CONFIRMED |
| D1 | GATE: name current behaviour, settle fail-direction | Hard abort today; settled direction = diff-and-backfill, split stale-vs-broken | The split is implemented and documented in three places (`SKILL.md` § `reconcile`, `manifest-schema.md`, `required-steps.md` § Reconciliation Contract) | CONFIRMED |
| D2 | Reconcile frozen manifest vs live config at finalize entry | `cmd_reconcile` + `compose` candidate snapshot + Step 1.5 rewire | All three present and wired; but external steps are structurally exempt and backfill bypasses the composer's filters | PARTIAL |
| D3 | Regenerate executor after a script-set-changing rebase | `_run_generate_executor` / `_refresh_worktree_executor` in `cmd_worktree_rebase_to`, three payload fields | The three bounds hold (the indeterminate bound confirmed against the real generator), but the success verdict is a presence check that the rebase population always satisfies, and the seam's "never raises" promise is incomplete | PARTIAL |
| D4 | Finalize prompt and log residue (3 items) | All three shipped | All three verified verbatim in the tree | CONFIRMED |
| D5 | Three tests, each verified to fail pre-fix | 15 / 6 / 7 tests, pre-fix reds recorded | 19 / 10 / 8 tests landed, 37 pass; three independent mutations each turn one red | CONFIRMED |

## Per-deliverable detail

### D0 — GATE: re-ground all four defects against the implementing source

- **Required (plan):** *"each of the four carries a confirmed-or-refuted verdict naming the file and
  symbol that settled it. A refuted item is dropped and recorded, not quietly carried."*
- **Claimed (report):** all four CONFIRMED live; the "nothing compares the frozen manifest against
  live config" half of defect 1 REFUTED, because `validate-loadable` at Step 1.5 already was such a
  comparison.
- **Found:** `report-01.md:33-45` carries a four-row verdict table, each row naming a file and a
  symbol. I re-derived two of the four independently against the pre-merge blob:
  - Defect 2 (executor not regenerated after rebase):
    `git show d2e94b4^:.../workflow-integration-git/scripts/git-workflow.py | grep -n executor`
    returns 16 hits, none inside `cmd_worktree_rebase_to` — the only executor references are
    `_executor_path()` (a `manage-status` dispatch helper, line 757) and prose. **Confirmed.**
  - Defect 4 (title-token line unconditional): at `d2e94b4^`, `_status_query.py:313-314` reads
    `rmw_json(get_status_path(args.plan_id), _apply_set)` immediately followed by an unguarded
    `log_entry('work', …, f'[MANAGE-STATUS] Title token: {state} (owner={owner})')`, while the
    sibling `clear` branch was already gated. **Confirmed, including the stated asymmetry.**
- **Checks run:** `git show d2e94b4^:<path>` on both files; grep for the emission site.
- **Verdict:** CONFIRMED — the gate produced re-derivable verdicts, and the refutation is not
  cosmetic: it is visibly what turned D2 from "replace the guard" into "narrow the guard", which is
  the shape that actually landed.

### D1 — GATE: establish what diverges and how it is handled today

- **Required (plan):** *"the current behaviour is named and the intended fail-direction is decided
  and recorded"*, with the hard-fail direction excluded unless D1 explicitly chooses it.
- **Claimed (report):** current behaviour is a hard abort; settled direction is diff-and-backfill,
  implemented as a stale/broken split rather than a blanket softening.
- **Found:** the split is the shipped contract, stated identically in three places:
  - `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md:378-382` — the
    authoritative three-row table (`unloadable + absent → stale → Drop`; `unloadable + still listed
    → broken → Fail loud`; `loadable → retained`).
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/required-steps.md:83-102` —
    § "Reconciliation Contract", which explicitly declines to restate the table and cross-references
    it instead.
  - `.../manage-execution-manifest/scripts/manage-execution-manifest.py:2886-2893` — the same split
    in the `cmd_reconcile` docstring.
- **Verdict:** CONFIRMED. The out-of-scope entry *"Hard-failing on manifest divergence"* is honoured:
  the hard fail survives only for the `broken` half, which is the case it was originally written for.

### D2 — reconcile the frozen manifest against live configuration at finalize entry

- **Required (plan):** *"a frozen manifest referencing a deleted step reconciles rather than failing
  hard or passing silently."*
- **Claimed (report):** new `reconcile [--apply]` verb; `compose` snapshots `phase_6.candidate_steps`
  before any subtraction; Step 1.5 reconciles before the loadability check; fail-closed on unreadable
  live config.
- **Found — all four present:**
  - `manage-execution-manifest.py:2869-3055` — `cmd_reconcile`. Partition loop at 2956-2969; the
    fail-loud early return at 2972-2982 (`error: unreconcilable_step`, and it returns **before** any
    write); backfill at 2984-3004; the apply block at 3008-3041.
  - `manage-execution-manifest.py:1940-1948` — `phase_6_candidate_snapshot = list(phase_6_candidates)`
    taken after boundary normalization (1937-1938) and **before** the first pre-filter (1975 onward).
    Verified by reading the intervening lines: everything between the snapshot at 1948 and
    `_apply_commit_push_disabled` at 1975 is comment, so nothing subtracts from the list in between.
  - `phase-6-finalize/SKILL.md:356-372` — Step 1.5 dispatches
    `reconcile --plan-id {plan_id} --apply` and branches on `success` / `unreconcilable_step`; the
    loadability check follows at 374-399.
  - `manage-execution-manifest.py:2942-2949` — `candidate_source: 'unavailable'` when
    `_live_phase_6_candidates()` returns `None`, and the partition's `elif` at 2960 requires
    `live_candidates is not None`, so with no live config **every** unloadable step falls through to
    `broken`. The fail-closed claim holds.
  - Registration and dispatch: `manage-execution-manifest.py:3314-3327` (subparser, `--apply` as
    `store_true`) and `:3396` (`'reconcile': cmd_reconcile`).
- **Checks run:** full read of `cmd_reconcile` and of the compose snapshot site; `grep -rn` for
  `reconcile --plan-id {plan_id} --apply` across `marketplace/bundles/` returns exactly one call site
  (`phase-6-finalize/SKILL.md:364`); mutation M2 (below).
- **Verdict:** PARTIAL. The specified mechanism is there and behaves as documented on every path I
  read, but two scope limits are unstated and reachable:
  1. **External steps are structurally exempt** (gap G1). The partition's loadability oracle is
     `_check_step_loadable`, whose docstring at `_manifest_validation.py:460-462` says: *"External
     steps are short-circuited to `loadable: true` with an empty standards_path"*. Every
     `project:` / `bundle:skill` entry therefore lands in `retained` unconditionally, so the stale
     partition can never fire for one. A meta-project plan that deletes one of its own
     `project:finalize-step-*` skills and sweeps `marshal.json` — exactly the self-modifying
     population D2 exists for — is not helped. A resolver for that case already exists in the same
     module (`_check_step_resolvable`, `_manifest_validation.py:634`) and is used only by `compose`.
  2. **Backfill bypasses the composer entirely** (gap G3). The list comprehension at
     `manage-execution-manifest.py:2998-3004` filters on membership plus `_check_step_loadable` and
     nothing else. A candidate that entered `marshal.json` after compose is written straight into
     `phase_6.steps` without the pre-filters (`_apply_commit_push_disabled`,
     `_apply_simplify_inactive`, `_apply_security_class_inactive`, `_apply_scope_gated_finalize`),
     without the ceremony gates, and without `_apply_lane_resolution` — all of which compose runs
     (`manage-execution-manifest.py:1975`, `:1980`, `:1994`, `:2023`, `:2043`, `:2232`, `:2254`). A
     `full`-tier step backfilled into a `minimal`-posture plan will be dispatched.
  3. **Step 1.5 enumerates only two of the verb's four `status` outcomes** (gap G7) —
     `phase-6-finalize/SKILL.md:368-370` names `success` and `unreconcilable_step`, while
     `cmd_reconcile` can also return `file_not_found` (`manage-execution-manifest.py:2917-2922`) and
     `invalid_manifest` (`:2926-2939`). A prose-following dispatcher improvises at a phase-entry
     gate.
- **On the self-exercisability trap:** the report states it correctly and names the observation point
  (`report-01.md:77-79`). I confirm the trap independently: the lane never runs `phase-6-finalize`,
  and `reconcile` has exactly one call site, which is inside it. Nothing in this tree demonstrates
  the finalize-entry behaviour end to end. See § Declared residue.

### D3 — regenerate the per-tree executor after a rebase that changed the script set

- **Required (plan):** *"a rebase changing the script set leaves a regenerated executor, and a
  clean-environment dispatch resolves notations afterwards."*
- **Claimed (report):** `_run_generate_executor` (subprocess seam) + `_refresh_worktree_executor`
  (decision) wired into `cmd_worktree_rebase_to`'s success path; three bounds (no replay → no probe;
  positive drift only; indeterminate → regenerate nothing); non-fatal by contract.
- **Found:** `workflow-integration-git/scripts/git-workflow.py:815-847` (seam), `:850-936`
  (decision), `:1708-1710` (wiring, guarded on `replayed = pre_sha != post_sha` at `:1704`),
  `:1683` (the `clean` early return sharing `_EXECUTOR_REFRESH_NOT_REPLAYED`, defined at `:808-812`).
  All three bounds are real:
  - `:1704-1710` — the probe is skipped unless the SHAs moved.
  - `:889-903` — a `drift_status` outside `{'ok','drift'}` returns `unknown` and returns before the
    `generate` call; `'ok'` likewise returns early. Only `'drift'` reaches `:905`.
  - `:916-931` — the success verdict is taken from `executor_landed(worktree_executor_path(...))`,
    i.e. from disk rather than from `gen_rc`. **But see gap G15 below: it is the wrong disk
    property.**
- **The indeterminate bound, settled against the real generator rather than the spy.** Every test in
  the file replaces the seam, so nothing in the suite establishes that the "tree with no vendored
  `marketplace/bundles`" case actually produces the `unknown` verdict the bound claims. Run
  directly: `generate_executor.py drift --marketplace-root <dir-with-no-bundles>` prints
  `status: error / error: Could not read executor mappings` and exits **RC=0**; the payload carries
  no `drift_status`, so `parse_toon(stdout).get('drift_status')` yields `''`, the guard at `:889`
  fires, and the verb returns `unknown` without calling `generate`. Independently, an explicit
  `--marketplace-root` **outranks** the plugin cache (`marketplace_paths.py:775-784`: the
  `cache-first` scope short-circuits to the explicit anchor and raises rather than falling back), so
  the probe genuinely answers "did the *worktree's* script set change?" and cannot silently answer
  it from the cache. **The bound holds and is reachable.**
- **Cross-check on the probe's exit convention:** `generate_executor.py`'s `main` prints the TOON and
  `return 0` unconditionally (`:2418-2419`), and `cmd_drift` returns
  `drift_status = 'drift' if (added or removed or changed or notation_drift) else 'ok'` (`:2153`).
  So a positive drift arrives as `rc == 0` with `drift_status: drift` — the guard **can** fire. Both
  `generate` and `drift` subparsers accept `--marketplace-root` (`:2327`, `:2359`), so the seam's
  argv is valid for both verbs. The same unconditional `return 0` is what makes `gen_rc` useless as a
  *failure* signal, which is the root of G15.
- **Verdict:** PARTIAL, and the more serious of the two defects is the success verdict itself.
  1. **The on-disk post-assertion cannot fire in the population it guards** (gap G15).
     `executor_landed` (`_executor_slot.py:38-59`) checks presence — `is_file()`,
     `not is_symlink()`, `st_size > 0` — and the rebase population always has an executor in the
     slot, because `prepare_execute` generates one at phase-5 move-in and self-heals it when missing
     (`prepare_execute.py:253-262`, `:318-327`, `:598`). Measured: adding a pre-existing file to the
     fixture worktree and re-running the landed-check scenario (`drift_status='drift'`,
     `lands_executor=False`) returns `executor_regenerated: True` with
     `executor_detail: 'script set changed by the rebase; worktree executor regenerated'`, over
     bytes the generation never touched. The exit code is no fallback: `generate` with an
     unresolvable `--marketplace-root` prints `status: error` and exits **RC=0**, and
     `cmd_generate`'s own comment at `generate_executor.py:1961-1965` asserts the opposite
     ("non-zero exit via the safe_main contract") — `safe_main` converts only raised exceptions.
     The existing test passes only because the fixture's cloned worktree has no
     `.plan/execute-script.py` at all (`test_worktree_rebase_executor_refresh.py:60-91`).
  2. **The seam's own contract is over-stated** (gap G4): `_run_generate_executor`'s docstring
     promises *"never raises"* and `_refresh_worktree_executor`'s promises *"Every failure mode is
     reported in the return value and none is raised"*, yet the `try` at `:828-846` catches only
     `FileNotFoundError` and `subprocess.TimeoutExpired`. A `PermissionError` (or any other
     `OSError`) from `subprocess.run` propagates out of `cmd_worktree_rebase_to` at `:1709` — after
     `git rebase` has already succeeded and moved HEAD — which is precisely the outcome the
     "non-fatal by contract" reasoning exists to prevent.
  3. A third documented caller also drops the payload on the floor (gap G6).

### D4 — finalize prompt and log residue

- **Required (plan):** three items, *"each … either shipped or recorded as already-closed by D0."*
- **Claimed (report):** all three shipped; none was already-closed.
- **Found — all three, verbatim:**
  - **(a) Line-level simplify scope.** `phase-6-finalize/standards/finalize-step-simplify.md:139-146`
    inside the dispatched prompt body: *"Under {changeset} scope the boundary is LINE-level, not
    merely file-level… A line that is identical to its base-SHA content is PRE-EXISTING and out of
    scope — do not delete, rewrite, or 'tidy' it, even when it exhibits one of the anti-patterns
    below."* The § Scope semantics prose at `:69` names the file-vs-line split as what `changeset`
    and `artifact` differ by, as claimed.
  - **(b) Title-token repeat suppression.** `manage-status/scripts/_status_query.py:420-460`. The
    `changed` decision is taken inside `_apply_set` (`:435-439`), the log fires only under
    `if set_outcome['changed']` (`:451`), `set_at` is excluded from the comparison by construction,
    the write is never suppressed (`:440`), and `changed` is published on the payload (`:459`).
    Documented at `manage-status/SKILL.md:85` § "Title-token log emission is change-gated" and
    `standards/status-lifecycle.md:72`, whose "both verbs emit" wording is corrected to *"only when
    they change the stored value"*.
  - **(c) Bypass-before-dispatch rule.** `ref-code-quality/standards/code-organization.md:129-158`,
    § Guard Clauses → *"Place a bypass before the dispatch it guards"*, carrying the correctness
    argument (*"a mutation, a lock acquisition, a remote call, a consumed rate budget, an operator
    prompt"*) rather than only the efficiency one, as the report claims.
- **Verdict:** CONFIRMED, all three, no caveats.

### D5 — tests, each verified to FAIL pre-fix

- **Required (plan):** three tests, (a) reconciliation, (b) executor regeneration, (c) unchanged
  title token, each verified red pre-fix.
- **Claimed (report):** the three files exist with 15 / 6 / 7 tests and the listed pre-fix failures.
- **Found (counts re-derived at `61a43e5`, `grep -c "def test_"`):**
  | File | Tests now | Tests at `d2e94b4` |
  |---|---|---|
  | `test/plan-marshall/manage-execution-manifest/test_reconcile.py` | 19 | 19 |
  | `test/plan-marshall/workflow-integration-git/test_worktree_rebase_executor_refresh.py` | 10 | 10 |
  | `test/plan-marshall/manage-status/test_title_token_repeat_suppression.py` | 8 | 8 |
- **Checks run:** all three files together —
  `UV_PYTHON=3.12 uv run python -m pytest <3 files> -o addopts="" -q` → **`37 passed in 12.31s`**.
  Three mutation checks (below) each turn exactly one test red.
- **Pre-fix reds re-derived, not taken on trust.** Each landed test file was run against its own
  pre-fix production module (`git show d2e94b4^:<path>` installed over the file, then restored from a
  byte snapshot):
  | Test file | Against `d2e94b4^` code | Report's claim |
  |---|---|---|
  | `test_reconcile.py` | collection error — `AttributeError: module '_mem_reconcile' has no attribute 'cmd_reconcile'` | matches |
  | `test_worktree_rebase_executor_refresh.py` | `10 failed` — `AttributeError … _run_generate_executor` | matches (6 of 6 at the time; all 10 now) |
  | `test_title_token_repeat_suppression.py` | `7 failed, 1 passed` — `KeyError: 'changed'`; the pass is `test_suppressed_set_still_returns_the_record` | matches (6 of 7 at the time), including the named pre-existing pass |
- **Verdict:** CONFIRMED. The coverage is genuine, not decorative, and every pre-fix red the report
  claims reproduces. The report's per-file counts are stale against what landed (gap G10) — a
  bookkeeping defect, not a coverage one. One covering test is *unrepresentative* rather than
  vacuous — see gap G15 under D3.

## Correctness review

Read in full: `cmd_reconcile` and its helpers (`_live_phase_6_candidates`,
`_read_marshal_phase_steps`, `_read_merged_phase_6_step_map`, `_snapshot_step_params`,
`_sort_steps_by_frontmatter_order`, `_check_step_loadable`); the compose snapshot site and every
pre-filter/gate/lane call between it and the emitted list; `_run_generate_executor`,
`_refresh_worktree_executor`, `_executor_slot.py`, the `prepare_execute` re-export block, and the
`cmd_worktree_rebase_to` success path; `cmd_title_token` in both branches; `generate_executor.cmd_drift`
and `cmd_generate` far enough to establish the exit-code convention the probe depends on.

Defects found:

1. **The executor-refresh success verdict is a presence check the rebase population always
   satisfies.** `git-workflow.py:921` asks `executor_landed(worktree_executor_path(worktree_path))`,
   and `executor_landed` (`_executor_slot.py:38-59`) only asks whether a non-empty, non-symlink file
   is in the slot. `prepare_execute` puts one there at phase-5 move-in and self-heals it when it
   goes missing (`prepare_execute.py:253-262`, `:318-327`, `:598`), so in a real worktree the
   `not landed` branch (`:922-931`) is unreachable and a generation that wrote nothing reports
   `executor_regenerated: True`. Measured by seeding the fixture worktree's slot before the rebase:
   `True`, with `executor_detail: 'script set changed by the rebase; worktree executor regenerated'`
   over untouched bytes. `gen_rc` is no backstop — `generate_executor.py`'s `main` returns `0`
   unconditionally (`:2418-2419`) and a `generate` against an unresolvable `--marketplace-root`
   prints `status: error` at **RC=0** (measured). Gap G15.

2. **`_run_generate_executor` does not honour its "never raises" contract.**
   `git-workflow.py:828-846` catches `FileNotFoundError` and `subprocess.TimeoutExpired` only. Any
   other `OSError` from `subprocess.run` — `PermissionError` on a non-executable `python3`, `ENOMEM`,
   an inaccessible cwd — propagates through `_refresh_worktree_executor` (which has no handler) to
   `cmd_worktree_rebase_to:1709`. Consequence: a `git rebase` that already succeeded and moved HEAD
   surfaces to the caller as a crash, which is the exact failure mode `:867-870` argues must not
   happen ("converting a refresh failure into a rebase failure would make callers abort a rebase
   that worked"). Gap G4.

3. **The stale partition cannot fire for an external step.**
   `manage-execution-manifest.py:2957` calls `_check_step_loadable(step)`, which short-circuits every
   `project:` / `bundle:skill` id to `loadable: True` (`_manifest_validation.py:464-469`). So the
   `elif` at `:2960` is unreachable for external steps and they are always `retained`. A frozen
   `project:finalize-step-X` whose skill the plan deleted survives reconciliation untouched and fails
   later at dispatch — the confusing mid-dispatch failure Step 1.5 exists to convert into an
   actionable phase-entry error. Gap G1; the undocumented scope limit is gap G2.

4. **Backfill applies no composer logic.**
   `manage-execution-manifest.py:2998-3004`. The only filters are "absent from `composed_set`",
   "absent from `frozen_set`", and `_check_step_loadable(...)['loadable']`. The pre-filters, the
   ceremony gates, and `_apply_lane_resolution` are all skipped. `SKILL.md:448` promises reconcile
   *"never re-runs the decision matrix"* — true, but the promise is about not **re-adding** dropped
   candidates; nothing says a **new** candidate is admitted without any of the composer's narrowing,
   which is what happens. Gap G3.

5. **A non-string `phase_6.steps` entry is silently deleted by any successful `--apply`.**
   `manage-execution-manifest.py:2940` builds `frozen_steps` with
   `[step for step in frozen if isinstance(step, str)]`, and `:3010` then assigns
   `phase_6['steps'] = merged` where `merged` derives only from `frozen_steps`. Non-string entries
   never reach `merged` and are dropped without appearing in `stale[]` or the decision log. This
   directly contradicts the sibling choke point `_sort_steps_by_frontmatter_order`, which explicitly
   supports non-string entries as position pins (`_manifest_validation.py:390-393`). Only reachable
   on a hand-edited manifest, which `SKILL.md:450` explicitly sanctions. Gap G8.

6. **Step 1.5 enumerates two of `cmd_reconcile`'s four `status` outcomes.**
   `phase-6-finalize/SKILL.md:368-370` gives a branch for `success` and one for
   `error: unreconcilable_step`. The verb also returns `error: file_not_found`
   (`manage-execution-manifest.py:2917-2922`) and `error: invalid_manifest` (`:2926-2939`). The
   dispatcher is an LLM following prose, so an unenumerated error leaves it improvising at the
   phase-entry gate D1 argued must have a deliberately chosen direction — and the correct answer
   already exists fifteen lines above for the `read` call ("abort finalize with an explicit error").
   Gap G7.

Not defects (checked and cleared):

- **The indeterminate-drift bound is real and reachable**, not merely asserted by a stubbed test.
  Both generator verbs were run directly against a directory with no `marketplace/bundles`: `drift`
  prints `status: error / error: Could not read executor mappings` with no `drift_status` field, so
  the seam's `:889` guard maps it to `unknown` and never calls `generate`. And the explicit
  `--marketplace-root` anchor outranks the plugin cache for the `cache-first` scope
  (`script-shared/scripts/marketplace_paths.py:775-784`, which raises rather than falling back to a
  cache hit), so the probe cannot silently answer "did the worktree's script set change?" from the
  cached main checkout.

- Canonicalization is symmetric. `_live_phase_6_candidates` canonicalizes the live set (`:2866`);
  the stale test canonicalizes the frozen id (`:2960`); backfill canonicalizes both `composed_set`
  (`:2989-2993`) and `frozen_set` (`:2997`). The original id is what is written back (`:2967`
  appends `step`, not its canonical form), so a sanctioned `default:`-prefixed entry survives intact.
- `_snapshot_step_params` tolerates a `None` marshal map (`_manifest_rules.py:199-200`), so the
  params re-snapshot at `:3013-3019` cannot blow up on a CSV-fallback tree.
- `executor_landed` rejects a symlink correctly: `is_file()` follows the link and `is_symlink()`
  then excludes it (`_executor_slot.py:53-57`).
- The decision-log emission is genuinely inside the `--apply` guard (`:3008` opens the block,
  `:3027-3041` sit within it), so the F4 fix is real and not merely asserted.
- `_GENERATE_EXECUTOR_PATH` resolves to `skills/tools-script-executor/scripts/generate_executor.py`
  from `skills/workflow-integration-git/scripts/git-workflow.py` — three `.parent` hops is correct.

## Test adequacy

| Deliverable | Covering tests | Evidence of non-vacuity |
|---|---|---|
| D2 | `test_reconcile.py` (19) — drop, fail-loud, narrow backfill, canonicalization, fail-closed, converged no-op, compose snapshot | Mutation M2 (below) |
| D3 | `test_worktree_rebase_executor_refresh.py` (10) — drift/no-drift, noop skip, non-fatal, indeterminate, disk-derived verdict, argv/cwd seam shape, conflict path | Mutation M3 (below). ⚠ The disk-derived-verdict test is **non-vacuous but unrepresentative**: it holds only because the fixture worktree starts with an empty executor slot, which no real worktree does (gap G15) |
| D4b | `test_title_token_repeat_suppression.py` (8) — first set, repeat, state change, owner change, post-clear, aged-out, write-not-suppressed, payload | Mutation M1 (below) |
| D2 ordering | `test/plan-marshall/phase-6-finalize/test_manifest_loadability_guard.py` — `test_skill_md_reconciles_before_the_loadability_check` asserts `body.index(reconcile…) < body.index(…)`, plus `test_skill_md_names_the_unreconcilable_step_error` and `test_required_steps_md_documents_reconciliation_contract` | Narrative pins; read, not mutated |
| D4a, D4c | none | Prose-only deliverables; the plan required no test for them |

**Mutation sweep.** Snapshots of the three production files were written to
`/tmp/verify-190-mutsweep/*.orig` before any edit, each file was restored from its own snapshot
(never `git checkout`/`restore`/`stash`, which would have discarded three other agents' unstaged work
present in this tree), and `git status --porcelain <path>` was confirmed empty for all three
afterwards.

- **M1 — `_status_query.py:434`**, `previous = read_title_token(current)` → `current.get('title_token')`
  (i.e. revert the F10 staleness-aware fix). Result: `1 failed, 7 passed`;
  `TestRepeatSuppression::test_set_after_the_token_aged_out_emits_a_line_again` →
  `AssertionError: … assert False is True`. **Non-vacuous.**
- **M2 — `manage-execution-manifest.py:2960`**, `canonicalize_step_key(step) not in live_set` →
  `step not in live_set` (revert the F11 fix). Result: `1 failed, 18 passed`;
  `TestPrefixedFrozenIdsCompareCanonically::test_prefixed_frozen_step_is_not_dropped_when_live_lists_it_bare`
  → `assert 'success' == 'error'`. **Non-vacuous** — the canonical comparison is load-bearing and the
  test proves it.
- **M3 — `git-workflow.py:921`**, `landed = executor_landed(worktree_executor_path(worktree_path))`
  → `landed = True` (revert the F7 fix). Result: `1 failed, 9 passed`;
  `TestSuccessIsDerivedFromDiskNotExitCode::test_generation_exiting_zero_without_landing_a_file_is_not_success`
  → `AssertionError: no executor landed on disk … assert True is False`. **Non-vacuous.**

All three mutations were re-run independently during the adversarial review, from fresh byte
snapshots in `/tmp/adv-190-mutsweep/`, and reproduced exactly: `1 failed, 7 passed` / `1 failed,
18 passed` / `1 failed, 9 passed`, each naming the same test. `git status --porcelain` was empty for
all three files afterwards, and the three files together return to `37 passed`.

- **M4 (added by the adversarial review) — no source mutation; a *fixture* mutation.** Seeding
  `worktree_executor_path(worktree)` with a file before the rebase, then running the M3 scenario
  (`drift_status='drift'`, `lands_executor=False`) unchanged: the verb returns
  `executor_regenerated: True`. The production code is correct-as-written under M3 and wrong under
  M4, which is what makes M3 a non-vacuous test of an unrepresentative scenario. Gap G15.

One test gap: nothing drives an exception out of the `_run_generate_executor` seam.
`test_failed_generation_does_not_fail_the_rebase` exercises `generate_rc=1`, not a raise, so the
"non-fatal by contract" property is pinned only for the return-code path. Gap G5.

Beyond that I found no tautological or self-satisfying guard. Two tests I checked specifically for
vacuity and cleared: `test_compose_records_the_candidate_set_it_selected_from` states the exact
condition its subset assertion holds under and warns against generalizing (`test_reconcile.py:412-422`,
the N1 fix — present and honest); `test_live_generator_exposes_the_verbs_and_field_the_seam_relies_on`
places its `is_file()` guard before the `read_text()` (`:306-309`, the N2 fix — present).

## Report accuracy

Every claim `report-01.md` makes about the *code* held when I checked it: the four D0 verdicts (two
re-derived against `d2e94b4^`), the D1 split, the D2 mechanism and its four sub-claims, the D3 three
bounds and the non-fatal rationale, all three D4 items, the F1/F2/F3/F5/F6/F9/F12 doc fixes, and the
N1/N2/N3/N4 round-2 fixes. The out-of-scope list is clean: the merge commit's 23 files contain no
plugin-registry, step-emission, or boundary-ledger surface. The reviewer-participation section is
accurate — I read the PR's own surfaces and found `sourcery-ai[bot]`'s review body *"your pull
request is larger than the review limit of 150000 diff characters"*, `coderabbitai[bot]`'s
*"Review limit reached"* issue comment, and `cuioss-review-bot[bot]`'s *"PR contains tests / No
security concerns identified / No major issues detected"*, exactly as recorded.

Three bookkeeping claims are false against the landed diff:

1. `report-01.md:119` — *"`git diff --name-only origin/main...HEAD -- '*.py'` → **4 Python files
   changed**"*, followed by a four-item list and *"(plus three new test files.)"*.
   Re-derived with `git show --numstat --format="" d2e94b4 | grep '\.py$'`: **nine** `.py` paths —
   five production (the four listed **plus** the new
   `workflow-integration-git/scripts/_executor_slot.py`, +59) and four test (three new plus a
   **modified** `test/plan-marshall/phase-6-finalize/test_manifest_loadability_guard.py`, +51/−12).
   `_executor_slot.py` was created in the `c81aee6` round, i.e. after the figure was first recorded,
   and the figure was never re-derived. Gap G7.

2. `report-01.md:109-111` — the D5 table annotates the three files *"(15 tests)"*, *"(6 tests)"*,
   *"(7 tests)"*. What landed at `d2e94b4` is **19 / 10 / 8** (`git show d2e94b4:<file> | grep -c
   "def test_"`). The column header does say "Pre-fix failure observed", so the numbers are
   defensible as pre-fix snapshots — but they sit beside the file paths and read as the files'
   contents. The PR description's own *"32 tests across …"* is unambiguously wrong: the three files
   carry **37**. Gap G9.

3. `report-01.md:322` — *"(2053 insertions across 23 files)"* as the sourcery size-refusal basis.
   The PR reports `additions: 2115, deletions: 50, changed_files: 23`. The file count holds; the
   insertion count is stale by 62 (the refusal fired at `d1e6a37`, before the later fix rounds, so
   the figure was plausibly true when read and was not re-derived at report time). Gap G10.

One claim is **UNVERIFIABLE** here: *"`./pw verify` SUCCESS … 19693 passed, 14 skipped … 19702
passed, 14 skipped"*. Running the full gate is out of this audit's scope per the brief. Nothing I ran
contradicts it — the 37 tests in the three new files pass, and the two files I mutated returned to a
clean `git status`.

One claim I could not re-derive because the underlying artifact was edited after the fact: the
CodeRabbit narrative at `report-01.md:244` (*"Review failed — the head commit changed during the
review"*, and *"Next review available in: 56 minutes"*). The live comment body (updated 12:18:10Z)
now reads *"Next review available in: **53 minutes**"* and carries no "Review failed" text. Bots
rewrite their comments in place; this is not evidence against the report.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| D2's observation point owed — first plan composed after this merges, reaching Step 1.5 | **OPEN** | `grep -rn "reconcile --plan-id {plan_id} --apply" marketplace/bundles/` returns exactly one site (`phase-6-finalize/SKILL.md:364`), and nothing in the tree records a run that reached it. The `doc/plans/` lane never executes `phase-6-finalize`. Gap G11. |
| A cloud run neither performs nor owes `/sync-plugin-cache` | **MOOT** | Correct per `CLAUDE.md` § Standalone Plan Lane; no debt tracked. |
| `reconcile` is called from nowhere but Step 1.5; phase 5 has the same exposure with no snapshot | **OPEN** | `grep -rn "candidate_steps\|candidate_verification_steps"` under `manage-execution-manifest/` returns hits for `phase_6` only — `phase_5.verification_steps` has no candidate snapshot and no reconcile. Gap G12. |
| `coderabbitai`'s window reopens ~13:10 UTC; `@coderabbitai review` re-triggers | **MOOT** | PR merged 2026-08-15T12:49:53Z; no second opinion was sought. |
| `sourcery-ai` will refuse this PR at any size | **MOOT** | PR merged; the general observation (large plans lose this reviewer) is an epic-level note, not a tracked item. |
| Contract-change proposal open and unshipped | **PARTIALLY CLOSED** | `.claude/skills/cloud-plan-lane/SKILL.md:456-461` now carries the substance of the § Step 4 correction — *"changes the head mid-review, which aborts a bot's in-progress review **and consumes its rate window**"*. Neither proposed edit landed: no § Step 7 "land every known-pending bookkeeping edit before the review window opens" rule (`grep -n "bookkeeping"` finds only `:1131` and `:1580`, both unrelated), and no conditions-1-and-3 sequencing note at `:1424-1435` (where the report condition is now condition **4**, the document having been renumbered since). Gap G13. |
| `test_branch_cleanup_merge_queue_routing` guard predicate is interpreter-version-sensitive | **OPEN** | `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py:589` — `if token.type != tokenize.NAME or token.string == own_symbol`. Unchanged, pre-existing, still latent below Python 3.12. Gap G14. |

## Out-of-scope and collateral

Clean. The plan excluded four things; the landed diff touches none of them:

- **Step/dispatch emission arm** — no `record-step`, dispatch-emission, or step-completion surface in
  the 23 changed files.
- **Boundary-ledger arithmetic** — no `manage-metrics` / ledger / coverage-ratio file touched.
- **Plugin-registry pin inversion** — no registry, pin, or plugin-resolution file touched. The new
  code regenerates a per-tree derived executor after a rebase; it neither pins nor resolves a registry.
- **Hard-failing on manifest divergence** — the hard fail survives only for the `broken` half, which
  D1 explicitly chose, exactly as the out-of-scope entry permits.

Collateral beyond the plan's declared surface, all declared in the report and all defensible:

- `workflow-integration-git/scripts/prepare_execute.py` (+19/−21) and the new
  `_executor_slot.py` (+59) — the N3 de-duplication. The re-export aliases at `prepare_execute.py:234-235`
  preserve the monkeypatch surface, so `test_prepare_execute.py`'s direct
  `prepare_execute._executor_landed(...)` calls still bind to the same object.
- `ref-code-quality/standards/code-organization.md` (+32) — D4c's home; named in the plan.
- `tools-script-executor/SKILL.md` (+10/−…) — the F6 sibling-enumeration fix.
- `test/plan-marshall/phase-6-finalize/test_manifest_loadability_guard.py` (+51/−12) — the narrative
  pins the D2 heading rename broke, updated rather than reverted, with two *new* pins added
  (ordering, `unreconcilable_step`).

Nothing was changed without being declared.

## Method and coverage

**Checked.** Read `plan.md` and `report-01.md` in full, then located the merge commit
(`d2e94b4`, PR #1236) and read its file list. Read end-to-end: `cmd_reconcile`; the compose candidate
snapshot and every subtraction between it and the emitted list; `_live_phase_6_candidates`,
`_check_step_loadable`, `_sort_steps_by_frontmatter_order`, `_snapshot_step_params`,
`_read_merged_phase_6_step_map`; `_run_generate_executor`, `_refresh_worktree_executor`,
`_executor_slot.py`, the `cmd_worktree_rebase_to` success path, and enough of
`generate_executor.py` to establish the probe's exit-code and flag contract; `cmd_title_token` in
both branches. Read all three new test files in full plus the modified loadability-guard test's
assertion list. Read every documentation surface the report claims to have fixed
(`manage-execution-manifest/SKILL.md`, `manifest-schema.md`, `phase-6-finalize/SKILL.md`,
`required-steps.md`, `branch-cleanup.md`, `finalize-step-simplify.md`,
`finalize-step-sync-baseline.md`, `worktree-handling.md`, `tools-script-executor/SKILL.md`,
`manage-status/SKILL.md`, `status-lifecycle.md`, `code-organization.md`). Re-derived two D0 verdicts
against the `d2e94b4^` blobs. Ran the three test files (37 pass) and three targeted mutations.
Verified PR #1236's state, reviews, and comments through the GitHub MCP server.

**Search-negative control.** Before trusting *"`reconcile` has exactly one call site"*, I ran the
same grep pattern against `reconcile --plan-id {plan_id} [--apply]` and confirmed it matches the
documentation site in `manage-execution-manifest/SKILL.md:368` — so the pattern does find text where
text exists, and the single-hit result is a real count rather than a mis-typed filter.

**Not checked, and why.**

- **Full `./pw verify`.** Out of scope per the brief; the report's suite totals (19693 / 19702) are
  therefore UNVERIFIABLE from this audit.
- **The end-to-end finalize path.** `phase-6-finalize` Step 1.5 cannot be exercised here: this clone
  has no `.plan/` and no generated executor, and the lane that produced the plan never runs phase 6.
  D2's runtime behaviour rests entirely on the unit tests driving `cmd_reconcile` directly — which is
  what the report itself says, and which is why the observation point remains owed.
- **`generate_executor generate`'s actual write path.** The seam is stubbed in every test and I did
  not run the real generator against a worktree; the disk post-assertion is what makes that gap
  tolerable, and it is itself pinned (mutation M3).
- **Gap G4's exception path empirically.** I established it by reading the `except` clauses rather
  than by forcing a `PermissionError` out of `subprocess.run`, which would require making `python3`
  non-executable in this environment.
