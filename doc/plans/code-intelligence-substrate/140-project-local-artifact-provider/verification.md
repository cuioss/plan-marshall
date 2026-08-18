# Verification — 140-project-local-artifact-provider

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `62e3807` on `claude/code-intelligence-substrate-analysis-kah884` (the audited change landed on
`main` as squash commit `cc923b6`, "feat(pm-plugin-development): own the project-local .claude tree via
Axis-D (#1208)"; `git branch --contains cc923b6` lists `main`). HEAD advanced from `61a43e5` to `62e3807`
during the audit because sibling audit sessions commit on this branch; nothing in the audited surface
changed under me — every citation below was re-read at the state reported here.
**Overall verdict:** CONFIRMED WITH GAPS

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Project-local artifact claim through the seam, uniform over the surface | `pm-plugin-development` `Extension` opts into `PathAttributionBase`; `claim_paths()` returns bare-root `('.claude', 'pm-plugin-development')`; `plan-marshall` drops `.claude/skills`; no core edit | Both extensions read as claimed; live seam probe returns the single `.claude` claim; `git show --stat cc923b6` shows no `_architecture_core.py` in the diff | CONFIRMED |
| D2 | Ownership decision recorded | Move from `plan-marshall` to `pm-plugin-development`, recorded in both docstrings, SKILL.md § Project-Local Artifact Ownership, and `code-intelligence.adoc` | All four records present and mutually consistent; a cold reader can state owner and rationale from any one of them | CONFIRMED |
| D3 | Consistency verification by enumeration, publishing its count | `test_path_attribution.py` walks the real `.claude` tree (47 files), asserts every path → `pm-plugin-development`, publishes the count | The walk test exists and enumerates; mutation of the claim turns it red (re-run independently: **6 failed, 14 passed**). But the walked population is whatever is on disk, not what the repository tracks — **47 git-tracked files, 52 on disk** at adversarial-review time (`settings.local.json` plus four `__pycache__` artifacts), so the published count is build-state-dependent (G7); and the "publication" itself is a `print()` that pytest swallows on green, asserted by a self-referential `capsys` check (G1) | CONFIRMED (with two test-quality gaps, G1 and G7) |
| D4 | Resolver distinguishes "not covered" from "covered, no matches" | Reuses the shipped `attributor_count` contract; negative-control pair asserted at the seam and at the which-module reader | The pair exists at the seam (`test_path_attribution.py:174`). At the reader only the `attributor_count > 0` half was added by this run; the 0-vs-N pair at the reader lives in `test_cmd_client.py:1040`, a file this PR did not touch | CONFIRMED (report wording overstated — G6) |
| D5 | Documentation: ownership contract + `code-intelligence.adoc` row | SKILL.md § Project-Local Artifact Ownership; adoc section; `ext-point-path-attribution.md` implementations table | All three present; both relative links from SKILL.md resolve; no stale `.claude/skills → plan-marshall` statement survives anywhere outside `doc/plans/` | CONFIRMED |

## Per-deliverable detail

### D1 — project-local artifact claim through the attribution seam

- **Required (plan):** "every discovered subtree is claimed, and the claim is registered through the seam
  rather than hard-coded", with the subtree set derived from the filesystem, not from the plan.
- **Claimed (report):** bare-root `('.claude', 'pm-plugin-development')`, covering skills, commands,
  settings and any future subtree by prefix containment; `plan-marshall` keeps only `.plan`; no core edit.
- **Found:**
  - `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/extension.py:55` —
    `class Extension(ExtensionBase, DerivationResolverBase, PathAttributionBase)`.
  - `…/extension.py:293-295` — `path_attributor_id()` returns `'pm-plugin-development'`.
  - `…/extension.py:350` — `return [('.claude', 'pm-plugin-development')], []`.
  - `marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/extension.py:133` —
    `return [('.plan', 'plan-marshall')], []` (the `.claude/skills` entry is gone; `:124-131` records why).
  - Pre-change baseline re-derived: `git show cc923b6^:marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/extension.py`
    line 131 read `return [('.claude/skills', 'plan-marshall'), ('.plan', 'plan-marshall')], []` — the plan's
    founding premise is real.
- **Checks run:**
  - Filesystem population: `.claude/` holds exactly two directories — `commands/` and `skills/` — so the
    report's "Refuted" verdict on the third-*subtree* HYPOTHESIS is correct. The top-level *entry* list is
    not stable, however: it is `commands/`, `skills/`, `settings.json` in a clean clone, and
    `commands/`, `settings.json`, `settings.local.json`, `skills/` on a working machine, because
    `.claude/settings.local.json` is git-ignored machine-local state. Neither the claim nor the
    uniformity test is disturbed by that (everything under `.claude` resolves to the one owner), but the
    enumeration's *count* is — see G7.
  - Live seam probe (script under `$TMPDIR`, all bundle `scripts/` dirs on `sys.path`, calling
    `_architecture_core._load_path_attribution_seam()` directly):
    `attributors: ['documentation', 'plan-marshall', 'pm-plugin-development']`;
    `claims: [{'prefix': '.claude', 'module': 'pm-plugin-development', 'producers': ['pm-plugin-development']}, {'prefix': '.plan', …}, {'prefix': 'CONTRIBUTING.md', …}, {'prefix': 'README.md', …}, {'prefix': 'doc', …}]`;
    lookups: `.claude` / `.claude/skills/x/SKILL.md` / `.claude/commands/a.md` / `.claude/settings.json`
    → `pm-plugin-development`; `.claudex/y` → `None`; `.github/workflows/v.yml` → `None`;
    `.plan/execute-script.py` → `plan-marshall`.
  - No-core-edit constraint: `git show --stat --format="" cc923b6` lists 13 files; `_architecture_core.py`
    is not among them. The out-of-scope rule held.
- **Verdict:** CONFIRMED. The bare-root prefix is strictly stronger than the enumerated list the plan
  warned against, and the claim is discovered, not hard-coded.

### D2 — the ownership decision, made explicitly and recorded

- **Required (plan):** "the decision and its reasoning are written where a future reader will find them",
  with the conflicting readings surfaced if two exist.
- **Claimed (report):** recorded in both extensions' `claim_paths()` docstrings, the pm-plugin-development
  SKILL.md, and `code-intelligence.adoc`; the two readings do not conflict because the former owner was
  never a ruling.
- **Found:**
  - `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/extension.py:297-349` — a
    four-part docstring: the decision, why it is a decision rather than a side effect, why the bare root
    rather than an enumeration, the accepted artifact/test split, and the consumer-project inertness.
  - `marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/extension.py:124-131` — the mirror
    record on the losing side, pointing at the winner's `claim_paths`.
  - `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/SKILL.md:99-126` —
    § Project-Local Artifact Ownership.
  - `doc/concepts/code-intelligence.adoc:202-210` — § "The project-local artifact tree, and the silent
    fallback it closes", including the ruling paragraph at `:208`.
- **Checks run:** cold read of each record in isolation — each independently answers "who owns `.claude`
  and why" (`pm-plugin-development`; owner = who understands the content). The plan's "⚠ tests live under
  a different module's test tree" caution is addressed explicitly at `extension.py:334-339` ("A split of
  artifacts from their tests is accepted, not introduced"). Both relative links at SKILL.md:124-126
  resolve on disk.
- **Verdict:** CONFIRMED.

### D3 — consistency verification across the whole tree

- **Required (plan):** "the check enumerates rather than samples, and publishes its count"; derived from
  the filesystem population, not a fixed probe list.
- **Claimed (report):** `test_path_attribution.py` enumerates the real `.claude` tree (47 files) and
  asserts every path → `pm-plugin-development`, publishing the count; each top-level subtree asserted
  uniform; reader-level test in `test_which_module_plan_claim.py`.
- **Found:**
  - `test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py:108-132` — walks
    `PROJECT_ROOT/'.claude'` with `rglob('*')`, guards against a vacuous zero-file walk at `:120`,
    collects mismatches, prints the count at `:131`.
  - `…:135-150` — each top-level entry derived from `claude_root.iterdir()`, asserted uniform.
  - `test/plan-marshall/manage-architecture/test_which_module_plan_claim.py:226-243` — the same closure
    at the `cmd_which_module` reader for skills / commands / settings.
- **Checks run:**
  - Population re-derived independently, twice. `git ls-files .claude | wc -l` → **47**, matching the
    report's number. The *filesystem walk the test actually performs*
    (`rglob('*')`, files only) → **47 at audit time, 52 at adversarial-review time**; the five extra
    entries are `.claude/settings.local.json` and four `.pyc` files under `__pycache__`, all git-ignored
    and all created by concurrent sessions after the audit measured. `git diff 62e3807 HEAD` over
    `marketplace/`, `doc/concepts/`, `test/` and `.claude/` is empty, so no tracked file moved — the
    delta is build state alone. The report's "47" is therefore right about the tracked corpus and the
    test's published count is right about neither corpus reliably (G7).
  - Non-vacuity proved by mutation. Snapshot of
    `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/extension.py` written to
    `$TMPDIR/.../verify-140-mutsweep/pmpd_extension.py`; claim narrowed to `('.claude/skills', …)`;
    `uv run python -m pytest test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py
    test/plan-marshall/manage-architecture/test_which_module_plan_claim.py -o addopts="" -q` →
    **6 failed, 14 passed**, including
    `test_every_path_under_the_real_claude_tree_resolves_to_pm_plugin_development` and
    `test_each_top_level_claude_subtree_resolves_uniformly`. File restored from the byte snapshot (not
    via git); `git status --porcelain` shows the file unmodified.
  - Green baseline after restore: the three attribution test files → **61 passed in 0.77s**;
    `test_files_inventory.py` → **33 passed**.
- **Verdict:** CONFIRMED for the enumeration; the *publication* half is nominal only — see G1.

### D4 — "not covered" distinct from "covered, no matches"

- **Required (plan):** "an uncovered path produces a distinct, named result that a caller can branch on",
  reusing the coverage contract already shipped in this epic rather than inventing a second one.
- **Claimed (report):** reuses `attributor_count`; "Negative-control pair asserted at the seam
  (attributor_count 0 vs N) **and at the which-module reader**."
- **Found:**
  - `test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py:174-201` — the seam-level
    pair: `merge(discover(), known)` → non-empty reports with `lookup(...) is None`, versus `merge([], known)`
    → empty reports with `lookup(...) is None`, closing with
    `assert len(covered_reports) != len(not_covered_reports)`.
  - `…:204-217` — the positive control (a `.claude` path resolves while `.github` stays null through the
    same seam).
  - `test/plan-marshall/manage-architecture/test_which_module_plan_claim.py:246-263` — at the reader,
    only the N side: `assert result['attributor_count'] > 0`.
  - The 0-vs-N pair at the reader is `test/plan-marshall/manage-architecture/test_cmd_client.py:1040-1059`,
    a file **not** in `git show --stat cc923b6` — it pre-dates this plan.
  - Contract surface (all pre-existing, correctly reused, not duplicated):
    `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:1032`
    (`'attributor_count': len(attributor_reports)`), `…/standards/client-api.md:808-809`,
    `…/extension-api/standards/ext-point-path-attribution.md:92-93`.
- **Checks run:** read `cmd_which_module` end to end
  (`_cmd_client_handlers.py:930-1040`) to confirm the seam runs unconditionally on every call, so the
  provenance pair is present on every response shape rather than only on rung-3 fallthrough.
- **Verdict:** CONFIRMED against the literal *Done when* — but with two qualifications recorded as gaps:
  the report's "and at the which-module reader" overstates what this run added (G6), and the discriminator
  reused separates *capability presence* from *capability absence*, which in this repository is a constant
  3 for every path (see § Correctness review and G2).

### D5 — documentation

- **Required (plan):** the ownership contract in the plugin-development bundle, and the project-local
  attribution row in `doc/concepts/code-intelligence.adoc`.
- **Claimed (report):** SKILL.md § Project-Local Artifact Ownership; adoc row + prose; the
  current-implementations table and Overview/Declaration in `ext-point-path-attribution.md`.
- **Found:**
  - `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/SKILL.md:96-97` (Extension API
    table rows for `path_attributor_id` / `claim_paths`) and `:99-126` (the contract section).
  - `doc/concepts/code-intelligence.adoc:173` (the Axis-D framing sentence naming
    `pm-plugin-development` for `.claude/**`) and `:202-210` (the dedicated section).
  - `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-path-attribution.md:139`
    — the "Project-local artifact tree" implementations row; `:9` and `:17` carry the same attribution in
    the overview and the declaration-site rationale.
  - The two collateral fixes the report records as findings are present:
    `doc/concepts/extension-architecture.adoc:29` now reads "`plan-marshall` claims `.plan`,
    `pm-plugin-development` the `.claude` project-local tree, and `pm-documents` the doc corpus", and
    `:31` includes `pm-plugin-development` in the straddle roster;
    `doc/resources/diagrams/extension-topology.svg:144-145` reads `3 impls · Active` /
    `claims: .plan · .claude · doc (Axis-D)`.
- **Checks run:** repo-wide sweep for a surviving stale attribution
  (`grep -rn "\.claude/skills.*plan-marshall" --include=*.md --include=*.adoc --include=*.svg doc/ marketplace/`,
  excluding `doc/plans/`) returns only the two *historical* sentences that deliberately narrate the move
  (`code-intelligence.adoc:208`, `SKILL.md:116`) plus unrelated path-resolution references. The
  Extension-API method table has no drift: the class declares 11 public hooks and the table lists the
  same 11.
- **Verdict:** CONFIRMED.

## Correctness review

I read the shipped attributor, both consuming seam functions, and the reader that surfaces the residue:
`marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/extension.py` (whole file),
`marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/extension.py:110-133`,
`marketplace/bundles/plan-marshall/skills/extension-api/scripts/_path_attribution_merge.py` (whole file),
`marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:1100-1211`,
and `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:900-1040`.

**No defect in the code this plan shipped.** Specific hazards checked and cleared:

- *Prefix leak.* `lookup_claim` (`_path_attribution_merge.py:399`) matches
  `path == prefix or path.startswith(prefix + '/')`, so `.claudex/thing` and the repo's real
  `marketplace/bundles/*/.claude-plugin/plugin.json` cannot resolve through the `.claude` claim. Verified
  live: `.claudex/y → None`.
- *Root-ish / traversing claim.* `.claude` is neither, so it survives `_normalize_prefix`
  (`_path_attribution_merge.py:114-119`) intact.
- *Collision.* No other attributor claims `.claude` — the live merge reports
  `producers: ['pm-plugin-development']` and `claim_count: 1`, so the ambiguous-ownership branch
  (`_path_attribution_merge.py:305-327`) is not entered.
- *Module-existence guard.* `merge_path_claims` drops a claim whose module is not in `module_names`
  (`:293-298`), so the claim is inert in a consumer project. Pinned by
  `test_path_attribution.py:158-166` and `test_files_inventory.py:741-753`.
- *Rung ordering.* The claim sits at rung 3, below exact-inventory and sources/tests containment
  (`_cmd_client_handlers.py:1010-1024`), so it cannot outrank a module that actually declares a path
  under `.claude`.
- *Fail-open.* `resolve_path_attribution` degrades to `(None, [])` only on `ImportError`
  (`_architecture_core.py:1171-1174`); a misconfigured resolver still raises. Pre-existing, unchanged.

**One structural observation, not a code defect** (recorded as G2): `attributor_count` discriminates
"no attribution capability ran" from "attributors ran". In this repository the live attributor population
is a constant 3, so **every** unclaimed path — `.github/**`, `.vscode/**`, an arbitrary untracked file —
answers `module: null, attributor_count: 3`. The zero branch is reachable in the tests only by handing
`merge()` an empty attributor list (`test_path_attribution.py:196`), never through the live path. And the
claim does not put `.claude` into any module's *inventory*: `plugin_discover.py:506-510` builds
`pm-plugin-development`'s `paths` from `marketplace/bundles/pm-plugin-development` only, while the crawl
skips every dotfile directory (`_cmd_manage.py:362-367`, allowlist `_FILES_DOTFILE_ALLOWLIST` =
`{'.gitignore', '.editorconfig'}` at `:85`). So `which-module` now answers for `.claude/**` while
`files --module pm-plugin-development`, `find`, and `search --content` still cannot see those 47 files —
including four production Python scripts under `.claude/skills/*/scripts/`. That is the half of the
plan's own headline cost ("every query against an unclaimed path pays whole-tree prices") the plan did
not scope, and the shipped prose does not say so at the point a reader would over-read it.

## Test adequacy

| Deliverable | Covering tests | Non-vacuity evidence |
|---|---|---|
| D1 | `test_path_attribution.py:87-101` (opt-in, id, exact claim); `test_which_module_plan_claim.py:266-300` (live merge yields `.plan` only for plan-marshall, `.claude` only from pm-plugin-development) | Mutation of `claim_paths()` → `test_claims_the_bare_claude_root` and `test_claude_tree_moved_to_pm_plugin_development` both red |
| D2 | Not test-covered by design — verified by cold read (above) | n/a |
| D3 | `test_path_attribution.py:108-132`, `:135-150`, `:153-155`, `:158-166`; `test_which_module_plan_claim.py:226-243`; `test_files_inventory.py:708-770` | Mutation to `.claude/skills` → 6 tests red across two files, incl. both enumeration tests |
| D4 | `test_path_attribution.py:174-201` (seam pair), `:204-217` (positive control); `test_which_module_plan_claim.py:246-263` (reader, N side only) | The seam pair is real but weak: its `not_covered` arm is constructed by passing `merge([])` a synthetic empty list, so it exercises the contract, not the product's behaviour on any real path |
| D5 | Indirectly by plugin-doctor (`broken-relative-link`), not re-run here; both SKILL.md links verified to resolve by hand | n/a |

**One tautological guard.** `test_path_attribution.py:131-132`:

```python
print(f'[D3] enumerated {len(files)} files under {claude_root}, all resolve to {_PM_PLUGIN_DEV}')
assert f'enumerated {len(files)} files' in capsys.readouterr().out
```

The assertion checks the test's own `print` two lines above, with `len(files)` on both sides — it cannot
fail for any state of the production code, and it is the only thing standing behind the plan's "publishes
its count". Worse, on a green run pytest captures and discards that output: the audit's own clean run
printed `9 passed in 4.81s` and nothing else, so the count is not observable by anyone. See G1.

## Report accuracy

Every substantive claim in `report-01.md` was re-checked against the tree. **Held:**

- The founding-premise table: pre-change `plan-marshall` claimed both `.claude/skills` and `.plan`
  (verified at `cc923b6^`); `.claude` has no third subdirectory (verified by listing); the hard-coded
  prefix map is absent from core (verified by reading `_architecture_core.py:1100-1211` and by the
  absence of core from the PR diff); `pm-plugin-development` implements `discover_modules` (`extension.py:182`).
- "the only test asserting the `.claude/skills → plan-marshall` claim is `test_which_module_plan_claim.py:188`" —
  `git show cc923b6^:…/test_which_module_plan_claim.py` line 188 reads
  `assert prefixes == ['.claude/skills', '.plan']`. Exact.
- "No production code branches on `.claude/skills → plan-marshall` specifically" — a repo-wide grep for
  `.claude/skills` in `marketplace/**/*.py` returns only *path-resolution* consumers (executor generation,
  skill discovery, manifest validation); none reads a `which-module` answer.
- "47 files" — re-derived independently today: 47.
- Findings 1, 2 and 3 are all present in the tree as described (`extension-architecture.adoc:29,31`;
  `extension-topology.svg:144-145`; `test_path_attribution_merge.py:641-654`).
- "No core edit" — confirmed by the merge commit's file list.
- Contract-check row "3 Plan directory" — `plan.md` exists and opens with the first-instruction block.

**Stale, overstated, or internally inconsistent:**

1. *(low, G6)* D4 row: "Negative-control pair asserted at the seam (attributor_count 0 vs N) **and at the
   which-module reader**." At the reader this run added only the `attributor_count > 0` half
   (`test_which_module_plan_claim.py:262`). The 0-vs-N pair at the reader is in `test_cmd_client.py:1040-1059`,
   which the PR did not touch.
2. *(low, G5)* § Build gate: "two `extension.py`, **two test files** under plan-marshall +
   pm-plugin-development". The merged diff carries **four** test files
   (`test_path_attribution.py` new, plus `test_path_attribution_merge.py`, `test_files_inventory.py`,
   `test_which_module_plan_claim.py`), and the report's own findings table records edits to two of the
   three it omits.
3. *(low, G4)* Every "Commit" cell cites a branch SHA (`935eaca`, `eef6a02`, `f741ba0`). All three are
   unreachable in a fresh clone (`git cat-file -t` → "Not a valid object name") because the PR was
   squash-merged as `cc923b6` and the branch deleted. A later reader cannot resolve any of them.
4. *(low)* D2 row: "Verified by the sub-agent cold-read (below)" — no cold-read record appears below;
   the only trace is one sentence after the findings table. Not false, but the pointer does not land.
5. *(low)* The plan's § Notes obliges a **file-set** collision check before running concurrently with the
   other plugin-development plans. The report records no such check anywhere. No harm is observable in
   the tree, so this is a process-record omission only.

Claims I could **not** check: `mypy 396 files clean`, `ruff clean`, plugin-doctor marketplace-wide
`0 issues`, `16342 passed / 1 skipped` for plan-marshall, `2241 passed` for pm-plugin-development, the
reviewer-participation table, and the wall-clock/cost figures. All are point-in-time measurements of a
build I was directed not to run; they are UNVERIFIABLE here rather than refuted.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| Full-suite `./pw verify` not run whole locally; delegated to CI's required `verify` check and the merge queue | **Closed** | The PR landed: `cc923b6` is on `main` (`git branch --contains cc923b6`), which the merge queue admits only on a green required check |
| `coderabbitai` / `sourcery-ai` may re-review once their rate-limit windows reopen | **Moot** | The PR is merged; a post-merge review would have no merge-gate effect. No later commit in the tree references PR #1208 review feedback |
| § What have we learned: proposed `cloud-plan-lane` Step-6 amendment (name "a test fixture/stub that hardcodes the retired value and still passes" as a consumer kind, and grep `*.py` fixtures) — explicitly *not shipped in this run*, pending operator approval | **Closed by a later change** | `.claude/skills/cloud-plan-lane/SKILL.md:611` now lists "a test fixture or stub that hardcodes the value"; `:619-623` narrates this exact run's `_StubAttributor` evidence; `:635-636` extends the sweep to "test fixtures and stubs (`*.py`) AND prose-bearing string literals in production code" |

## Out-of-scope and collateral

- **"Editing the architecture core" — respected.** `_architecture_core.py` and every other
  `manage-architecture` script are absent from `git show --stat cc923b6`. The escape clause ("if this plan
  finds itself editing core, loop back and report") was not triggered.
- **"Fixing a consuming project's own inventory data" — respected.** No consumer-side data touched.
- **"Changing how these paths are classified by the bookkeeping-prefix logic" — respected.**
  `classify_changed_path` and its prefix logic are untouched by the diff.
- **Collateral, declared:** `doc/concepts/extension-architecture.adoc` and
  `doc/resources/diagrams/extension-topology.svg` were edited outside the plan's § Expected surface, but
  both are disclosed in the report's findings table as sub-agent findings 1 and 2, and both edits are
  corrections made necessary by the move.
- **Collateral, undeclared in § Expected surface but declared in the report:**
  `test/plan-marshall/extension-api/test_path_attribution_merge.py` and
  `test/plan-marshall/manage-architecture/test_files_inventory.py` (finding 3 and the build-gate row).
  Nothing in the diff is undisclosed.

## Method and coverage

**Checked, and how.** Read `plan.md` and `report-01.md` in full, then the epic README. Located the landed
change as squash commit `cc923b6` and read its file list and message. Read both `extension.py` files in
full, the merge helper in full, the rung-3 core functions, and `cmd_which_module`. Read all four touched
test files and the doc surfaces (SKILL.md, `code-intelligence.adoc`, `ext-point-path-attribution.md`,
`extension-architecture.adoc`, the SVG). Re-derived the `.claude` population (47) and its top-level
entries from the filesystem. Executed the live Axis-D seam out-of-band (custom `sys.path`, no
`.plan/execute-script.py`) to observe the real attributor roster, the real merged claim set, and eight
lookups. Ran four test files under `uv run python -m pytest … -o addopts=""` (94 tests, all green).
Proved non-vacuity by mutating `claim_paths()` to the retired `.claude/skills` prefix and observing 6
failures across two files; restored the file from a byte snapshot taken under `$TMPDIR` and confirmed
`git status --porcelain` clean for it. Verified the pre-change baseline through `git show cc923b6^:…`
for both the extension and the test the report cites by line.

**Not checked, and why.** The build/CI numbers in § Build gate (`./pw verify`, `quality-gate`,
per-module test counts, mypy/ruff/plugin-doctor) — the audit brief forbids running the full suite, and
those figures are point-in-time measurements of a tree that has since advanced. The reviewer-participation
table and the PR comment surfaces — not reachable without querying GitHub, and outside the "does the tree
contain what was promised" question. `search --content` / `find` behaviour was derived by reading the
crawl walker rather than executed, because `.plan/project-architecture/` does not exist in this clone.

**Search-reliability note.** Every "grep found nothing" verdict above was preceded by a positive control:
the stale-attribution sweep pattern was first confirmed to match the known-good historical sentences at
`code-intelligence.adoc:208` and `SKILL.md:116` before its silence elsewhere was treated as evidence.

**Working-tree hygiene.** No repository file was modified by this audit other than the two files this
brief creates. The one mutation was reverted from an audit-owned byte snapshot, never with
`git checkout`/`restore`/`stash`. Other unstaged modifications visible in `git status` during the audit
belong to concurrent sibling sessions on this branch and were neither touched nor relied upon.
