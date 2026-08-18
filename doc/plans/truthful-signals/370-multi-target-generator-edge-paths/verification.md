# Verification — 370-multi-target-generator-edge-paths

**Verified against:** commit `dc7684d6`   **Landed as:** PR #1228, commit `7de3084a`   **Verdict:** implemented-with-gaps

> Verdict revised during adversarial review (§ Adversarial review): every deliverable shipped, but
> D4's done-when — "the documented behaviour is what actually happens" — holds for only one of the
> two corrupt-input classes (G6, reproduced by execution), and D0's reverse sweep missed a second
> asymmetry (G7). No deliverable is unimplemented, so this is `implemented-with-gaps`, not
> `partially-implemented`.

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
| D0 | GATE: confirm findings by symbol, re-count, delete the closed deliverable, reverse-sweep | Each finding confirmed/refuted by symbol; surviving set stated | yes | yes | yes | mostly | `report-01.md` § D0 table (11 rows, all by symbol). Prefix-strip sweep re-derived → 0 occurrences; guard `test/marketplace/test_prefix_strip_idiom_retired.py` present (population-derived: asserts `scanned > 0` before asserting the offender list is empty, so it cannot pass vacuously). Reverse sweep missed **two** asymmetries — see G3 and G7 |
| D1 | Guard the destructive wipe, reuse the sibling helper, fix the docstring | An output path inside the source tree is refused | yes | yes | yes | yes | `marketplace/targets/fs_safety.py::is_within`/`safe_rmtree` (new, 49 lines); `claude/emitter.py::emit_bundle_verbatim` raises `ValueError('… lies inside the source tree …')` before the wipe, then `safe_rmtree(dest_root, output_dir)`. `opencode/emitter.py` imports the shared helper; pre-fix `_safe_rmtree` gone (0 hits). Docstring rewritten — the "gitignored ⇒ safe" clause is now explicitly labelled NOT the safeguard. Mutation → RED |
| D2 | Make the non-pruning emitter prune | A skill removed from source leaves no emitted directory behind | yes | yes | yes | yes for **this** emitter (full regen only, disclosed); the sibling Claude emitter has no equivalent — G7 | `opencode/emitter.py::_prune_stale_outputs`, called from `emit_bundles` when `bundle_list is None`. File-granularity unlink + deepest-first empty-dir `rmdir`. Verified on the real corpus (injected stale file **and** stale dir both removed) and by three tests, all RED with the prune disabled |
| D3 | Anchor the frontmatter closing fence | A value containing three hyphens no longer truncates | yes | yes | yes | yes (within `marketplace/targets/`, one weaker sibling — G2) | `opencode/frontmatter.py::parse_frontmatter` — `content.startswith('---\n')`, `content.find('\n---\n', 4)`, plus the EOF-fence tolerance, matching `claude/variant_emitter.py::parse_frontmatter` (`startswith` at `:101`, `find` at `:103`). Mutation → RED |
| D4 | Guard the JSON read | The documented diagnostic, not a traceback | yes | mostly | mostly | **no** | `claude/equality_check.py::CorruptEmittedPluginJsonError` raised in `_read_emitted_plugin_json:133`, caught in `run_equality_check:263`; summary reads "…not valid JSON for: demo — run 'python3 marketplace/targets/generate.py …' first". `test_corrupt_emitted_plugin_json_returns_diagnostic` passes. **But the guard is only `except json.JSONDecodeError`:** executed on a synthetic target tree, an emitted `plugin.json` of `[]` / `"hello"` / `null` still escapes as `AttributeError: 'list' object has no attribute 'get'` from `check_bundle:198`, while the adjacent `_check_marketplace_json` guards both halves (`:111` decode **and** `:113` `isinstance(..., dict)`) — see G6. Docstring still enumerates only "missing or drifts" — see G1 |
| D5 | Key the cache on content, not path | A modified file at the same path is re-read | yes | yes | yes | yes | `claude/variant_emitter.py::_load_mapping` (uncached, stats) → `_load_mapping_cached(path, mtime_ns)` (`@lru_cache`). **Executed** with a real in-place rewrite and no `utime`: `False` → `True`. `lru_cache` sweep over `marketplace/targets/` → this is the only one |
| D6 | De-duplicate the overlapping diff layers | One root cause → one entry | **DROPPED** (plan-sanctioned) | yes | n/a | n/a | `check_bundle:167` still has both layers. The drop rationale re-checked: `claude/target.py::generate:143-149` writes the bundle files and immediately regenerates `plugin.json` in the same loop iteration from one source, so the C1 state (file on disk, absent from its own sibling manifest, still in source) is not producible by the pipeline. Plan explicitly authorises the drop; the report names it and gives the four constructed states |
| D7 | Tests, each verified FAIL-first, with a matched control for the wipe guard | All pass, each seen red first, both halves present | yes | yes | yes | yes | 104 tests pass across the six files. Both control halves exist and are named in the diff. FAIL-first independently re-derived here for D1, D2, D3 by mutation and for D5 by execution |

