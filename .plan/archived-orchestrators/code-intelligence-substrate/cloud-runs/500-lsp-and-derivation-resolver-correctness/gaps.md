# Gaps — 500-lsp-and-derivation-resolver-correctness

This plan's own run report already discloses most of its residue (§ Left open, twelve behavioural
survivors S1–S12/B2/B3, plus three items no verifier independently re-checked). The entries below turn
that disclosure — plus two items this audit found independently — into actionable follow-up work,
scoped and bounded so a successor plan can pick them up without re-deriving the reproduction from
scratch. None of these was left silently absent from the report; they are catalogued here because a
gaps file, unlike a narrative report, is meant to be triaged and worked one line at a time.

They cluster into three groups: (1) genuinely open, low-blast-radius correctness edges in the write
path (G1–G3); (2) a verification-debt group — figures or fixes nobody independently reproduced (G4,
G5); (3) one pre-existing, undisclosed-severity risk on the npm side that has the same shape as a
defect this plan treated as high-severity on the Python side (G6).

## G1 — CRLF files lose their line endings on any edit, invisibly to the rollback check

- **Kind:** bug
- **Severity:** low
- **Topic:** write-path-line-endings
- **Where:** `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/_lsp_workspace_edit.py:190-196` (comment naming the limit); the underlying cause is `Path.read_text`/`Path.write_text`'s newline translation, used throughout `apply_workspace_edit` and `_still_modified`.
- **Evidence:** Report `report-01.md` § Left open, row S1: *"a 3-character edit turned `b'aaa\r\nbbb\r\nccc\r\n'` into `b'aaa\nBBB\nccc\n'`. Invisible to the diagnostics gate **and to `_still_modified`**, so a rollback reports `rolled_back: true` over a file whose bytes differ from the pre-edit bytes."* Confirmed at HEAD: the write path still uses text-mode `read_text`/`write_text`, and no binary I/O with explicit newline handling was added.
- **Consequence:** On a CRLF-authored file (Windows-originated, or a mixed-EOL file), any successful edit — even a rejected/rolled-back one — silently rewrites every line ending to LF. `_still_modified` (the function that decides whether `restore_error` should be set) compares text content, which is unaffected, so this is the one residue item that can look clean while the bytes on disk changed.
- **Action:** Move the write path to binary I/O with explicit newline detection/preservation, or at minimum make `_still_modified`'s comparison byte-exact so a CRLF→LF change is at least visible as `restore_error` rather than silent.
- **Done when:** A test drives `apply_workspace_edit` over a CRLF-content file, applies an edit, rolls it back (e.g. via a follow-on diagnostics-worsened path), and asserts the restored file's bytes — not just its decoded text — are byte-identical to the pre-edit file.
- **Effort:** M
- **Risk if fixed:** Binary I/O changes error handling for non-UTF-8 files project-wide in this module; must be threaded through `_still_modified`'s existing `UnicodeDecodeError` handling (round 10's A-5 fix) without regressing it.

## G2 — Two rollback call sites in `_run_edit` sit outside any exception boundary

