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

Counts re-derived at the moment of writing: `grep -c '^def test_'` → 35 / 8 / 5 = 48; three `python3
-c` call sites in `generate_executor.py`, all argv-based; zero write operations
(`write_text|open(|mkdir|unlink|rmtree|os.replace`) in `_plugin_pin_trap.py`; zero references to
`_plugin_pin_trap` anywhere outside `test/` and `doc/plans/`.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | Derive the three stores and who writes each, by symbol | Writer of each store established from source; the "sync never writes the registry" claim confirmed at the sync entry point | yes | yes | yes | yes | `.claude/skills/sync-plugin-cache/scripts/sync.py:518` `main` → `:439` `_rsync_bundle` (writes `{cache_root}/{bundle}/{version}/` via rsync) and `:460` `_copy_dist_manifest` (writes `{cache_root}/dist-manifest.json`). `grep -n 'registry\|installPath\|config.json'` over that file → no hits. The report's own correction — that the executor half of the claim belongs to `generate_executor.generate_executor`, not `sync.py` — matches the source |
| D1 | Detector with the right oracle | Rejects all six shapes + eight named conjuncts | yes | mostly | **no** | mostly | `_plugin_pin_trap.py:308` `evaluate`, `:339` `_evaluate_single`. Gate on `executor == installPath` naming `GATE_FIELD='installPath'` (`:88`, `:355`); separate `installPath == version` conjunct (`:358`) — mutation-verified load-bearing; `_UNMARKED_DERIVED_NOTE` (`:90`); `ContentComparison.render()` (`:179`); `_volatile_signature` double-sample (`:290`); `indeterminate` distinct (`:77`, `:426-433`); instant/population/marker-age published (`:446-450`); divergence vs GC-exposure as separate tuples (`:350-351`). **Defects:** G1 (unreadable/empty source dir → PASS "content matches source"), G2 (`partial` unreachable from the adapter), G3 (content excluded from the double-sample signature), G4 (literal shape-3 tree passes) |
| D2 | Mid-run assertion a loaded body came from the pin | Fails closed and says which version it got | yes | yes | yes | yes | `_plugin_pin_trap.py:489` `assert_loaded_version` → `LoadedVersionVerdict(outcome=fail, got_version=…)`; unparseable path → `indeterminate` (`:499`). Tests at `test_plugin_pin_trap.py:229,237,243` (3, as the report states) |
| D3 | Operator-facing remedy stated, not implied | Remedy text explicit | yes | yes | yes | yes | `REMEDY_OPERATOR` (`:115`), `REMEDY_NO_RESTART` (`:123`), `REMEDY_IN_RUN_TEMPLATE` (`:127`), `REMEDY_RESAMPLE` (`:131`), assembled by `_fail_remedy` (`:456`). Asserted at `test_plugin_pin_trap.py:252` |
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
`4ac41326`: the selector then partitioned on `.orphaned_at` via `_partition_version_dirs`, and
`max(live)` still equalled the newest-on-disk dir, so the mirror matched. It no longer describes
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

One post-landing change to this plan's files: `7cadb986` (PR #1272) adjusted the module-loading
preamble of `test_pin_trap_executor_reachability.py` as part of a repo-wide test-hygiene sweep. It
changes no assertion.

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