### D0 — reverse sweep, two misses

The reverse sweep ("the emitter with the guard may lack something the other has") concluded "no
*other* asymmetry survives". Its statement about `claude/iter_bundle_dirs` is correct — I confirmed
by reading it that it filters real `iterdir()` entries by name membership and never joins a
caller-supplied name, so it cannot traverse. But the sweep ran before D1 and D2 landed, and **each of
them created an asymmetry it could not have seen**:

1. `claude/emitter.py` now refuses a destination inside the source tree; `opencode/emitter.py` has no
   equivalent check, and D2 gave it a new (file-granularity) destructive path. No reachable harm was
   found in this repository — see G3.
2. `opencode/emitter.py` now prunes a bundle removed from source; `claude/target.py::generate` does
   not, and nothing else surfaces the resulting drift. Reproduced against the real corpus during the
   adversarial review — see G7.

The sweep's own conclusion, "no *other* asymmetry survives", was therefore true of the pre-PR pair
and false of the pair the PR shipped. A reverse sweep that runs before the change it is meant to
police is a clean signal about the wrong tree.

### D4 — documented behaviour, partially

The behaviour is correct **for the input class the shipped test covers** (a file that fails to
parse), and tested. Three mismatches remain:

1. The guard is `except json.JSONDecodeError` only. An emitted `plugin.json` that parses to a
   non-object — `[]`, `"hello"`, `null`, `3` — reaches `check_bundle:198`'s `committed.get(...)` and
   escapes as `AttributeError`. `generate.py:439`'s blanket `except Exception` turns that into
   `error: target 'claude' failed: 'list' object has no attribute 'get'` — a type error where the
   documented re-run-emit remedy belongs. The plan named this read's asymmetry with
   `_check_marketplace_json` as *the evidence*, and `_check_marketplace_json` guards both halves
   (`:111` and `:113`). D4 copied one. See G6 — this is why D4's "Complete?" is now `no`.
2. `run_equality_check`'s docstring still lists only "missing or drifts" as the failure modes it
   converts into a diagnostic.
3. The corrupt bundles are returned inside a field named `missing_target_bundles` (as
   `sorted(missing) + sorted(corrupt)`, so not globally sorted either).

(2) and (3) are G1.

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
  matches `claude/target.py::generate` (the loop at `:141-149` writes the mirror and rewrites
  `plugin.json` in the same iteration). **Re-derived again by execution during the adversarial
  review**: all four states were built as synthetic trees and run through `check_bundle`, giving
  C1 = 2 (`['agents', 'agents-orphans']`), C2 = 1, C3 = 1, C4 = 1 — the report's table exactly.
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
| D6 dropped with evidence | Still dropped — `check_bundle` retains both layers; no code was added. Correct per the plan; the C1–C4 counts were re-derived by execution during the adversarial review and match. |
| Observation 2 accepted: D5 keys on `st_mtime_ns`, not a content hash (two-writes-in-one-tick blind spot) | Still true at `variant_emitter.py:302-336`. The plan explicitly sanctions "path plus modification time", and the real-edit execution above confirms the practical path works. Not a gap. |
| "Nothing else open." | **Not** confirmed. Seven items are in `gaps.md` — five from this verification, two (G6, G7) added by the adversarial review. None reverses a deliverable, but G6 narrows D4's done-when and G7 shows D2's defect class alive in the sibling emitter. |

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

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked — by what means.** Everything below was re-derived at HEAD (`6dbf0657`), not read off this
document.

