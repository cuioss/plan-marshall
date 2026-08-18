# Verification — 320 the plugin pin trap (build the detector, and give it an oracle that can actually fail)

**Verified against:** commit `2402b02bf5bc64b5ece468b6d2a3e884b5f0b30d`   **Landed as:** PR #1213, commit `4ac413261cac8f46b16994008f339af1e26a6140`   **Verdict:** implemented-with-gaps

## Method

Files read in full: `plan.md`, `report-01.md`,
`marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py` (735 lines),
`test/pm-plugin-development/plugin-doctor/test_plugin_pin_trap.py`,
`test/plan-marshall/tools-script-executor/test_pin_trap_executor_reachability.py`,
`test/plan-marshall/tools-input-validation/test_router_flag_placement.py`.
Read in part: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py`
(the three D5 sites plus `cmd_drift`/`discover_scripts`),
`marketplace/bundles/plan-marshall/skills/tools-input-validation/scripts/input_validation.py` (D6),
`marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_bundles.py`
(`select_live_version_dir`, `resolve_bundle_path`, `collect_script_dirs`) at HEAD **and** at `4ac41326`,
`.claude/skills/sync-plugin-cache/scripts/sync.py` (`main`, `_rsync_bundle`, `_copy_dist_manifest`).

Landed diff established with `git log --grep '#1213'` → `4ac41326`; `git show -M --name-status 4ac41326`
(8 paths: 1 rename, 4 additions, 2 modifications, 1 report). Later history checked with
`git log 4ac41326..HEAD -- <path>` for every touched file.

Commands executed (all from the repo root):

- `uv run python -m pytest <the three new test files> -o addopts="" -q` → **48 passed** (0.46s).
- `uv run python -c ...` importing `_plugin_pin_trap` directly and **executing** the oracle on
  constructed inputs — four separate probes (loader marker-sensitivity over all 16 mark
  combinations; `compare_pin_content` against a pin missing files; `compare_pin_content` against a
  nonexistent source dir; `evaluate` with samples that differ only on the content axis; `evaluate`
  on the literal shape-3 configuration).
- **Mutation check 1** (`generate_executor.py`, byte-snapshot taken to the scratchpad first,
  `git diff --quiet` confirmed clean before mutating): reverted `except (Exception, SystemExit)` to
  `except Exception` **and** the precise `test_`/`_test` filter to the bare `'test' in name.lower()`
  substring → `test_pin_trap_executor_reachability.py` went **2 failed, 3 passed** (both the
  SystemExit-reaches-fallback test and the `latest.py`-kept test go RED). File restored from the
  saved bytes; `git diff --quiet` clean afterwards.
- **Mutation check 2** (`_plugin_pin_trap.py`, same snapshot/restore discipline): disabled the
  separate `installPath == version` conjunct (turning the oracle pairwise) →
  `test_negative_control_two_agree_third_disagrees_must_fail` went RED reporting `pass`, together
  with `test_shape5_registry_two_fields_disagree`. File restored; `git diff --quiet` clean.

Counts re-derived at the moment of writing: `grep -c '^def test_'` → 35 (detector) / 5 (executor
reachability) / 8 (router flag) = 48; three `python3
-c` call sites in `generate_executor.py`, all argv-based; zero write operations
(`write_text|open(|mkdir|unlink|rmtree|os.replace`) in `_plugin_pin_trap.py`; zero references to
`_plugin_pin_trap` anywhere outside `test/` and `doc/plans/`.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | Derive the three stores and who writes each, by symbol | Writer of each store established from source; the "sync never writes the registry" claim confirmed at the sync entry point | yes | yes | yes | yes | `.claude/skills/sync-plugin-cache/scripts/sync.py:518` `main` → `:439` `_rsync_bundle` (writes `{cache_root}/{bundle}/{version}/` via rsync) and `:460` `_copy_dist_manifest` (writes `{cache_root}/dist-manifest.json`). `grep -n 'registry\|installPath\|config.json'` over that file → no hits. The report's own correction — that the executor half of the claim belongs to `generate_executor.generate_executor`, not `sync.py` — matches the source |
| D1 | Detector with the right oracle | Rejects all six shapes + eight named conjuncts | yes | mostly | **no** | mostly | `_plugin_pin_trap.py:308` `evaluate`, `:339` `_evaluate_single`. Gate on `executor == installPath` naming `GATE_FIELD='installPath'` (`:88`, `:355`); separate `installPath == version` conjunct (`:358`) — mutation-verified load-bearing; `_UNMARKED_DERIVED_NOTE` (`:90`); `ContentComparison.render()` (`:179`); `_volatile_signature` double-sample (`:290`); `indeterminate` distinct (`:77`, `:426-433`); instant/population/marker-age published (`:446-450`); divergence vs GC-exposure as separate tuples (`:350-351`). **Defects:** G1 (unreadable/empty source dir → PASS "content matches source"), G2 (`partial` unreachable from the adapter), G3 (content excluded from the double-sample signature — `high`), G4 (literal shape-3 tree passes), G8 (a pin that is a strict superset of source reads as a clean match), G10 (no adapter produces the two samples the double-sample conjunct requires) |
| D2 | Mid-run assertion a loaded body came from the pin | Fails closed and says which version it got | yes | yes | yes | yes | `_plugin_pin_trap.py:489` `assert_loaded_version` → `LoadedVersionVerdict(outcome=fail, got_version=…)`; unparseable path → `indeterminate` (`:499`). Tests at `test_plugin_pin_trap.py:229,237,243` (3, as the report states) |
| D3 | Operator-facing remedy stated, not implied | Remedy text explicit | yes | yes | yes | **mostly** | `REMEDY_OPERATOR` (`:115`), `REMEDY_NO_RESTART` (`:123`), `REMEDY_IN_RUN_TEMPLATE` (`:127`), `REMEDY_RESAMPLE` (`:131`), assembled by `_fail_remedy` (`:456`). Asserted at `test_plugin_pin_trap.py:252`. **Defect:** G9 — step (3) of `REMEDY_OPERATOR` is the bare phrase "regenerate the executor", the only one of the three steps naming no invocable surface, and it is not covered by step (1) (`sync-plugin-cache/SKILL.md:131` names `/marshall-steward` executor regeneration as a *sister* surface) |
| D4 | Settle the loader's behaviour under two unmarked dirs, from the loader's selection code | Answer established from the selector | yes | **no** | partly | **no** | `_plugin_pin_trap.py:269` `loader_selected_version`. Executed over all 16 mark combinations of 4 dirs: **0 of 16 marker-sensitive** — the `live`/`pool` filtering is provably dead, the function is `max(dirs, key=_version_key)`. Its docstring still describes a retention-pin/unmarked-set mirror that `select_live_version_dir` no longer performs (superseded by #1223) and it omits the real `is_candidate` predicate — see G5, G6 |
| D5 | Three executor reachability fixes, ordering honoured | All three fixed together | yes | yes | yes | yes | `generate_executor.py:1931` `except (Exception, SystemExit)`; `:394` `stem.startswith('test_') or stem.endswith('_test')`; `:1598`, `:1629`, `:1668` all pass paths through argv. Both coupled fixes are in the same commit `4ac41326`. `discover_scripts` exits via `sys.exit(2)` (`:295`) and the sibling `cmd_drift` catches `SystemExit` (`:2123`) — both plan claims confirmed by symbol. Mutation check 1 turned both guards RED |
| D6 | Argparse rejection names a misplaced router flag | Rejection says "this flag exists but belongs before the verb" | yes | yes | yes | yes | `input_validation.py` `_root_router_option_strings`, `_augment_misplaced_router_flag`, wired into `parse_args_with_toon_errors`'s `toon_error` (replacing the bare `orig(message)`). Exit code 2 preserved. 8 tests, incl. the negative case (genuinely-unknown flag gets no note). Reaches a real router: `manage-architecture/scripts/architecture.py:458` calls `parse_args_with_toon_errors` |
| D7 | Tests, each verified to fail pre-fix | All six pass, each seen red first | yes | mostly | mostly | partly | 48 tests, all green. (a) six shapes + shape-6-vs-shape-1; (b) healthy passes; (c) non-pinned load; (d) disagreeing samples → indeterminate; (e) negative control — **mutation-verified non-vacuous**; (f) SystemExit → glob fallback keeping `latest.py` — **mutation-verified non-vacuous**. Weak spot: `test_content_comparison_partial_scan_says_so` constructs `ContentComparison` directly, and the state it asserts is unreachable from `compare_pin_content` (G2) |

**D1.** `_evaluate_single`'s outcome ladder (`_plugin_pin_trap.py:405-437`) is `fail → could-not-look
→ content-not-compared → pass`, which is right in shape. What breaks it is the content adapter:
`compare_pin_content` (`:637`) enumerates `source_dir.rglob('*')`, and a source dir that is absent
or empty yields `total=0, diverged=0`, which the oracle reads as a satisfied content conjunct and
reports as `pass` with reason *"all three stores agree and the pin content matches source"*
(executed — see G1). Separately, `scanned + unreadable == total` holds by construction, so the
`scanned` value handed to `ContentComparison` never satisfies `partial`, and the honest-degradation
path exists only on the dataclass (G2). And `_volatile_signature` (`:290`) omits `obs.content`, so
two samples that disagree only on the content axis produce a confident `fail` rather than
`indeterminate` — the false-FAIL direction the plan singles out as the dangerous one (G3).

**D1 / shape 3.** The implemented condition is `len(unmarked) >= 2 and loader != installPath`
(`:381`). The literal configuration the plan's table names — `unmarked == [stale, pin]` with a
*correct* (newest) pin — evaluates to `pass` (executed). The implemented shape 3 therefore fires
only in the mirror-image tree, where a non-pin dir sorts *higher* than the pin, which is what the
test fixture at `test_plugin_pin_trap.py:111` encodes. The reinterpretation may well be the right
call given newest-wins selection, but it is nowhere disclosed and the report states the oracle
"rejects all six shapes" (G4).

**D4.** The question the plan asked ("with two unmarked, which does the loader follow?") was
answered against `marketplace_bundles.select_live_version_dir` — this repository's *script-path
resolver*, not Claude Code's skill loader, whose selection code is not in this clone. Within that
substitution the answer given (newest version-key wins) is correct, and was correct at
`4ac41326`: the selector then partitioned on `.orphaned_at` via `_partition_version_dirs`, and —
*for a pool in which every dir is eligible, which is the only pool the marker-free mirror can
represent* — `max(live)` still equalled the newest-on-disk dir, so the mirror matched. (At
`4ac41326` the retention pin was `max(version_dirs)` while `live` was drawn from `eligible`, so the
real selector's marker filtering *could* bite whenever `is_candidate` excluded the newest dir —
which is the same omission G5 names.) It no longer describes
anything: PR #1223 (`d01edfdf`, 3h45m after this plan landed) rewrote the selector to
newest-*eligible*-wins with no marker read at all and deleted the sole `.orphaned_at` writer under
our tree (G6). The mirror also drops `is_candidate`, and the report's caveat about that omission is
wrong in a load-bearing way (G5).

## Report accuracy

Re-derived and **confirmed**:

- "48 new tests, all green" — `grep -c '^def test_'` gives 35 + 8 + 5 = 48; pytest reports 48 passed.
- D1 "35 detector tests", D2 "3 tests", D5 "5 tests", D6 "8 tests" — all exact.
- "all three `-c` sites fixed" — exactly three `'-c'` call sites remain in `generate_executor.py`
  (lines 1598, 1629, 1668) and none interpolates a path into the source string.
- "the sibling reader `cmd_drift` already catches `SystemExit`" — `generate_executor.py:2123`.
- "(1)+(2) in the same commit" — both hunks are in `4ac41326`.
- D0's symbol-level account of `sync.py` (and its explicit correction of the plan's organising claim,
  that the *executor* half belongs to a different symbol) — matches the file.
- "this detector writes nothing" — no write call of any kind in `_plugin_pin_trap.py`.
- Findings table item 1 (the `test-compile` mypy slip) is consistent with `5afcdcb` being a separate
  fix commit on the branch.

**Contradicted:**

1. The non-blocking caveat — *"`loader_selected_version` omits the real selector's `is_candidate`
   predicate, so it diverges only in the practically-unreachable case where the newest-on-disk dir
   lacks `skills/`"* — is wrong. `skills/` is only `collect_script_dirs`' predicate
   (`marketplace_bundles.py:176`). `resolve_bundle_path` (`:135`) passes
   `lambda d: (d / subpath).exists()`, a **per-request** predicate, so the selector resolves to an
   *older* dir whenever the newest one lacks the specific subpath being resolved. That is a routine
   condition (a script added, renamed, or moved between versions), and it is the only mechanism in
   this repository by which a resolution can go *backward* — i.e. the mechanism the plan's own
   problem statement describes. See G5.
2. The D4 row's description of the model — *"newest version-key among the live set (unmarked ∪
   retention-pinned newest, whose marker is ignored)"* — describes code that does nothing: the
   retention pin is by construction the maximum of the live set, so the marker filtering cannot
   change the result (0 of 16 mark combinations diverge from plain `max`). Harmless at the time,
   actively misleading now that #1223 removed marker consultation from the mirrored selector (G6).
3. The D7 row's "SATISFIED" for the honest-degradation conjunct is not supported at the adapter
   level: the only partial-scan assertion constructs the dataclass by hand, and no input to
   `compare_pin_content` can produce `partial=True` (G2).

Not re-derivable from the tree (historical build-log claims, recorded as such rather than as
contradictions): "mypy … 397 source files", "730 test files", "2370 passed locally", the reviewer
participation table, and the "seen red first" narrative for tests other than the two families I
mutation-checked myself.

## Out-of-scope compliance

Clean. `git show -M --name-status 4ac41326` lists exactly eight paths: the plan-file rename into its
plan directory, the new `report-01.md`, `input_validation.py` (D6), `generate_executor.py` (D5), the
new detector, and three new test files. No file outside the plan's Expected surface was touched, no
`doc/plans/` bookkeeping outside this plan's own directory, and no registry write of any kind — the
detector contains no filesystem write call at all, honouring the plan's hardest ⛔. `.plan/` was not
touched. The repair-the-live-machine and age-heuristic exclusions were both honoured
(`newest_marker_age_seconds` is carried on `StoreObservation`/`Verdict` and is never read by the
oracle — grep confirms it appears only at assignment/reporting sites).

## Residue carried forward

| Report residue | Status in today's tree |
|---|---|
| The detector is a library + adapters, not wired into a live gate or a plugin-doctor rule | **Still open.** `grep -rn '_plugin_pin_trap\|plugin_pin_trap'` outside `test/` and `doc/plans/` returns nothing — no production import, no rule-catalog entry, no `plugin-doctor/SKILL.md` mention. The module's leading `_` also excludes it from executor discovery, so there is no way to invoke it |
| No live cache/registry/executor measurement attempted (STOP CONDITION) | Honoured, and correctly declared. Nothing in the landed code or tests reads `~/.claude/plugins/` |
| Step-9 contract-change proposal (build gate must run full `./pw verify`) awaiting operator decision, to ship as a separate `chore/` PR | **Closed.** Accepted and shipped as PR #1218 (`8bb94b29`), touching only `.claude/skills/cloud-plan-lane/SKILL.md` (+11 lines) — exactly the shape the report promised |

One post-landing change to this plan's files: `7cadb986` (PR #1272) adjusted
`test_pin_trap_executor_reachability.py` as part of a repo-wide test-hygiene sweep — it switched the
module-loading preamble to `conftest`'s `MARKETPLACE_ROOT`/`PROJECT_ROOT`, replaced a hard-coded
five-entry `shared_dirs` list with `_gen.get_shared_module_dirs(MARKETPLACE_ROOT)`, and **added** a
vacuity guard (`assert shared_dirs, 'no shared module dirs resolved; the stub would be vacuous'`).
It weakens no assertion and strengthens one. (The earlier reading here, "changes no assertion", was
too weak: an assertion was added.)

## What could NOT be verified

- **The plan's live measurements** (the dozen-plus incidents, "352 of 360 files", "14 of 14
  entries", the marker-timestamp observations). The plan itself declares these unreachable from a
  clone and forbids attempting them. Unverifiable by design, and correctly treated as motivation.
- **Whether `select_live_version_dir` is "the loader"** the plan's D4 means. Claude Code's skill
  loader — the thing that announces a base directory when a `Skill:` body is loaded — has no source
  in this repository. D4's answer was established against this repo's script-path resolver instead.
  That substitution is reasonable (nothing better exists here) but it is undisclosed in the report,
  and it means D4's *Done when* ("established from the loader's selection code") is met only for a
  proxy.
- **"Seen red first"** for the D1/D2/D3 detector tests. The module is new, so there is no pre-fix
  state to run them against. I mutation-checked the two guards where a pre-fix state does exist
  (D5) plus the negative control (D7e); the rest is asserted, not diff-reproducible — which the
  report itself already concedes.
- **The build-gate figures** in the report (mypy source/test file counts, the 2370-test local run).
  Re-running the full gate was out of proportion to this check; the three new test files were run
  and pass.
- **D6 end-to-end through a real router process.** `architecture.py` cannot be imported standalone
  without the generated executor's PYTHONPATH (`ModuleNotFoundError: file_ops`), which the
  standalone-plan lane does not have. Verified instead by symbol (the call site at
  `architecture.py:458`) and by the end-to-end unit test over an equivalently-shaped parser.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every `high` gap, every clean-pass deliverable row, and every "swept, clean" claim, by
re-execution rather than re-reading:

- **Re-ran the suite**: `uv run python -m pytest <the three new test files> -o addopts="" -q` →
  **48 passed** (0.39s). Re-derived the per-file counts with `grep -c '^def test_'` → 35 / 5 / 8.
- **Re-executed the oracle** against constructed inputs (a fresh probe, not this document's):
  `compare_pin_content` against a nonexistent *and* an empty `source_dir`; a pin missing 2 of 5
  files; two samples differing only on `content`; the literal shape-3 tree; all 16 mark combinations
  of four version dirs; a version-split executor; a registry pin naming a deleted dir; a pin that is
  a strict superset of source; and `evaluate(obs, obs)` with the same object passed twice.
- **Independent mutation 1** (`input_validation.py`, `git diff --quiet` clean first, byte snapshot to
  the scratchpad, restored from those bytes, `git diff --quiet` clean after): made
  `_augment_misplaced_router_flag` return its argument unchanged → **3 failed, 5 passed**
  (`test_augment_names_router_flag_belongs_before_verb`, `test_augment_handles_equals_form`,
  `test_router_flag_after_verb_is_rejected_with_helpful_note`). D6's row is non-vacuous.
- **Independent mutation 2** (`_plugin_pin_trap.py`, same discipline): disabled the
  `installPath == version` conjunct → **2 failed, 33 passed**
  (`test_negative_control_two_agree_third_disagrees_must_fail` at `test_plugin_pin_trap.py:186`, and
  `test_shape5_registry_two_fields_disagree`). This reproduces the original mutation check 2
  independently; the plan's most important test (D7e) bites.
- **Broader sweeps than the originals.** Write operations in `_plugin_pin_trap.py` re-swept with
  `write_text|write_bytes|open\(|mkdir|unlink|rmtree|os.replace|shutil|touch\(|rename|symlink|chmod|copy|remove|\.write\(|subprocess|os.system`
  → **zero**. `_plugin_pin_trap` references re-swept case-insensitively as `pin.trap|pin_trap|PinTrap`
  across the whole tree → only the module's own docstring plus `.pytest_cache`; the "not wired"
  residue holds. The `python3 -c` sweep re-run as `subprocess.run|subprocess.Popen|os.system|check_output`
  → four call sites in `generate_executor.py` (`:308`, `:1597`, `:1628`, `:1667`); the first is the
  inventory scan (argv), the other three are the `-c` sites, all argv-based. `sync.py` re-swept
  case-insensitively for `registry|installPath|config.json|~/.claude|expanduser|home()` plus every
  write verb → its only writes are the per-bundle rsync into `{cache_root}/{bundle}/{version}/`
  (`:443`, `:445`) and `shutil.copyfile` of `dist-manifest.json` into the cache root (`:487`, `:490`).
- **Line references re-derived**, all exact: `_plugin_pin_trap.py` `:77 :88 :90 :115 :123 :127 :131
  :142 :179 :269-287 :290 :308 :339 :381 :420-437 :456 :489 :616 :637 :673`;
  `marketplace_bundles.py:135` and `:176`; `generate_executor.py:295 :394 :1598 :1629 :1668 :1931
  :2123`; `sync.py:439 :460 :518`; `architecture.py:458`; `test_plugin_pin_trap.py:111 :229 :237
  :243 :252 :320`.
- **Commits re-derived**: `4ac41326` = 8 paths, timestamped 2026-08-13 17:33:22Z; `d01edfdf`
  (PR #1223) 2026-08-13 21:18:03Z → **3h44m41s** later ("3h45m" holds); `8bb94b29` (PR #1218) is
  `.claude/skills/cloud-plan-lane/SKILL.md`, **+11 lines**, one file; `7cadb986` (PR #1272) diff read
  in full; `2402b02b` is an ancestor of HEAD and **no** source file this verification cites has
  changed between them, so every finding below applies at HEAD.
- **D6 reaches a real router** re-confirmed by symbol: `architecture.py:31-37` declares `--project-dir`
  and (via `add_plan_id_arg`) `--plan-id` on the root parser ahead of `add_subparsers`, and `:458`
  calls `parse_args_with_toon_errors`.
- **D3's remedy targets re-confirmed to exist**: `marshall-steward/scripts/cache_retention.py`
  declares a `sweep` subparser (`:358`); `.claude/skills/sync-plugin-cache/` exists.

**Not re-checked** (unchanged from the "What could NOT be verified" section, plus): the build-gate
figures (397 source files, 730 test files, 2370 local tests); the reviewer-participation table; the
"seen red first" narrative for the D1/D2/D3 detector tests; the plan's live measurements; D6 driven
through a real `architecture.py` process. Additionally **not** re-mutated: the D5 guards (mutation
check 1) — I confirmed both fixes by symbol (`generate_executor.py:1931`, `:394`) and read the two
tests, but did not re-run that mutation, since mutation budget went to D6, which the original review
had not mutated at all.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | Empty/unreadable `source_dir` → `pass` "content matches source"; `high` | **upheld** | Re-executed: nonexistent *and* empty `source_dir` both give `ContentComparison(0,0,0)`, `render()` = `'0 of 0 files match; 0 diverge'`, `evaluate` → `outcome='pass'` |
| G2 | `partial` unreachable from `compare_pin_content`; `medium` | **upheld, figures corrected** | Re-executed with a pin missing 2 of 5: `ContentComparison(matched=3, total=5, diverged=2, scanned=5)`, `partial=False`. The recorded `matched=2 / diverged=3` described a pin missing *three* of five; the conclusion is unchanged. Also confirmed the `except OSError` return (`total=0, scanned=0`) is non-partial |
| G3 | Content axis omitted from `_volatile_signature`; `medium` | **re-severitied → `high`** | Re-executed: samples differing only on `ContentComparison(352,360,8)` vs `(360,360,0)` → `outcome='fail'`. `evaluate`'s own docstring promises `indeterminate` on disagreement, so this is a documented-contract violation producing a false FAIL — the direction the plan ranks as the more dangerous, because it acts. Same rank as G1 |
| G4 | The literal `[stale, pin]` tree passes; `medium` | **upheld** | Re-executed: `version_dirs=(VersionDir('0.1.100',False), VersionDir('0.1.200',False))`, `installPath='0.1.200'`, all else agreeing → `outcome='pass'`, `shapes=()`, no divergence, no GC exposure |
| G5 | The report's `is_candidate` caveat is wrong; backward resolution is routine; `medium` | **upheld and strengthened** | `marketplace_bundles.py:135` = `lambda d: (d / subpath).exists()`, `:176` = `lambda d: (d / 'skills').is_dir()` — both exact. **New:** the report also says the omission is "documented in the module"; `grep -n 'is_candidate\|candidate'` over `_plugin_pin_trap.py` returns **nothing**, so no such caveat exists there. G5's *Fix* was rewritten from "update the caveat" to "add the paragraph", which is what an implementer can actually carry out |
| G6 | `live`/`pool` filtering is dead; docstring superseded by #1223; `medium` | **upheld** | Re-executed over all 16 mark combinations of four dirs → **0 diverge** from plain `max(dirs, key=_version_key)`. `d01edfdf` confirmed at 3h44m after `4ac41326`; the current `select_live_version_dir` reads no marker (`marketplace_bundles.py:16-58`); `grep -rn 'orphaned_at'` outside `test/` and `doc/plans/` finds only read-side documentation and the detector — no production writer remains |
| G7 | Version-split executor filed as `could not look`; `low` | **upheld** | Re-executed: an executor embedding `0.1.100` and `0.1.200` → `read_executor_anchored_version` returns `None`, `evaluate` → `indeterminate: could_not_look: executor`. `low` is right: nothing green ships |
| G8 | *(new)* Pin as a strict superset of source reads as a clean match | **added, `medium`** | Re-executed: source of 3 files, pin holding those 3 plus a retired `retired_flag.py` → `'3 of 3 files match; 0 diverge'`, `evaluate` → `pass`. `compare_pin_content` walks only `source_dir.rglob('*')` (`:648`) |
| G9 | *(new)* `REMEDY_OPERATOR` step (3) names no command | **added, `low`** | `:120` is the bare phrase "regenerate the executor"; steps (1) and (2) name `/sync-plugin-cache` and `plan-marshall:marshall-steward:cache_retention sweep`. `sync-plugin-cache/SKILL.md:131` shows the sync does **not** regenerate the executor |
| G10 | *(new)* No adapter produces the two samples | **added, `low`** | `observe()` (`:677`) returns one observation; `__all__` exposes no paired variant; `evaluate(obs, obs, ...)` → `pass`. Overlaps but is not identical to the report's declared "not wired into a live gate" residue |
| D0 clean pass | "sync writes cache, never the registry", by symbol | **upheld** | Re-swept `sync.py` case-insensitively for every write verb and for `registry\|installPath\|config.json\|~/.claude\|expanduser\|home()` — a broader pattern than the original. Only writes: `_rsync_bundle` (`:439`, `dest_dir.mkdir` + rsync) and `_copy_dist_manifest` (`:460`, `cache_root.mkdir` + `shutil.copyfile`). No registry path exists |
| D2 clean pass | Fails closed, names the version it got | **upheld** | `assert_loaded_version` re-read at `:489`; three tests at `:229 :237 :243`; the unparseable path returns `indeterminate`, not a verdict |
| D3 clean pass | Remedy explicit | **re-scored: Complete? yes → mostly** | See G9. The row's other four columns stand |
| D5 clean pass | Three fixes, ordering honoured | **upheld** | All five sites re-derived by symbol; `discover_scripts` exits `sys.exit(2)` (`:295`), `cmd_generate` catches `(Exception, SystemExit)` (`:1931`), the sibling `cmd_drift` catches `SystemExit` (`:2123`), the glob filter is `startswith('test_') or endswith('_test')` (`:394`), and the broader `subprocess.*` sweep finds no fourth interpolating site. Both coupled hunks in `4ac41326`. Not re-mutated — see "Not re-checked" |
| D6 clean pass | Rejection names a misplaced router flag | **upheld, mutation-verified** | Independent mutation → 3 tests RED. Root-parser router flags confirmed at `architecture.py:31-37`; call site at `:458` |
| D7 | 48 tests, (e) and (f) non-vacuous | **upheld** | 48 passed re-run; (e) re-mutated independently and goes RED; the `test_content_comparison_partial_scan_says_so` weak spot re-confirmed at `:320` (constructs `ContentComparison(..., scanned=110)` by hand) |
| Verdict | `implemented-with-gaps` | **upheld** | Every deliverable row scores `Implemented? = yes`; none is absent. D1 is `Correct? = no` and D4 is `Complete? = no`, which is the definition of implemented-**with-gaps** rather than partially-implemented |
| "writes nothing" | No filesystem write in the detector | **upheld** | Re-swept with a materially broader verb set (adds `shutil`, `subprocess`, `os.system`, `rename`, `symlink`, `chmod`, `copy`, `remove`, `.write(`) → zero hits |
| "not wired" residue | Zero references outside `test/` and `doc/plans/` | **upheld** | Re-swept case-insensitively as `pin.trap\|pin_trap\|PinTrap` — broader than the original literal — over the whole tree. Only the module itself and `.pytest_cache` |
| `7cadb986` "changes no assertion" | Post-landing edit is inert | **rewritten** | The diff replaces a hard-coded five-entry `shared_dirs` list with `_gen.get_shared_module_dirs(MARKETPLACE_ROOT)` and **adds** `assert shared_dirs, 'no shared module dirs resolved; the stub would be vacuous'`. It strengthens the test; "changes no assertion" was too weak |

**Documents corrected.** In `gaps.md`: G3 re-severitied `medium` → `high` with a stated rationale;
G2's executed figures re-derived and corrected; G5's *Where* and *Fix* rewritten (the module carries
no `is_candidate` caveat, so the fix is to **add** the paragraph and it now names
`resolve_bundle_path`'s predicate and its line); G8, G9 and G10 added; a
`## Refuted during adversarial review` section added recording that **nothing** was refuted and by
what means each of G1-G7 was re-checked; **Open items** 7 → 10. In `verification.md`: the D1 row's
defect list extended with G3's new severity, G8 and G10; the D3 row's *Complete?* lowered from `yes`
to `mostly` with G9 named; the test-count ordering corrected to 35 / 5 / 8; the D4 historical
sentence about `max(live)` qualified (at `4ac41326` the retention pin was drawn from all version
dirs while `live` was drawn from `eligible`, so the real selector's marker filtering *could* bite —
the mirror's dead-code finding survives only because the mirror has no eligibility predicate at all);
the `7cadb986` sentence corrected; this section appended. The headline verdict is **unchanged**.

**Residual doubt** — what a third reviewer should look at first:

1. **G8 and G1 are the same conjunct failing from two sides**, and a fix for one can mask the other.
   Whoever implements them should implement them together and assert the union-denominator and the
   zero-file cases in one test, or the second fix will be validated by the first.
2. **`read_registry_entry`'s liberal shape-guessing** was not exercised against a real registry — it
   accepts three different nestings and the plan declares the real file unreachable from a clone. If
   the plugin manager's actual shape is a fourth, the reader returns `(None, None)` and the detector
   reports `indeterminate` forever. That is fail-safe, but it means the detector may never issue a
   verdict on the machine it was built for, and nothing here can tell.
3. **`compare_pin_content` has no exclusion set** — it hashes `__pycache__`, `.pyc` and any other
   build residue under `source_dir`. On a real repository checkout that is a large and permanently
   divergent file population, which could drown the eight-file signal the plan measured. Not filed as
   a gap because no caller exists to establish what `source_dir` will actually be pointed at.
4. **The D5 mutation was not re-run** here. The original review's mutation check 1 is the only
   evidence that the two coupled executor guards bite, and it is single-sourced.