- **Kind:** bug
- **Severity:** low
- **Topic:** rollback-exception-boundary
- **Where:** `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/lsp_client.py:405` and `:425` — both bare `restore_files(originals)` calls in `_run_edit`, on the `diagnostics_unavailable` (`phase: after`) and `diagnostics_worsened` return paths.
- **Evidence:** `report-01.md` § Left open, row B2. Confirmed at HEAD: `grep -n "restore_files(originals)" lsp_client.py` returns exactly these two lines, neither wrapped in a `try`/`except`, unlike `apply_workspace_edit`'s own internal restore path which is guarded and sets `restore_error`.
- **Consequence:** An `OSError` during either of these two rollback attempts escapes `_run_edit` to `safe_main`, so the verb returns a bare `status: error` — never a false `success`/`rolled_back: true` (the report's own analysis is correct that this cannot produce a false clean) — but the caller also gets no `restore_error` detail and no indication the tree may still carry the edit.
- **Action:** Wrap both call sites the same way `apply_workspace_edit`'s internal restore is wrapped: catch `OSError`, re-derive `restore_error` via `_still_modified`, and return the existing `_edit_failure` payload shape with `restore_error` populated instead of letting the exception escape uncaught.
- **Done when:** A test patches `restore_files` (or the underlying `Path.write_text`) to raise during each of the two call sites and asserts the verb returns a structured `_edit_failure` payload with `restore_error` set, rather than an unhandled exception reaching `safe_main`.
- **Effort:** S
- **Risk if fixed:** Low — this mirrors an existing, already-tested pattern in the same file (`apply_workspace_edit`'s restore-error handling); the main risk is missing the fail-closed detail that a restore-error here means the tree state is *unknown*, not merely "restore attempted."

## G3 — The harvest's search-path derivation misses one real bare-import target

- **Kind:** bug
- **Severity:** low
- **Topic:** harvest-search-path-completeness
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/lsp_harvest.py:304-347` (`bare_import_roots`), structural rule at `:347` (`if not (parent / '__init__.py').exists()`).
- **Evidence:** `report-01.md` § D3 and § Left open row B3: `platform-runtime/scripts` carries an `__init__.py`, so the structural "no `__init__.py` ⇒ needs a search-path entry" rule correctly treats it as an ordinary package and omits it from `extraPaths` — but **three** real bare imports (`from claude_runtime import …` in `permission_common.py:26` and `permission_doctor.py:27`, and `from platform_runtime import _make_runtime` in `marketplace_paths.py:214`) target it anyway, meaning those three imports do not resolve through the search-path mechanism this deliverable built.
- **Consequence:** Provably bounded today — all three importers are inside the `plan-marshall` bundle, so no cross-bundle reference and no module edge is affected (confirmed by the report's own measurement: 72/10 unchanged with and without this directory). But the gap is structural, not just a one-off miss: any future bundle whose package-style directory is imported bare from a *different* bundle would silently fail to resolve, with no note explaining why.
- **Action:** Either special-case `platform-runtime/scripts` (or any directory reachable by a real bare import despite carrying `__init__.py`) into `extraPaths`, or emit a distinguishable note (analogous to `ambiguous-module-name`) when a bare import targets a directory the structural rule excluded, so a future cross-bundle case is visible rather than silently unresolved.
- **Done when:** A test constructs a synthetic tree with a package-style directory (has `__init__.py`) imported bare from a *different* bundle's file, and asserts either the reference resolves or a named note explains why it did not — never a silent `unresolved-symbol` indistinguishable from an unrelated failure.
- **Effort:** S
- **Risk if fixed:** Very low — this is an edge case with a proven-zero blast radius today; the fix is additive.

## G4 — CI-portability figures in the run report were never independently reproduced

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** ci-portability-verification-debt
- **Where:** `report-01.md` § Build gate → CI portability (the two-row table: `662 passed, 10 skipped` with pyright hidden on current code; `53 failed, 10 passed, 1 skipped` with pyright hidden against reverted code).
- **Evidence:** `report-01.md` § Left open: *"§ Build gate's CI-portability row 1 (`662 passed, 10 skipped`) does not name its population, and none of the four populations round 5 tried reproduced it — unverifiable, not proven false; row 2 … need[s] a detached worktree with hand-adapted pre-change test copies, which round 5 did not reconstruct."* This audit did not attempt to reproduce it either (out of scope for a read-only audit run without a hidden-`pyright` CI environment), so the figure remains unverified by **two** independent audits now.
- **Consequence:** This is the plan's own designated "CI portability is itself a check" verification item (§ Verification, item 2) — the one guaranteeing the new guards are falsifiable without a locally-installed language server. If the underlying population is smaller than claimed, or the reverted-code failure count is inflated by unrelated pre-existing skips, the plan's central "a guard only a locally-installed binary can falsify does not protect CI" claim would be weaker than reported, though nothing so far contradicts it.
- **Action:** Re-run the CI-portability sweep (hide `pyright-langserver` from `PATH`, run the affected suites, then run the five new/changed guard modules against `origin/main` pre-`cdf8062`) and publish the population each figure was drawn from (which test paths, how many collected, how many `skipif`-guarded), per the plan's own population-honesty standard.
- **Done when:** A CI job (or a documented reproducible local recipe) runs this exact sweep and the resulting counts are recorded with the command and the population, replacing the currently-unverified figures.
- **Effort:** S
- **Risk if fixed:** None — this is pure measurement, not a behaviour change.

## G5 — Round 11's `setup.cfg` fix was never re-checked by an independent verification round

- **Kind:** test-gap
- **Severity:** low
- **Topic:** verification-loop-tail-coverage
- **Where:** `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py:462-520` (`_read_setup_cfg`, the interpolation-stays-on remedy).
- **Evidence:** `report-01.md` § Independent re-check of round 9's fixes, and what carries NO independent verification: *"Round 11's own fixes, at `1c234ff`. Round 11 verified `91629f3` and found its `setup.cfg` remedy wrong; the correction … carries the run's own guards and red-check and no independent round."* This audit independently re-read the code and confirms it matches round 11's stated correction (interpolation on, reads moved fully inside the guard, all-or-nothing commit via a local dict) — but this is a code *reading*, not an execution-based re-verification of the kind rounds 7–10 used to find the two prior `setup.cfg` defects (B-1, then round 11's own correction of round 10's fix).
- **Consequence:** Given this exact function has now been wrong **twice** in this run (round 10's initial abort-on-`%` bug, then round 10's own remedy being wrong about setuptools' interpolation behaviour, corrected by round 11), it is the single highest-churn function in the branch. A third defect in the same function is disproportionately likely relative to the rest of the shipped surface, and nothing beyond code-reading has re-verified it since round 11.
- **Action:** Run one targeted execution-based verification pass (a plan-verifier-style dispatch, or manual reproduction) against `_read_setup_cfg` specifically: feed it the three input classes named in round 11's docstring (interpolated `%(version)s`, escaped `%%`, and a bare `%` that setuptools itself rejects) plus at least one additional adversarial shape (e.g. a value containing an unmatched `%(` with no closing paren, which `ConfigParser.BasicInterpolation` may raise a different exception class for than the three currently caught).
- **Done when:** A test exists asserting `_read_setup_cfg`'s behaviour on an unmatched-`%(` value is caught by the narrowed exception set (not an uncaught `InterpolationSyntaxError` or similar), executed and green.
- **Effort:** S
- **Risk if fixed:** None — additive test coverage on a function already in its final shipped form.

## G6 — The npm-side equivalent of the D4 Python percent-sign defect remains unfixed and undersevered

- **Kind:** bug
- **Severity:** medium
- **Topic:** npm-discovery-malformed-descriptor
- **Where:** `marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_cmd_discover.py`, specifically `_resolve_workspaces` (glob/workspace resolution) and the top-level `package.json` shape assumptions in `discover_npm_modules`.
- **Evidence:** `report-01.md` § Left open, row S5, second half: *"The npm half remains open and bounded: a `package.json` whose top level is an array or string, `workspaces: [\"/etc/*\"]`, and `workspaces: [\"../*\"]` globbing outside the project root are pre-existing on `origin/main` and untouched here."* The Python-side analogue of this defect class — a single malformed value (`description = 100% pure python`) aborting **every** module's discovery, including ones that parsed perfectly — was found by this same run's round 10 and treated as the round's worst finding, fixed with two dedicated multi-module guards specifically because the blast radius was "every module in the tree, not just the malformed one." The npm-side equivalent (an array/string top-level `package.json`, or a `workspaces` glob escaping the project root) has the same shape — one module's malformed shape or a permissive glob potentially compromising or mis-scoping the whole discovery — but was not measured for blast radius in this run, only named as pre-existing and out of scope.
- **Consequence:** Unknown severity until measured: this may be a whole-tree-abort defect exactly like the Python one just fixed, or it may be scoped to one module (more like D4's `except Exception` swallow before it was narrowed). The `workspaces` glob escaping outside the project root is separately a potential path-traversal-adjacent concern (a workspace pattern resolving to `/etc/*` or `../*` reading files outside the intended tree), which is a different risk class from a crash.
- **Action:** Measure the blast radius the same way round 10 measured the Python defect: construct a multi-module npm workspace fixture where one `package.json` has a malformed top-level shape (array/string) or an out-of-root `workspaces` glob, and observe whether sibling modules' discovery is also lost. If the blast radius matches the Python case (whole-tree loss), this should be re-triaged to high severity and fixed with the same guard-per-input-class approach D4 used. If it is module-scoped, the existing disclosure suffices and this can be downgraded to a documentation-only gap.
- **Done when:** A blast-radius measurement is recorded (multi-module fixture, malformed shape on one module, assert whether siblings still discover), and either (a) a fix + regression guard lands if the radius matches the Python case, or (b) the finding is downgraded and documented if it does not.
- **Effort:** M
- **Risk if fixed:** Moderate — `_resolve_workspaces`' glob semantics are shared with legitimate monorepo layouts; a fix that restricts globs to the project root must not break existing workspace configurations that legitimately reference sibling directories via `../`.
