# Verification — 370-multi-target-generator-edge-paths

**Verified against:** commit `dc7684d6`   **Landed as:** PR #1228, commit `7de3084a`   **Verdict:** fully-implemented

## Method

Read `plan.md` and `report-01.md` in full. Located the landed commit via
`git log --oneline --all --grep '#1228'` → `7de3084a` ("fix(targets): harden the multi-target
generator's error and edge paths (#1228)"), confirmed an ancestor of HEAD
(`git merge-base --is-ancestor 7de3084a HEAD` → 0). Read the full landed diff
(`git show --stat -M`, `git show <sha> -- <path>`) and confirmed **no later commit touches any of
the twelve code/test files** (`git log 7de3084a..HEAD -- <each file>` → empty for all twelve), so
HEAD is the landed state.

Files opened at HEAD: `marketplace/targets/fs_safety.py`, `marketplace/targets/claude/emitter.py`,
`marketplace/targets/claude/equality_check.py`, `marketplace/targets/claude/variant_emitter.py`,
`marketplace/targets/claude/target.py`, `marketplace/targets/opencode/emitter.py`,
`marketplace/targets/opencode/frontmatter.py`, `marketplace/targets/opencode/variant_emitter.py`,
`marketplace/targets/opencode/target.py`, `marketplace/targets/body_transform_engine.py`,
`marketplace/targets/README.md`, and the six test files. Also read the pre-fix bodies
(`git show 7de3084a^:…`) of `opencode/emitter.py::_safe_rmtree` and
`opencode/frontmatter.py::parse_frontmatter` to check the "extracted, not re-implemented" claim.

Commands run:

- `uv run python -m pytest` over the six touched test files, `-o addopts="" -q` → **104 passed**.
- `--collect-only` grep confirming all seven D7 test names (plus the five `is_within` /
  two `safe_rmtree` unit tests) are collected.
- **Real end-to-end generation**: `generate.py --target opencode --output <tmp>` → 1090 entries;
  then injected two stale artifacts (`skill/ZZZ-stale.md`, `command/leftover/old.md`) and
  re-generated → **both removed, including the emptied `command/leftover/` directory**. D2 verified
  against the real 11-bundle corpus, not only fixtures.
  `generate.py --target claude --output <tmp>` → 1165 entries, guard does not break real emits.
- **D5 executed, not read**: `supports_effort('opus','xhigh', p)` on a mapping written v1→v2
  **in place at the same path with NO `os.utime` call** returned `False` then `True` — the fix
  works on a genuine edit, not only on the test's synthetic mtime bump.
- Sweeps re-derived at HEAD: `lstrip('./')` / `lstrip("./")` under `marketplace/` → **0**;
  `_safe_rmtree` in production code → **0** (only the two test names in `test_fs_safety.py`);
  `_load_mapping.cache_clear()` → **0**; `lru_cache`/`@cache` under `marketplace/targets/` → **1**
  (the new `_load_mapping_cached`); "gitignored ⇒ safe" prose → **0**.

**Mutation checks** (each file confirmed unmodified with `git diff --quiet` first, snapshotted to
the scratchpad, restored from those bytes, and re-confirmed clean — never `git checkout`):

| Mutation | Test result |
|---|---|
| `claude/emitter.py` — disabled the source-tree refusal (`if False and is_within(...)`) | `test_emit_bundle_verbatim_refuses_output_inside_source_tree` **RED** ("DID NOT RAISE ValueError"); the fixture source was in fact wiped, confirming the original hazard is real |
| `opencode/frontmatter.py` — restored the raw-substring fence (`content.find('---', 3)`) | `test_value_containing_triple_dash_does_not_truncate` **RED** (`'before' != 'before --- after'`) |
| `opencode/emitter.py` — disabled the prune call | all three `test_emit_bundles_prunes_*` **RED** |

Working tree left clean: `git status --porcelain -- marketplace/ test/` → empty.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: confirm findings by symbol, re-count, delete the closed deliverable, reverse-sweep | Each finding confirmed/refuted by symbol; surviving set stated | yes | yes | yes | mostly | `report-01.md` § D0 table (11 rows, all by symbol). Prefix-strip sweep re-derived → 0 occurrences; guard `test/marketplace/test_prefix_strip_idiom_retired.py` present. Reverse sweep missed one new asymmetry — see G3 |
| D1 | Guard the destructive wipe, reuse the sibling helper, fix the docstring | An output path inside the source tree is refused | yes | yes | yes | yes | `marketplace/targets/fs_safety.py::is_within`/`safe_rmtree` (new, 49 lines); `claude/emitter.py::emit_bundle_verbatim` raises `ValueError('… lies inside the source tree …')` before the wipe, then `safe_rmtree(dest_root, output_dir)`. `opencode/emitter.py` imports the shared helper; pre-fix `_safe_rmtree` gone (0 hits). Docstring rewritten — the "gitignored ⇒ safe" clause is now explicitly labelled NOT the safeguard. Mutation → RED |
| D2 | Make the non-pruning emitter prune | A skill removed from source leaves no emitted directory behind | yes | yes | yes | yes (full regen only, disclosed) | `opencode/emitter.py::_prune_stale_outputs`, called from `emit_bundles` when `bundle_list is None`. File-granularity unlink + deepest-first empty-dir `rmdir`. Verified on the real corpus (injected stale file **and** stale dir both removed) and by three tests, all RED with the prune disabled |
| D3 | Anchor the frontmatter closing fence | A value containing three hyphens no longer truncates | yes | yes | yes | yes (within `marketplace/targets/`, one weaker sibling — G2) | `opencode/frontmatter.py::parse_frontmatter` — `content.startswith('---\n')`, `content.find('\n---\n', 4)`, plus the EOF-fence tolerance, matching `claude/variant_emitter.py::parse_frontmatter:102`. Mutation → RED |
| D4 | Guard the JSON read | The documented diagnostic, not a traceback | yes | mostly | yes | yes | `claude/equality_check.py::CorruptEmittedPluginJsonError` raised in `_read_emitted_plugin_json:133`, caught in `run_equality_check:263`; summary reads "…not valid JSON for: demo — run 'python3 marketplace/targets/generate.py …' first". `test_corrupt_emitted_plugin_json_returns_diagnostic` passes. `run_equality_check`'s own docstring still enumerates only "missing or drifts" — see G1 |
| D5 | Key the cache on content, not path | A modified file at the same path is re-read | yes | yes | yes | yes | `claude/variant_emitter.py::_load_mapping` (uncached, stats) → `_load_mapping_cached(path, mtime_ns)` (`@lru_cache`). **Executed** with a real in-place rewrite and no `utime`: `False` → `True`. `lru_cache` sweep over `marketplace/targets/` → this is the only one |
| D6 | De-duplicate the overlapping diff layers | One root cause → one entry | **DROPPED** (plan-sanctioned) | yes | n/a | n/a | `check_bundle:167` still has both layers. The drop rationale re-checked: `claude/target.py::generate:143-149` writes the bundle files and immediately regenerates `plugin.json` in the same loop iteration from one source, so the C1 state (file on disk, absent from its own sibling manifest, still in source) is not producible by the pipeline. Plan explicitly authorises the drop; the report names it and gives the four constructed states |
| D7 | Tests, each verified FAIL-first, with a matched control for the wipe guard | All pass, each seen red first, both halves present | yes | yes | yes | yes | 104 tests pass across the six files. Both control halves exist and are named in the diff. FAIL-first independently re-derived here for D1, D2, D3 by mutation and for D5 by execution |

### D0 — reverse sweep, one miss

The reverse sweep ("the emitter with the guard may lack something the other has") concluded "no
*other* asymmetry survives". Its statement about `claude/iter_bundle_dirs` is correct — I confirmed
by reading it that it filters real `iterdir()` entries by name membership and never joins a
caller-supplied name, so it cannot traverse. But D1 *created* a new asymmetry the sweep ran before:
`claude/emitter.py` now refuses a destination inside the source tree; `opencode/emitter.py` has no
equivalent check, and D2 gave it a new (file-granularity) destructive path. No reachable harm was
found in this repository — see G3.

### D4 — documented behaviour, partially

The behaviour is correct and tested. Two smaller mismatches remain between code and its own prose:
`run_equality_check`'s docstring still lists only "missing or drifts" as the failure modes it
converts into a diagnostic, and the corrupt bundles are returned inside a field named
`missing_target_bundles` (as `sorted(missing) + sorted(corrupt)`, so not globally sorted either).
See G1.

## Report accuracy

Re-derived, and the tree contradicts **no material claim**. Checked specifically:

- **"New shared `fs_safety.py` … the sibling `_safe_rmtree` extracted, not re-implemented."** True.
  The pre-fix `opencode/emitter.py::_safe_rmtree` (at `7de3084a^`, lines 125–132) is semantically
  identical to `safe_rmtree`; `opencode/emitter.py:31` now imports it and defines no local copy
  (0 hits repo-wide).
- **"`opencode/frontmatter.py::parse_frontmatter` — `end = content.find('---', 3)`"** — confirmed
  at `7de3084a^`. **"`claude/variant_emitter.py::parse_frontmatter` — `end = text.find('\n---\n', 4)`"**
  — confirmed at `variant_emitter.py:103`.
- **"`_load_mapping` — `@lru_cache` keyed on `Path` only"** pre-fix — confirmed in the diff.
- **D6 reachability table (C1–C4).** Re-derived by reading `check_bundle`: C1 fires the manifest
  layer (`only_in_generated`) *and* the `{subdir}-orphans` layer → 2 entries; C3 fires only the
  manifest layer (orphans set is empty) → 1. The counts are right, and the unreachability argument
  matches `claude/target.py::generate`.
- **"the prefix-strip idiom returns zero occurrences … guard fails the build on re-introduction."**
  Re-derived: 0 occurrences under `marketplace/`; `test/marketplace/test_prefix_strip_idiom_retired.py`
  exists.
- **D7 test-name table.** All seven named tests plus the shared-helper unit tests exist and are
  collected under the exact paths given.
- **Out-of-scope claims** ("no `marketplace/bundles/**` edits, no second containment helper, no
  prefix-strip restatement"). All hold against `git show --name-status`.

Two minor imprecisions, neither changing an outcome:

1. The D0 table says the OpenCode emitter's functions "only `mkdir` + `write_text`". Pre-fix,
   `_copy_verbatim` also did `_safe_rmtree` + `copytree`, so a *file* removed from a surviving
   verbatim sub-directory was already pruned. The finding's substance — no top-level prune, so a
   removed component or a removed whole sub-directory lingers — is correct.
2. The report says the corrupt-JSON path returns "the documented 're-run emit' diagnostic". The
   emitted summary is correct, but `run_equality_check`'s docstring was never extended to document
   the corrupt case (G1).

**Not verifiable from this clone:** the `./pw verify` figures ("19632 passed, 14 skipped"), the
reviewer-participation table (`gh` is not installed here and no GitHub access was used), the PR
timestamps, and the two `./pw verify` wall-clock figures. The merge itself *is* verified: `7de3084a`
carries the `(#1228)` subject and is an ancestor of HEAD.

## Out-of-scope compliance

Clean. The landed diff is 14 files / +653 / −33:

- `doc/plans/truthful-signals/370-multi-target-generator-edge-paths.md` → `…/plan.md` (R100, the
  sanctioned plan-directory step) and the new `report-01.md`.
- Six files under `marketplace/targets/` (five modified, `fs_safety.py` new).
- Six test files under `test/marketplace/targets/`.

No file under `marketplace/bundles/**` was touched — the declared hard boundary. No second
containment helper was introduced (one module, imported by both emitters). The prefix-strip
deliverable was not restated. No undeclared collateral change: every non-plan file in the diff is
named in the plan's Expected surface, and `fs_safety.py` is the plan's own "reuse or share it"
instruction realised as a shared module.

## Residue carried forward

| Report residue | Status in today's tree |
|---|---|
| `coderabbitai` / `sourcery-ai` rate-limited, did not review this diff | Still true as a historical fact; PR #1228 is merged, so the window is closed. Not actionable. |
| D6 dropped with evidence | Still dropped — `check_bundle` retains both layers; no code was added. Correct per the plan. |
| Observation 2 accepted: D5 keys on `st_mtime_ns`, not a content hash (two-writes-in-one-tick blind spot) | Still true at `variant_emitter.py:302-336`. The plan explicitly sanctions "path plus modification time", and the real-edit execution above confirms the practical path works. Not a gap. |
| "Nothing else open." | Confirmed for the plan's own deliverables. Five smaller items surfaced by this verification are in `gaps.md`; all are low or medium, none reverses a deliverable. |

## What could NOT be verified

- The full-suite `./pw verify` result and its counts (19632 passed / 14 skipped) — re-running the
  whole build was out of proportion for this check. The six touched test files were run directly and
  are green.
- Everything in "Reviewer participation" and "Cost": PR comment surfaces, reviewer logins, rate-limit
  notices, PR `created_at`, and the wall-clock estimates. `gh` is not installed in this environment
  and no GitHub API call was made.
- The report's claim that each D7 test was seen red *at the time of the run* via `git stash`. What is
  verified here is the equivalent property, re-derived independently: D1, D2 and D3 go red under a
  targeted mutation of the production code, and D5's behaviour flips on a real in-place edit.
- Whether the `--bundles`-scoped OpenCode emit path is exercised by any real workflow (the prune is
  deliberately skipped there). The docstring's claim that "the normal build and the drift checks both
  run full regenerations" was spot-checked only against `opencode/target.py::generate`, which passes
  `bundles` straight through.
