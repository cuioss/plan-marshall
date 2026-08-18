# Gaps — 140-project-local-artifact-provider

The plan landed substantially as specified: the bare-root `.claude` claim ships through the Axis-D seam,
the ownership ruling is recorded in four places, the consistency check enumerates the real tree (47 files,
re-derived at audit time) and dies under mutation, and the core was not edited. Six gaps remain, none of
which refutes a deliverable. One is a test-quality defect on the deliverable the plan singled out as
"the enumeration *is* the deliverable" (G1); one is a substantive coverage half-closure the shipped prose
does not warn about (G2); one is a scope statement missing from the ownership contract (G3); and three are
inaccuracies confined to the run report (G4-G6).

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
  both sides. It holds for every possible state of the production code and can only fail if the `print`
  itself is deleted. And on a green run pytest captures and discards stdout: the audit's clean run of this
  file emitted `9 passed in 4.81s` and nothing else — the `[D3] enumerated 47 files …` line appeared
  nowhere.
- **Why it matters:** the plan made the publication load-bearing — "⛔ N probes of a pure prefix function
  is ONE assertion repeated N times … the check that bites walks the actual tree and **publishes the
  population size it walked**", and D3's *Done when* is "the check enumerates rather than samples, **and
  publishes its count**". The enumeration half is real and proven (mutating the claim reddens this test).
  The publication half is satisfied only in appearance: no reader, human or CI, ever sees the number on a
  passing run, and the guard that claims to verify the publication cannot fail.
- **Action:** replace the `capsys` round-trip with a mechanism that survives a green run — e.g.
  `record_property('claude_tree_population', len(files))` (surfaced in the JUnit XML CI already collects),
  or a `pytest` `-rA`-visible summary via `request.node.user_properties`. Keep the real assertions
  (`assert files`, `assert not mismatches`) unchanged and delete the self-referential `in
  capsys.readouterr().out` check, which asserts nothing about the system under test.
- **Done when:** the file's tests pass with `capsys` no longer imported or used for the count, and the
  enumerated population size is retrievable from a passing run's machine-readable output (JUnit XML
  property or equivalent) without `-s`.
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
  `pm-plugin-development`'s module paths are built solely from `marketplace/bundles/pm-plugin-development`
  (`marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/plugin_discover.py:506-510`),
  and the crawl skips every dotfile directory
  (`marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_manage.py:362-367`, with
  `_FILES_DOTFILE_ALLOWLIST = frozenset({'.gitignore', '.editorconfig'})` at `:85`). So after this plan
  `which-module .claude/skills/x` answers `pm-plugin-development`, while `files --module
  pm-plugin-development`, `find --pattern '.claude/*'` and `search --content` still return none of those
  47 files — among them four production Python scripts (`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`,
  `.claude/skills/sync-plugin-cache/scripts/sync.py`, `…/reconcile_daemon.py`, `…/review_retrospective.py`).
  The general limit is documented at `code-intelligence.adoc:244-250` (§ "Inventory scope is not tree
  scope"), but the project-local section — the one a reader lands on for this tree — points there only for
  the "never inventoried" fact and does not say the claim leaves that half open.
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
- **Done when:** both surfaces state the attribution-vs-inventory boundary for `.claude` in their own
  words, and a reader of either can answer "does `search --content` cover `.claude/skills`?" correctly
  without leaving the section.
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
  `test/plan-marshall/manage-architecture/test_cmd_client.py:1040-1059`, a file
  `git show --stat cc923b6` does not list — it pre-dates this plan.
- **Why it matters:** the plan's § Verification makes the pair the acceptance criterion for D4 ("assert
  both; the pair is the point"). The report claims the pair at two levels; it exists at one level from
  this run, and at the other from earlier work. A later reader auditing D4's coverage will look for an
  assertion that is not there.
- **Action:** rewrite the D4 row to say the pair is asserted at the seam by this run
  (`test_path_attribution.py:174-201`) and that the reader-level 0-vs-N pair already shipped in
  `test_cmd_client.py:1040-1059`, with this run adding the N-side assertion for the `.github` control at
  `test_which_module_plan_claim.py:246-263`.
- **Done when:** the D4 row names, for each assertion, the file and whether this run added it.
- **Effort:** S
- **Risk if fixed:** none.
