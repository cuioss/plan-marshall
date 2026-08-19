# Gaps — 140-project-local-artifact-provider

The plan landed substantially as specified: the bare-root `.claude` claim ships through the Axis-D seam,
the ownership ruling is recorded in four places, the consistency check enumerates the real tree and dies
under mutation (re-run independently: 6 failed, 14 passed), and the core was not edited. Nine gaps
remain, none of which refutes a deliverable.

Three are medium, one per deliverable they sit on. **G1** is on D3, the deliverable the plan singled out
as "the enumeration *is* the deliverable": the enumeration bites, but the count it is required to publish
is observable in no run mode. **G2** is on D5: the shipped prose does not warn that the claim closes
attribution without closing inventory coverage, so `search --content` still misses `.claude` while
reporting clean coverage. **G9** is on D2 — a **false premise inside the ownership record itself**: the
docstring argues the move separates no artifact from its tests "because that split predates this claim",
and for three of the six project-local scripts it demonstrably did not.

The remaining six are low: a non-deterministic walk population (G7), a scope statement missing from the
ownership contract (G3), a misleading comment in the very fixture the run's own finding 3 corrected
(G8), and three inaccuracies confined to the run report (G4-G6).

**On the `.claude` population, since two gaps turn on it.** `git ls-files .claude` → **47** — the
report's number, correct for the tracked corpus. The walk the test performs is a live filesystem
`rglob`, which at adversarial-review time read **52**: the 47 tracked files plus git-ignored
`.claude/settings.local.json` and four `__pycache__/*.pyc` artifacts. No tracked file moved between the
audit and this review (`git diff` over the audited surface is empty), so the delta is build state alone.