*Provenance and scope.* `git log --all --grep '#1228'` → `7de3084a`;
`git merge-base --is-ancestor 7de3084a HEAD` → 0; `git show --stat -M` → **14 files, +653/−33**
(matches); `git log 7de3084a..HEAD -- <path>` → **empty for all twelve** code/test files (re-run
per file); `git show --name-status -M` → **no `marketplace/bundles/**` path**, confirming the
out-of-scope claim.

*Tests.* The six touched test files re-run with `-o addopts="" -q` → **104 passed** (matches).
`--collect-only` → all **seven** D7 test names plus **five** `is_within` and **two** `safe_rmtree`
unit tests collected under the exact paths given (matches).

*Mutations* (each file `git diff --quiet`-checked clean first, byte-snapshotted to the scratchpad,
restored from those bytes, re-confirmed clean — never `git checkout`):

| Mutation | Result |
|---|---|
| `claude/emitter.py` — `if False and is_within(dest_root, source_root)` | `test_emit_bundle_verbatim_refuses_output_inside_source_tree` **RED** ("DID NOT RAISE ValueError") |
| `opencode/frontmatter.py` — restored `content.find('---', 3)` | `test_value_containing_triple_dash_does_not_truncate` **and** `test_simple_keys_parsed` **RED** |
| `opencode/emitter.py` — `if False and bundle_list is None` | all three `test_emit_bundles_prunes_*` **RED** |

*Functions executed, not read.* `supports_effort('opus','xhigh', p)` across an in-place v1→v2 rewrite
at the same path with **no `os.utime`** → `False` then `True`, `_load_mapping_cached.cache_info()` =
2 misses / 0 hits (D5 upheld). `_frontmatter_field` on four crafted inputs (G2). `run_equality_check`
on four emitted-`plugin.json` payloads (G6). `check_bundle` on all four D6 states (C1–C4). Two real
end-to-end generations: `--target opencode` → **1090 entries**, `--target claude` → **1165 entries**
(both match), plus the opencode stale-artifact injection (stale skill dir, stale command sub-dir,
stale agent file — **all three removed**) and the claude phantom-bundle injection (G7).

