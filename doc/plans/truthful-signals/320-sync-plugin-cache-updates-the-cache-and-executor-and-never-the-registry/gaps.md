# Gaps — 320 the plugin pin trap (build the detector, and give it an oracle that can actually fail)

**Source:** verification.md (same directory)   **Open items:** 7

## G1 — Stop `compare_pin_content` from reporting an unlooked-at content axis as a clean match

- **Kind:** bug
- **Severity:** high
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py:637` — `compare_pin_content`, consumed by `_evaluate_single`'s outcome ladder at `:430-437`
- **What is wrong:** the function enumerates `source_dir.rglob('*')`; a `source_dir` that does not exist, is empty, or raises `OSError` yields `ContentComparison(matched=0, total=0, diverged=0)`. `_evaluate_single` tests only `content.diverged > 0`, so a zero-file comparison satisfies the content conjunct. Executed against the module at HEAD: `compare_pin_content(pin, tmp/'does-not-exist')` → `render()` = `'0 of 0 files match; 0 diverge'`, and `evaluate` over an otherwise-agreeing observation returns `outcome='pass'`, `reason='all three stores agree and the pin content matches source'`.
- **Why it matters:** this is a false green on the one conjunct the plan built specifically because *"'clean' would have been wrong"* — an operator handed a wrong or mistyped `source_dir` is told the pin matches source, when nothing was compared. It reproduces the epic's archetype (could-not-look collapsed into pass) inside the detector meant to catch it.
- **Fix:** make an empty comparison unrepresentable as a pass. Either return `None` from `compare_pin_content` when `total == 0` (routing to the existing `content is None` → `indeterminate` branch at `:430`), or add an explicit `ContentComparison.usable` predicate (`total > 0 and not partial`) and require it in `_evaluate_single` before the `pass` arm, emitting `could_not_look: pin content comparison examined 0 files` otherwise. Distinguish the `OSError` case from the genuinely-empty case in the reason string.
- **Done when:** `evaluate` over an observation whose `content` has `total == 0` returns `indeterminate`, not `pass`, and a test in `test/pm-plugin-development/plugin-doctor/test_plugin_pin_trap.py` drives `compare_pin_content` with a nonexistent `source_dir` and asserts the resulting verdict is `indeterminate`.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — the pin-trap detector's content conjunct.

## G2 — Make the partial-scan signal reachable from the adapter that is supposed to raise it

- **Kind:** vacuous-test
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py:673` — the `scanned=` argument built by `compare_pin_content`; assertion at `test/pm-plugin-development/plugin-doctor/test_plugin_pin_trap.py:320`
- **What is wrong:** every source file is counted either into `scanned` or into `unreadable`, so `scanned_total = scanned + unreadable == total` always holds, and `ContentComparison.partial` (`_scanned < total`) is therefore **never** `True` for any value the adapter can produce. Executed: a pin missing 2 of 5 source files returns `ContentComparison(matched=2, total=5, diverged=3, scanned=5)`, `partial=False`. The only test of the honest-degradation path, `test_content_comparison_partial_scan_says_so`, constructs `ContentComparison(..., scanned=110)` by hand — a state no code path reaches.
- **Why it matters:** the plan's *"it degrades honestly: a partial scan says so"* conjunct is present in `render()` and dead in practice, so a genuinely degraded comparison renders identically to a complete one. The test guards a shape of data the production adapter cannot emit, which is the vacuous-guard pattern this epic exists to remove.
- **Fix:** decide what "partial" means and wire it. A file the pin simply lacks is a **divergence**, not a degradation, so `FileNotFoundError` on the counterpart should count into `diverged` with `scanned` incremented; only an unreadable *source* file (or an `OSError` other than not-found) should count as unscanned and drive `scanned < total`. Then add a test that makes a source file unreadable (`chmod 000`, skipped when running as root) or otherwise forces the degraded branch, and assert `PARTIAL scan` appears in `render()`.
- **Done when:** a test drives `compare_pin_content` — not the dataclass constructor — into a state where `partial` is `True` and `render()` contains `PARTIAL scan`.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — the pin-trap detector's content conjunct.

## G3 — Include the content axis in the double-sample agreement check, or say why it is excluded