## G1 — Make D3's published count observable, and drop the self-referential assertion

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py:131-132`, in
  `test_every_path_under_the_real_claude_tree_resolves_to_pm_plugin_development`
- **Evidence:** the last two statements of the test are

  ```python
  print(f'[D3] enumerated {len(files)} files under {claude_root}, all resolve to {_PM_PLUGIN_DEV}')
  assert f'enumerated {len(files)} files' in capsys.readouterr().out
  ```

  The assertion reads back the test's own `print` from the line above, with `len(files)` interpolated on
  both sides. `files` is a local derived from a filesystem walk (`:117`), so no state of the production
  code can make the two sides disagree; the statement can only fail if the `print` itself is edited.
  Re-derived independently at adversarial review, three ways:

  1. `uv run python -m pytest test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py -o addopts="" -q`
     emitted `9 passed` and nothing else — no `[D3] enumerated … files …` line.
  2. Adding `-s` does **not** surface it either. `capsys` installs its own fixture-level capture even
     when global capturing is off, and `readouterr()` **drains** the buffer, so the text reaches neither
     the terminal nor pytest's "Captured stdout call" section. Confirmed with a two-line probe
     (`print("HELLO-MARKER")` → `readouterr()` → failing assert): the failure report showed the marker
     only inside the assertion's own repr, and no captured-stdout section was emitted. The one flag a
     developer would reach for to see the number is therefore also unable to show it.
  3. Under the mutation sweep the test dies at `assert not mismatches` (`:129`) and never reaches the
     `capsys` line — so the `capsys` assertion is not what bites, even on the run where the test fails.
- **Why it matters:** the plan made the publication load-bearing — "⛔ N probes of a pure prefix function
  is ONE assertion repeated N times … the check that bites walks the actual tree and **publishes the
  population size it walked**", and D3's *Done when* is "the check enumerates rather than samples, **and
  publishes its count**". The enumeration half is real and proven (mutating the claim reddens this test).
  The publication half is satisfied only in appearance: no reader, human or CI, ever sees the number on a
  passing run, and the guard that claims to verify the publication cannot fail.
- **Action:** delete the `assert … in capsys.readouterr().out` statement and the `capsys` fixture
  parameter — it asserts nothing about the system under test — and keep the real assertions
  (`assert files`, `assert not mismatches`) unchanged. Then give the count a channel that survives a
  green run: `record_property('claude_tree_population', len(files))`.
  ⛔ **Do not justify that as "the JUnit XML CI already collects"** — this repository collects none.
  `pyproject.toml:110` sets `addopts = ["-v", "--tb=short", "--strict-markers", "--strict-config",
  "--durations=25"]` with no `--junitxml` and no `junit_family`, and the CI `verify` job delegates to an
  external reusable workflow (`.github/workflows/python-verify.yml:43`) whose collection behaviour is not
  inspectable from this repository. So the property must be paired with a run that actually requests the
  XML, and the fixing run must demonstrate that pairing rather than assume it.
- **Done when:** `capsys` appears nowhere in
  `test_every_path_under_the_real_claude_tree_resolves_to_pm_plugin_development`; the file's tests still
  pass; and running it with `--junitxml` produces an XML in which a `<property name="claude_tree_population" …>`
  element carries the walked count — demonstrated by pasting that element into the fixing run's report.
- **Effort:** S
- **Risk if fixed:** none to production behaviour; the test's fixture signature changes, so any sibling
  test copying this pattern should be checked for the same defect.

## G2 — State, at the claim site, that ownership does not put `.claude` into the inventory

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/concepts/code-intelligence.adoc:202-210` (§ "The project-local artifact tree, and the
  silent fallback it closes") and
  `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/SKILL.md:99-126`
  (§ Project-Local Artifact Ownership)
- **Evidence:** the adoc section frames the cost as "A caller obeying the structured-queries-first rule
  asked `which-module` for an unclaimed one, got `module: null` … fell back to a whole-tree scan …
  and every such query paid whole-tree prices", then closes with "The bare-root claim covers every
  subtree, present and future, uniformly". What the claim covers is *attribution only*.
  `pm-plugin-development`'s module paths are built from the bundle directory plus
  `test/pm-plugin-development` — there is no `.claude` entry among them
  (`marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/plugin_discover.py:503-512`),
  and the crawl skips every dotfile directory
  (`marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_manage.py:362-369`, with
  `_FILES_DOTFILE_ALLOWLIST = frozenset({'.gitignore', '.editorconfig'})` at `:85`). So after this plan
  `which-module .claude/skills/x` answers `pm-plugin-development`, while `files --module
  pm-plugin-development`, `find --pattern '.claude/*'` and `search --content` still return none of those
  47 tracked files — among them **six** production Python scripts (re-derived from the tree):
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`,
  `.claude/skills/finalize-step-era-stamp-fill/scripts/era_stamp_fill.py`,
  `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`,
  `.claude/skills/sync-plugin-cache/scripts/list_bundles_and_versions.py`,
  `…/sync-plugin-cache/scripts/reconcile_daemon.py`, and `…/sync-plugin-cache/scripts/sync.py`.
  `CLAUDE.md` itself states the limit for callers ("dotfile trees outside the allowlist (`.claude/**`,
  `.github/**`) are **not** searched"), which is why the omission is in the *substrate* docs, not in the
  house rules.
  The general limit is documented at `code-intelligence.adoc:244-250` (§ "Inventory scope is not tree
  scope"), but the project-local section — the one a reader lands on for this tree — points there only for
  the "never inventoried" fact and does not say the claim leaves that half open.

  **Demonstrated live, not inferred.** This clone has a populated `.plan/project-architecture/`, so the
  readers were executed rather than read:

  ```text
  which-module --path .claude/commands/x.md   → module: pm-plugin-development, attributor_count: 3
  files --module pm-plugin-development        → 0 rows matching '.claude'
  find --pattern '.claude/**'                 → count: 0, truncated: false
  search --content --pattern 'parse_metrics_end_time_presence'
        → count: 11, file_count: 8, files_scanned: 5543, unreadable[0], truncated: false
  ```

  That last one is the sharp case. `parse_metrics_end_time_presence` is **defined** at
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:1139`, and the sweep returns its
  three *consumers* under `test/` and five `doc/plans/` mentions — but never the defining file, while
  reporting the clean coverage metadata (`unreadable[0]`, `truncated: false`) that `client-api.md`
  § search makes the licence for treating a result as complete.
- **Why it matters:** a reader of the ownership contract concludes the whole-tree-scan cost for `.claude`
  is closed. It is closed for the "who owns this path?" question and open for the "which files does this
  module hold?" and "which file contains X?" questions — the ones that actually trigger the expensive
  scan the epic exists to eliminate. An owner with no enumerable files is also an inconsistency a later
  reader will trip over on its own.
- **Action:** add one paragraph to `code-intelligence.adoc` § "The project-local artifact tree" and one
  sentence to SKILL.md § Project-Local Artifact Ownership stating that the claim is an *attribution*
  claim: `which-module` answers for `.claude/**`, while `files`/`find`/`search --content` do not cover it
  because the crawl excludes dotfile trees, with an `xref:` to § "Inventory scope is not tree scope".
  Name the consequence explicitly (a caller enumerating this module's files, or searching their content,
  must still read the tree directly).
- **Done when:** each of the two surfaces contains a sentence that names `search --content` (or
  `files`/`find`) and states it does **not** cover `.claude`, without requiring the reader to follow a
  cross-reference to learn it; and the `code-intelligence.adoc` addition carries an `xref:` to
  § "Inventory scope is not tree scope".
- **Effort:** S
- **Risk if fixed:** none — additive prose. If a later plan instead *closes* the gap by inventorying the
  tree, the paragraph must be retired with it.

## G3 — Say in the ownership contract that the claim's benefit is meta-project-only

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/SKILL.md:119-122`
  and the mirroring paragraph at
  `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/extension.py:341-346`
- **Evidence:** both records say the module-existence guard drops the claim in a consumer project
  "so no consumer-project behaviour changes" — accurate, and verified
  (`merge_path_claims` drops unknown-module claims at
  `marketplace/bundles/plan-marshall/skills/extension-api/scripts/_path_attribution_merge.py:293-298`;
  pinned by `test_path_attribution.py:158-166`). What neither says is the corollary: a consumer project's
  own `.claude/**` tree therefore still resolves to `module: null` with `attributor_count: N` — exactly
  the silent-fallback condition the plan set out to end — because the claim names a module that exists
  only in this repository.
- **Why it matters:** the bundle ships to consumers. A consumer-project reader of this contract can
  reasonably infer their `.claude` tree is now attributed; it is not, and there is no hint about what
  they would do instead (claim it from one of their own modules' attributors).
- **Action:** extend the "Inert where it should be" paragraph in both records with one sentence: the
  claim resolves only where a `pm-plugin-development` module exists (this marketplace repository), and a
  consumer project that wants its project-local tree attributed declares its own Axis-D claim naming one
  of its modules, per `ext-point-path-attribution.md`.
- **Done when:** SKILL.md § Project-Local Artifact Ownership names both the inertness and the
  consumer-side remedy, and the `claim_paths()` docstring carries the same sentence.
- **Effort:** S
- **Risk if fixed:** none — additive prose in a docstring and a SKILL.md section.

## G4 — Replace the unresolvable branch SHAs in the run report's deliverable table

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/140-project-local-artifact-provider/report-01.md:37-41`
  (the "Commit" column) and `:60-62` (the findings table)
- **Evidence:** the report cites `935eaca`, `eef6a02` and `f741ba0`. In a fresh clone,
  `git cat-file -t 935eaca` → `fatal: Not a valid object name 935eaca`, and the same for the other two.
  The PR was squash-merged, so the only reachable object is `cc923b6`
  ("feat(pm-plugin-development): own the project-local .claude tree via Axis-D (#1208)").
- **Why it matters:** the report is the durable record of this run, and the column that is supposed to let
  a later reader locate each change points at objects that do not exist in any clone. Every claim in the
  table becomes uncheckable by the route the table offers.
- **Action:** replace the branch SHAs with the merge commit `cc923b6` (or with `PR #1208` plus that SHA),
  keeping the per-deliverable rows otherwise unchanged. If per-commit granularity matters to the record,
  state it in words ("three commits on the branch, squashed as `cc923b6`") rather than by hash.
- **Done when:** every SHA in `report-01.md` resolves via `git cat-file -t` in a fresh clone of `main`.
- **Effort:** S
- **Risk if fixed:** none. If this is systemic across lane reports, the durable fix belongs in the
  `cloud-plan-lane` report template rather than in this one file.

## G5 — Correct the build-gate footprint count in the run report

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/140-project-local-artifact-provider/report-01.md:47`
- **Evidence:** "`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (two `extension.py`,
  **two test files** under plan-marshall + pm-plugin-development)". The merged diff
  (`git show --stat --format="" cc923b6`) carries four `*.py` test files:
  `test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py` (new, 217 lines),
  `test/plan-marshall/extension-api/test_path_attribution_merge.py`,
  `test/plan-marshall/manage-architecture/test_files_inventory.py`, and
  `test/plan-marshall/manage-architecture/test_which_module_plan_claim.py`. The report's own findings
  table (`:62`) and build-gate note (`:50`) record edits to two of the three it leaves out, so the
  document contradicts itself.
- **Why it matters:** the build-gate section is the record of *what the gate covered*. An understated
  footprint makes the gate look narrower than it was and invites a later reader to conclude a file went
  through unverified.
- **Action:** restate the footprint as the four test files plus the two `extension.py` files, matching
  the merged diff.
- **Done when:** the § Build gate footprint sentence enumerates the same file set as
  `git show --stat cc923b6` for `*.py`.
- **Effort:** S
- **Risk if fixed:** none.

## G6 — Correct the D4 row's claim about the which-module reader

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/140-project-local-artifact-provider/report-01.md:40`
  (deliverable table, D4 row)
- **Evidence:** the row reads "Negative-control pair asserted at the seam (attributor_count 0 vs N) **and
  at the which-module reader**." The reader-level test this run added,
  `test/plan-marshall/manage-architecture/test_which_module_plan_claim.py:246-263`, asserts only the N
  side (`assert result['attributor_count'] > 0`); there is no 0-side assertion at the reader in the PR's
  diff. The 0-vs-N pair at the reader is
  `test/plan-marshall/manage-architecture/test_cmd_client.py:1039-1061`
  (`test_which_module_residue_distinction_is_observable_without_reading_module`), a file
  `git show --stat cc923b6` does not list — it pre-dates this plan.
- **Why it matters:** the plan's § Verification makes the pair the acceptance criterion for D4 ("assert
  both; the pair is the point"). The report claims the pair at two levels; it exists at one level from
  this run, and at the other from earlier work. A later reader auditing D4's coverage will look for an
  assertion that is not there.
- **Action:** rewrite the D4 row to say the pair is asserted at the seam by this run
  (`test_path_attribution.py:174-201`) and that the reader-level 0-vs-N pair already shipped in
  `test_cmd_client.py:1039-1061`, with this run adding the N-side assertion for the `.github` control at
  `test_which_module_plan_claim.py:246-263`.
- **Done when:** the D4 row names, for each assertion, the file and whether this run added it.
- **Effort:** S
- **Risk if fixed:** none.

## G7 — Make D3's walked population deterministic

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py:117` (the `rglob`
  in `test_every_path_under_the_real_claude_tree_resolves_to_pm_plugin_development`) and `:144` (the
  `iterdir` in `test_each_top_level_claude_subtree_resolves_uniformly`)
- **Evidence:** the walk is `files = sorted(p for p in claude_root.rglob('*') if p.is_file())`, a live
  filesystem read, so the number the test publishes is whatever the working tree happens to hold.
  Re-derived at adversarial review: `git ls-files .claude | wc -l` → **47**; the same `rglob`, files
  only → **52**. The five extra entries are all git-ignored build state —
  `.claude/settings.local.json` plus `__pycache__/audit.cpython-312.pyc`,
  `__pycache__/era_stamp_fill.cpython-312.pyc`, `__pycache__/review_retrospective.cpython-312.pyc` and
  `__pycache__/reconcile_daemon.cpython-312.pyc`. `git diff` over `marketplace/`, `doc/concepts/`,
  `test/` and `.claude/` between the audit's tree state and this one is empty, so no tracked file moved:
  the delta is build state alone. `iterdir()` is affected the same way — the top-level entry list is
  `commands`, `skills`, `settings.json` in a clean clone and gains `settings.local.json` on a working
  machine.
- **Why it matters:** D3's *Done when* makes the published count the deliverable's own artifact, and the
  run report states it as a fact ("47 files"). A figure that moves with `__pycache__` state is not
  reproducible, so no later reader can check the report against a run — they will read 52 and conclude
  the record is wrong. **No assertion is weakened:** every extra entry is still under `.claude` and still
  resolves to `pm-plugin-development`, which is why this is low rather than a broken test.
- **Action:** derive the walked population from a deterministic source. Preferred: filter the `rglob`
  (skip any path with a `__pycache__` component, and any entry `git check-ignore -q` accepts) and filter
  `iterdir()` the same way. `git ls-files .claude` is the other option but gives the test a hard git
  dependency, so take it only if the suite already assumes a worktree.
- **Done when:** on a machine that has run the suite at least once (so `__pycache__` directories exist
  under `.claude`) and carries a `.claude/settings.local.json`, the count the walk test reports equals
  `git ls-files .claude | wc -l`, and both enumeration tests still pass.
- **Effort:** S
- **Risk if fixed:** a filter that is too broad could hide a real tracked file and re-open the vacuity
  the `assert files` guard at `:120` exists to prevent — keep that guard, and assert the filtered count
  is non-zero.

## G8 — Stop the merge fixture from calling its stubs "the two real attributors"

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/extension-api/test_path_attribution_merge.py:641-654`,
  `test_lookup_claim_consumes_the_merge_output_end_to_end`
- **Evidence:** lines 642-647 read

  ```python
  # Arrange — the shipped claims, produced by the real merge over the two real
  # attributors: pm-plugin-development owns the bare-root ``.claude`` tree, and
  # plan-marshall owns ``.plan``.
  pm_dev = _StubAttributor(claims=[('.claude', 'pm-plugin-development')])
  plan_marshall = _StubAttributor(claims=[('.plan', 'plan-marshall')])
  claims, _ = _merge_with(('pm-plugin-development', pm_dev), ('plan-marshall', plan_marshall))
  ```

  `_merge_with` (`:77-80`) calls the real `merge_path_claims` over those **stub** records, so "the real
  merge" is accurate but "the two real attributors" is not — nothing is discovered here, and both claim
  tuples are hardcoded. "The shipped claims" is wrong about the population too: re-derived live at
  adversarial review the shipped set is **five claims from three attributors** —
  `.claude → pm-plugin-development`, `.plan → plan-marshall`, and
  `doc`/`README.md`/`CONTRIBUTING.md → documentation` from `pm-documents`
  (`marketplace/bundles/pm-documents/skills/plan-marshall-plugin/extension.py:284-286`).
- **Why it matters:** this is the same fixture the run's own finding 3 corrected, and the run's Step-9
  lesson generalised exactly this hazard — "a test fixture or stub that hardcodes the [retired] value"
  and passes regardless because it is not driven by the real code path. The values were updated; the
  comment now asserts they *are* the real ones, which restores the property that made the original
  defect invisible. If the shipped claim set moves again, this test stays green and its comment lies.
- **Action:** rewrite the comment to say the records are stubs mirroring two of the shipped claims, and
  that this test pins `lookup_claim`'s consumption of merge output rather than the shipped claim set.
  Point at the tests that do pin the real set:
  `test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py:97-100` and
  `test/plan-marshall/manage-architecture/test_which_module_plan_claim.py:286-300`.
- **Done when:** the comment at `:642-644` no longer calls the stub records "real attributors" or "the
  shipped claims", and names at least one test that asserts against the discovered attributor
  population.
- **Effort:** S
- **Risk if fixed:** none — comment text only, no assertion changes.

## G9 — Correct the false "the split predates this claim" premise in the D2 ownership record

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/extension.py:333-339`
  — the "A split of artifacts from their tests is accepted, not introduced" paragraph of `claim_paths()`
- **Evidence:** the paragraph reads, verbatim:

  ```text
  **A split of artifacts from their tests is accepted, not introduced.** The
  project-local skills under ``.claude/skills`` have their tests under
  ``test/{skill}`` trees owned by other modules — but that split predates
  this claim (it held under ``plan-marshall`` ownership too), so the move
  does not newly separate anything. Ownership tracks who understands the
  artifact's content, which is the plugin-development domain regardless of
  where the tests live.
  ```

  The premise is false for half the population. Re-derived at adversarial review — the six production
  scripts under `.claude/skills/*/scripts/`, their covering test trees, and the owning module of each
  test tree (`which-module`, live):

  | `.claude` script | Covering tests | Test-tree module | Artifact module **before** the move | Split before? | Split now? |
  |---|---|---|---|---|---|
  | `audit-archived-plan-retrospectives/scripts/audit.py` | `test/plan-marshall/audit-archived-plan-retrospectives/` | `plan-marshall` | `plan-marshall` | **no** | **yes** |
  | `finalize-step-era-stamp-fill/scripts/era_stamp_fill.py` | `test/plan-marshall/audit-archived-plan-retrospectives/test_era_stamp_fill.py` | `plan-marshall` | `plan-marshall` | **no** | **yes** |
  | `finalize-step-review-retrospective/scripts/review_retrospective.py` | `test/plan-marshall/finalize-step-review-retrospective/` | `plan-marshall` | `plan-marshall` | **no** | **yes** |
  | `sync-plugin-cache/scripts/sync.py` | `test/sync-plugin-cache/` | `default` | `plan-marshall` | yes | yes |
  | `sync-plugin-cache/scripts/reconcile_daemon.py` | `test/sync-plugin-cache/` | `default` | `plan-marshall` | yes | yes |
  | `sync-plugin-cache/scripts/list_bundles_and_versions.py` | `test/sync-plugin-cache/` | `default` | `plan-marshall` | yes | yes |

  For three of the six, artifact and tests were both owned by `plan-marshall` before the move — the
  tests live *inside* `plan-marshall`'s own test path (`plugin_discover.py:503-512` gives every bundle
  module `tests: ['test/{bundle_name}']`), not under a `test/{skill}` tree. The move separated them. So
  the paragraph's "it held under `plan-marshall` ownership too" and "the move does not newly separate
  anything" are both wrong for that half, and its "under `test/{skill}` trees" description fits only the
  `sync-plugin-cache` half.
- **Why it matters:** the plan made this the explicit pre-condition of the move — "⚠ The artifacts'
  **tests live under a different module's test tree**, so a move may split an artifact from its tests
  across two modules — **decide whether that is acceptable before moving; it may be exactly why the
  original owner was chosen.**" D2's *Done when* is that the decision "and its reasoning" are recorded.
  The decision is recorded; the reasoning that discharges the plan's one stated risk rests on a false
  factual premise, so a future reader is told the risk did not exist rather than that it was accepted.
  ⚠ **Scope check performed, so a later run need not redo it:** this is a documentation defect only, not
  a behaviour one. `derive-verification` for `.claude/skills/**/*.py` was executed live and yields
  `compile pm-plugin-development` where it previously yielded `compile plan-marshall` — but no module's
  `sources`/`tests` paths cover `.claude` (`architecture module --module pm-plugin-development` →
  `sources: [marketplace/bundles/pm-plugin-development/skills]`, `tests: [test/pm-plugin-development]`;
  `--module plan-marshall` → its own bundle dirs plus `test/plan-marshall`; `--module default` →
  `sources: null`). So the derived command failed to cover the changed file under **both** owners, and
  the `compile` build_class derives no test command either way. Nothing regressed; only the record is
  wrong.
- **Action:** replace the paragraph's factual premise with the measured one — for the three skills whose
  tests live under `test/plan-marshall/`, this claim **does** newly split artifact from tests, and that
  is accepted because ownership tracks who understands the artifact's content — and keep the existing
  conclusion. State the accepted consequence explicitly: a `.claude` production script and its tests now
  resolve to different modules, so a per-module verification derived from the artifact's owner does not
  reach its tests.
- **Done when:** the paragraph no longer asserts that the artifact/test split predates the claim or that
  the move "does not newly separate anything"; it names the split as newly introduced for the skills
  tested under `test/plan-marshall/`; and a reader can name, from the paragraph alone, which module owns
  the tests of a `.claude/skills/*/scripts/*.py` file.
- **Effort:** S
- **Risk if fixed:** none — docstring prose. If a later plan moves the affected tests under
  `test/pm-plugin-development/` instead, this paragraph is retired with that move.