*Sweeps re-run with broader patterns than the originals.* `lstrip(` (not just `lstrip('./')`) across
`marketplace/**/*.py` → 20+ legitimate uses, **0** of the retired two-spelling idiom; the guard test
read in full and confirmed population-derived (asserts `scanned > 0` first). `_safe_rmtree`
repo-wide → **2 hits, both test function names**. `cache_clear` under `marketplace/` → 3 hits, none
in `targets/`. `lru_cache|@cache|cached_property|functools` under `marketplace/targets/` → the single
`@lru_cache` at `variant_emitter.py:326`. `gitignored` (case-insensitive, not the phrase
"gitignored ⇒ safe") under `marketplace/targets/` → 4 prose hits, each read and each correct.
`---` across every `.py` under `marketplace/targets/` to find frontmatter readers the D3 sweep might
have missed → exactly the three G2 names plus `opencode/variant_emitter.py::_inject_effort`, which
is a writer over a self-generated block and already line-anchored.
`missing_target_bundles` repo-wide → 3 production sites, 3 test assertions, **no production
consumer** (G1's "only tests read it" upheld). Singular `skill`/`agent`/`command` directories under
`marketplace/bundles/` → **none** (G3's containment claim upheld). `(Recorded at close.)` under
`doc/` and `.claude/` → this report and this gaps file only (G4 is not a template-wide defect).

*Pre-fix bodies.* `git show 7de3084a^:` for `opencode/emitter.py` (`_safe_rmtree` at `:125-132`,
semantically identical to `safe_rmtree` — "extracted, not re-implemented" upheld),
`opencode/frontmatter.py` (`startswith('---')` at `:113`, `find('---', 3)` at `:115`), and
`claude/variant_emitter.py` (`@lru_cache` on `_load_mapping(mapping_path)` at `:302-303`). All three
report claims upheld verbatim.

**Not re-checked.** The `./pw verify` totals (19632 passed / 14 skipped) and its wall-clock; the
entire "Reviewer participation" and "Cost" sections (no GitHub access was used); the PR timestamps;
whether the `--bundles`-scoped OpenCode path is exercised by a real workflow; the `pr_agent` target
and `claude/content_drift*.py` / `source_fingerprint.py`, which the PR did not touch; and how
`/sync-plugin-cache` treats a phantom bundle directory (G7's local-machine impact is stated as the
mechanism observed at the generator, not traced into the sync engine).

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | `run_equality_check` docstring omits the corrupt case; corrupt names folded into `missing_target_bundles`, unsorted — medium | **upheld**, refs tightened | Docstring at `:232-236` lists only "missing or drifts"; fold at `:283`; field at `:87`. Repo-wide sweep: 3 production sites, 3 test assertions, **zero** production consumers — "only tests read the field" holds. Fix text corrected from "three call sites" to the two construction sites + declaration, with the test line numbers named |
| G2 | `_frontmatter_field` closes on any `---`-leading line — low | **upheld as a defect; its rationale refuted and rewritten** | Executed: an unindented `--- note` line inside the block makes `_frontmatter_field(..., 'user-invocable')` return `''` instead of `'true'`. But `build_user_invocable_lookup` does **not** decide the command wrapper — its one consumer (`opencode/target.py:53`) feeds the Transform 2 slash-command body rewrite; the wrapper is decided by `opencode/emitter.py:215` off the D3-fixed parser. Full refutation recorded in `gaps.md` § Refuted. Line ref `:356` corrected to `:347`/`:355`/`:357`. Latency claim upheld: 0 disagreements over all 11 bundles' SKILL.md |
| G3 | OpenCode `emit_bundles` lacks the source-tree refusal — low | **upheld** | `emit_bundles` at `:438` and `_prune_stale_outputs` at `:135` confirmed; `safe_rmtree` constrains only the target, never `output_dir` itself (`fs_safety.py:42-46`). `find` over `marketplace/bundles/` for singular `skill`/`agent`/`command` dirs → **none**, so "creates junk rather than destroying source" holds. Fix is actionable and its Done-when observable: `is_within(marketplace_dir, marketplace_dir)` is `True`, so the proposed check does fire on the stated call |
| G4 | Four duplicated empty placeholder sections at the end of `report-01.md` — low | **upheld**, rationale tightened | Confirmed at `report-01.md:153-167`; the filled versions are at `:118-151`. The headings are the tail of the report template (`cloud-plan-lane/SKILL.md:1536-1560`). The unchecked clause "an archived-plan retrospective sweep that reads the last occurrence of a heading" was replaced with what is actually observable. Also checked and **not** filed: the report carries no § Findings stop record, but that requirement landed in `2b5d1aad` on 2026-08-17, three days after this run — not a defect of this report |
| G5 | `fs_safety.py` missing from the README architecture tree — low | **upheld**, figures re-derived | Tree confirmed at `README.md:9-26`. The "already incomplete" list was a sample: re-derived by listing the package, **eight** modules are missing, not six — the original list omitted `claude/content_drift_cli.py` and did not name `fs_safety.py` itself. Done-when widened to match the Fix, which had asked for `claude/` too while the Done-when covered only the top level and `opencode/` |
| D0 reverse sweep | "No *other* asymmetry survives" | **refuted a second time** | Its `claude/iter_bundle_dirs` reasoning is correct (re-read: filters real `iterdir()` entries by name membership, never joins a caller-supplied name). But the sweep ran before D1/D2 landed, so it is a clean signal about the pre-PR pair. G3 is one miss; G7 is a second |
| D2 clean pass | "A skill removed from source leaves no emitted directory behind" | **upheld for this emitter** | Re-derived on the real 11-bundle corpus, not fixtures: stale `skill/ZZZ-stale/SKILL.md`, stale `command/leftover/old.md` and stale `agent/zz-orphan.md` injected, re-generated → all three files unlinked and both emptied directories removed. Mutation → 3 RED |
| D4 clean pass | "Correct? yes / Complete? yes" | **re-severitied → Correct? mostly, Complete? no** | New gap **G6**, established by execution, not reading: `[]` / `"hello"` / `null` as the emitted `plugin.json` still escape `run_equality_check` as `AttributeError`, because the guard is `except json.JSONDecodeError` alone while the adjacent read the plan cited as the evidence checks `isinstance(..., dict)` too |
| D5 clean pass | Cache re-reads a file edited in place | **upheld by execution** | `supports_effort('opus','xhigh', p)` → `False`, in-place rewrite with **no `os.utime`**, → `True`; `cache_info()` = 2 misses / 0 hits. `supports_effort` is shared by both targets (`opencode/variant_emitter.py:71`), so one fix covers both |
| D6 drop | Unreachable → dropped, no code added | **upheld by construction** | All four states built and run: C1 = 2 entries (`agents` + `agents-orphans`), C2 = 1, C3 = 1, C4 = 1 — the report's table exactly. `claude/target.py::generate:141-149` writes the mirror and rewrites `plugin.json` in the same iteration, and `emit_bundle_verbatim` excludes `plugin.json` from the copy while wiping `dest_root`, so a mid-emit crash leaves no manifest at all → the `missing` path, not C1 |
| Report accuracy | "the tree contradicts no material claim" | **upheld** | Every re-derivable figure matched: 14 files / +653/−33, 104 tests, 7 + 7 test names, 1090 and 1165 entries, C1–C4, the three pre-fix bodies, the zero-occurrence prefix-strip sweep. Two line refs were off by one and are corrected in place (`variant_emitter.py:102` → `:103`; `target.py::generate:143-149` → `:141-149`) |
| — | (new) | **added: G6** | See D4 row |
| — | (new) | **added: G7** | Claude emitter never prunes a bundle removed from source. Reproduced: generate → 1165 entries; inject `zz-removed-bundle/` with a `plugin.json` and an `agents/gone.md`; re-generate → **both survive**, run reports success, and the post-emit line reads `stamped version 0.1.513 into 12 bundle plugin.json` against an 11-bundle source (`generate.py:462` walks the output tree). Phantom also enters `.emit-marker.json`'s `file_hashes`; it is absent from the regenerated `marketplace.json`, and `run_equality_check` iterates the *source* bundle list, so nothing surfaces the drift. Bounded: `claude-distribute.yml` builds from a fresh checkout, so no published distribution can carry one |

**Documents corrected.**

*verification.md:* verdict `fully-implemented` → **`implemented-with-gaps`**, with the reason stated
under the heading. D4's row re-scored (`Correct? mostly`, `Complete? no`) and its § D4 section
rewritten from two mismatches to three, the new one first. D2's row qualified to "this emitter".
D0's row and § D0 rewritten to record **two** missed asymmetries and to name *why* the sweep was
clean (it ran before the change it was meant to police). `variant_emitter.py:102` → `:103`;
`target.py::generate:143-149` → `:141-149`. The C1–C4 re-derivation upgraded from "by reading" to
"by execution", in both places it appears. The "Nothing else open" residue row flipped from
confirmed to not confirmed, with the count corrected from five to seven.

*gaps.md:* open items 5 → **7**; the header summary rewritten, since "correct" no longer holds
unqualified for D4. G1's fix text corrected. G2's line reference corrected and its **Why it matters**
clause replaced after refutation, with the refutation recorded in a new § Refuted during adversarial
review rather than dropped. G4's unchecked-mechanism clause replaced with observable facts. G5's
sampled module list re-derived (six → eight) and its Done-when widened to match its own Fix. G6 and
G7 added.

**Residual doubt — what a third reviewer should look at first.**

1. **G7's blast radius, traced into the sync engine.** This review established the drift and the
   inflated count at the generator. It did **not** trace what
   `marshall-steward`'s cache sync does with a phantom bundle directory in `target/claude/` — whether
   it is mirrored into `~/.claude/plugins/cache/plan-marshall/`, and whether the cache-freshness /
   retention guards notice. If it is mirrored, G7 is arguably `high`, not `medium`.
2. **The `--bundles`-scoped OpenCode path.** `_prune_stale_outputs` is deliberately skipped there,
   and the docstring's justification ("the normal build and the drift checks both run full
   regenerations") was spot-checked only against `opencode/target.py::generate`. If any workflow
   invokes a scoped emit as its *only* emit, that tree drifts silently and the D2 done-when does not
   cover it.
3. **`fs_safety.is_within`'s string comparison.** It resolves both operands and then compares with
   `str(resolved).startswith(str(resolved_root) + '/')`. `test_is_within_rejects_prefix_sibling`
   covers the `/a/bc` vs `/a/b` case, but the separator is hard-coded `'/'` and the root-directory
   case (`root == Path('/')`, where the concatenation yields `'//'`) is untested. Irrelevant on the
   POSIX CI runner; a third reviewer targeting portability should start there.
4. **The `./pw verify` totals**, still unverified from this clone in either pass.