- **Kind:** bug
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py:290` — `_volatile_signature`
- **What is wrong:** the signature covers the marker set, `install_path_version`, `registry_version`, and `executor_version`, but not `obs.content`. Executed: two observations identical except for `ContentComparison(352,360,8)` vs `ContentComparison(360,360,0)` yield `outcome='fail'`, `shapes=('shape4:pin-diverges-from-source',)` — a confident verdict over two samples that demonstrably disagreed. The docstring names the marker set and "the registry and executor reads" and is silent on the omission.
- **Why it matters:** the content scan is by far the longest read in an observation (it hashes every source file), so it is the axis most exposed to a read-during-write — a sync writing into the pin dir while it is being hashed. The plan states that the false FAIL is the more dangerous direction *because it acts* (an operator was told not to launch, citing a trap that did not exist), and D7(d) exists specifically to close it. The one axis where a mid-write is most likely is the one the guard skips.
- **Fix:** add the content comparison's counts (`matched`, `total`, `diverged`, `_scanned`) to the tuple returned by `_volatile_signature`, so a content disagreement between the two samples yields `indeterminate` with the existing `read_during_write` reason. If the cost of a second content scan is judged prohibitive, keep the exclusion but state it in the docstring and in `Verdict.notes`, so the verdict discloses which axes were double-sampled.
- **Done when:** `evaluate` over two observations differing only in `content` returns `indeterminate`, covered by a test alongside `test_disagreeing_samples_yield_indeterminate`; or the exclusion is explicit in both the `_volatile_signature` docstring and the published notes.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — the pin-trap detector's double-sampling.

## G4 — Shape 3 does not fire on the configuration the plan's shape 3 names

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py:381` — the `SHAPE_3_STALE_UNMARKED_BESIDE_PIN` condition; fixture at `test/pm-plugin-development/plugin-doctor/test_plugin_pin_trap.py:111`
- **What is wrong:** the plan's shape 3 is `unmarked == [stale, pin]` — "a stale unmarked dir **beside a correct pin**". The implemented condition is `len(unmarked) >= 2 and loader_selected_version(dirs) != install_path_version`, and since `loader_selected_version` is the numerically-highest dir, it can only be satisfied when a **non-pin dir sorts higher than the pin**. Executed: `version_dirs=(VersionDir('0.1.100', marked=False), VersionDir('0.1.200', marked=False))` with `installPath='0.1.200'` and every other store agreeing → `outcome='pass'`, `shapes=()`. The test fixture encodes the mirror-image tree (pin `0.1.100`, stale-but-higher `0.1.300`), so the discrepancy is invisible from the suite.
- **Why it matters:** report-01.md states the oracle "rejects all six shapes"; one of the six, as literally described, passes. Whether the reinterpretation is defensible (under newest-wins selection an older unmarked dir is harmless) is a judgement the reader is never given the chance to make, because neither the module nor the report records that shape 3 was redefined.
- **Fix:** either (a) broaden the condition so `len(unmarked) >= 2` is itself reported — as a GC-adjacent *observation* rather than a hard fail, since two unmarked dirs is the post-sync window the plan says the unmarked set is good for — or (b) record the reinterpretation explicitly: rename the constant to match what it detects (e.g. `shape3:loader-follows-non-pin-dir`), state in the module docstring that the plan's literal `[stale, pin]` tree is a pass under newest-wins selection, and say why. Whichever is chosen, add a test asserting the literal tree's verdict so the choice is pinned.
- **Done when:** the literal `unmarked == [older-stale, newest-correct-pin]` tree has an asserted verdict in the test suite, and the shape-3 constant's name and docstring describe the condition the code actually evaluates.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — the pin-trap detector's shape table.

## G5 — Correct the `is_candidate` caveat: backward resolution is routine, not "practically unreachable"

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `doc/plans/truthful-signals/320-.../report-01.md` (the non-blocking caveat below the deliverables table) and `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py:269` — `loader_selected_version`
- **What is wrong:** the report says the model "diverges only in the practically-unreachable case where the newest-on-disk dir lacks `skills/`". `skills/` is only `collect_script_dirs`' predicate (`marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_bundles.py:176`). `resolve_bundle_path` (`:135`) passes `lambda d: (d / subpath).exists()` — a per-request predicate — so `select_live_version_dir` resolves to an **older** version dir whenever the newest one does not carry the specific subpath being resolved (a script added, renamed, or moved between versions).
- **Why it matters:** that per-request predicate is the only mechanism in this repository by which a resolution can go *backward*, which is exactly the incident the plan's problem statement describes ("seated a session dozens of versions backward"). Because `loader_selected_version` cannot represent it, the detector cannot name the failure it was built for, and the report's caveat tells a future reader the omission does not matter.
- **Fix:** give `loader_selected_version` an optional eligibility parameter (e.g. `eligible: Container[str] | None`) restricting the pool, defaulting to all dirs; have `observe()` populate it from the cache dirs that actually carry the subpath/skill under test. Update the caveat in the module docstring to name `resolve_bundle_path`'s per-request predicate as the divergence case rather than `skills/`.
- **Done when:** `loader_selected_version` returns an older dir when the newest is excluded by the supplied eligibility set, asserted by a test, and no surface still claims the divergence case is "practically unreachable".
- **Module/topic:** `pm-plugin-development:plugin-doctor` — the D4 loader-selection model.

## G6 — Retire the dead marker logic in `loader_selected_version` and the docstrings that describe it

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py:269-287` (`loader_selected_version` body and docstring), `:23-25` and `:90` (`_UNMARKED_DERIVED_NOTE`), `:63-64`, `:141-149` (`VersionDir`)
- **What is wrong:** the body computes `pinned = max(dirs, ...)`, then `live = [d for d in dirs if d.name == pinned.name or not d.marked]`, then `max(pool, ...)`. Since `pinned ∈ live` by construction and `pinned` is already the maximum, `max(live) == pinned` unconditionally. Executed over all 16 mark combinations of four version dirs: **0 diverge** from plain `max(dirs, key=_version_key)`. The docstring nevertheless describes a retention-pin/unmarked-set mirror of `select_live_version_dir` — and since PR #1223 (`d01edfdf`, landed 3h45m after this plan's `4ac41326`) that selector reads `.orphaned_at` **not at all**, `_partition_version_dirs` and `live_version_dirs` are deleted, and the sole `.orphaned_at` writer under our tree is gone. This is supersession, not an original defect: the mirror was faithful at `4ac41326`.
- **Why it matters:** a reader auditing the detector is told it mirrors marker-aware selection code that no longer exists, and the dead `live`/`pool` filtering invites a future change that assumes markers are load-bearing here. `VersionDir.marked` remains legitimately load-bearing for the GC-exposure axis, so the fix is a trim, not a removal.
- **Fix:** reduce `loader_selected_version` to `max(dirs, key=_version_key).name` (guarding the empty case) and rewrite its docstring to state the current selector contract — numerically-newest **eligible** wins, marker never consulted — citing `marketplace_bundles.select_live_version_dir` and `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md` § plugin-cache retention semantics. Rewrite `_UNMARKED_DERIVED_NOTE` so it scopes the marker claim to the foreign GC and to the GC-exposure axis, without implying our resolvers follow the unmarked set. Keep `test_loader_ignores_marker_on_retention_pinned_newest` and `test_loader_saturation_falls_back_to_newest` but rename them to describe marker-insensitivity.
- **Done when:** no docstring in `_plugin_pin_trap.py` claims our version selection consults `.orphaned_at`, and `loader_selected_version` contains no branch whose outcome is independent of the marker.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — the D4 loader-selection model (superseded by `truthful-signals/360`).

## G7 — A version-split executor is reported as unreadable rather than as the divergence it is

- **Kind:** bug
- **Severity:** low
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py:616` — `read_executor_anchored_version`, consumed at `:407-408`
- **What is wrong:** the function returns `None` for three distinct conditions — the file is unreadable, it carries no cache-anchored path at all (the marketplace-layout executor), and its embedded paths **disagree** on the version. Its own docstring calls the third case "fail-closed", but `_evaluate_single` maps `executor_version is None` into `unreadable`, so the verdict is `indeterminate: could_not_look: executor` rather than a fail. An internally version-split executor is a genuine pin-gap symptom being filed as "could not look".
- **Why it matters:** the three conditions carry different operator actions (re-read / not applicable / regenerate the executor), and collapsing them loses the one that names a real defect. Severity is low because `indeterminate` is not a pass, so nothing green ships — the loss is diagnostic precision.
- **Fix:** return a small result type (or a `(version, status)` tuple) distinguishing `unreadable` / `no_anchor` / `split(versions)`, and have `_evaluate_single` route `split` onto the divergence axis with the conflicting versions named, leaving the other two on the `unreadable` list. Extend `test_read_executor_anchored_version_split_is_none` to assert the resulting verdict rather than only the `None`.
- **Done when:** `evaluate` over an observation built from a version-split executor returns `fail` naming the conflicting versions, while an unreadable executor still returns `indeterminate`.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — the pin-trap detector's executor adapter.
