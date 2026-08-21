# Run report — 030-claude-literal-residuals (run 01)

**Date (UTC):** 2026-08-21    **Branch:** `claude/claude-literal-residuals-tcyauu`    **PR:** [#1319](https://github.com/cuioss/plan-marshall/pull/1319)    **Outcome:** completed

> **Verification loop exit:** `verifier-clear`

## Skills loaded

Loaded via the plugin notation where it resolved, else by bundle path — the route is recorded
because the `plan-marshall` plugin is often absent in a cloud session.

| Skill | Route | When |
|---|---|---|
| `cloud-plan-lane` | `Skill: cloud-plan-lane` (project-local, resolved) | first action |
| `plan-marshall:ref-code-quality` | bundle path | Step 1 |
| `pm-plugin-development:plugin-script-architecture` | bundle path | Step 1 |
| `pm-dev-python:python-core` | bundle path | conditional — Python production code |
| `pm-dev-python:pytest-testing` | bundle path | conditional — Python tests |

Stated precisely, because "loaded" can be read wider than it is: for each of the four bundle-path
skills the `SKILL.md` was read. All four are **reference-mode** skills that index further
standards under `standards/`, and those sub-documents were **not** read — the changed files sit
inside an established house style and every edit follows the surrounding module's own
conventions. That is a choice, not a claim that the standards were consulted.

`plan-marshall:persona-implementer` and `pm-plugin-development:plugin-architecture` were **not**
loaded. The first is a work-identity persona the lane lists for production code; the second
governs `SKILL.md`/bundle structure, and this run's two `SKILL.md` edits are single table rows in
existing tables, not structural changes. Both omissions are disclosed rather than argued away.

No skill was unobtainable by both routes.

## Deliverables

Commits are named by subject rather than SHA throughout this report, because the branch was rebased
onto `main` before the PR and a rebase replaces every replayed commit's object id — a quoted SHA
would cite a commit on no branch under review. That choice is why the rebase needed no citation
remapping: there was no same-branch SHA anywhere to go stale.

**What the rebase picked up.** The operator asked for it in order to fetch a test-restructuring PR
(#1314, the module-budget campaign). At the first rebase that PR **had not merged**, so what came in
was three unrelated documentation commits; it merged afterwards and a second rebase took it. Both
were clean, and re-derived so: the intersection of #1314's 281 changed files with this branch's is
**empty**. § Build gate records both gate runs, and the order-independence check the second one
warranted.

### D1 — Default permissions render in the runtime

**Done.** `permission_fix.py` no longer declares `DEFAULT_PERMISSIONS` or `add_default_permissions`.
`cmd_apply_fixes` states the goal through `permission_common.ensure_default_permissions`, which
delegates to `claude_runtime.ensure_default_permissions`: the runtime renders the rules from
`_default_permission_rules()`, merges them, sorts the allow list, performs the write, and returns
`{'defaults_added': [semantic ids], 'defaults_added_count': int, 'applied': bool}`.

*Done-when:* no `.claude/` literal remains in `permission_fix.py`, and no rendered `Read(...)` value
is received — the ids are `plan-dir-edit`, `plan-dir-write`, `bundle-cache-read`. The written set is
pinned byte-identically against literals by
`test_permission_fix.py::test_written_default_set_is_the_pinned_three_rules` and by the
pre-existing `test_permission_fix_behavior.py:117`, which already encoded the same three rules and
would have failed had the relocation changed them.

Commit: *render Claude permission grammar and layout only in the runtime*.

**Declared limitation (see Findings F4, F25).** D1 does not route through the `Runtime` op surface:
`permission_common` imports `claude_runtime` directly, as it already did for settings load/save and
both path selectors, so the set ensured is Claude's whatever `runtime.target` says. And the settings
**mapping** — a Claude-shaped dict whose allow list holds rendered rules — still crosses into the
runtime as an argument, which principles §1 forbids. Both are the module's pre-existing binding
rather than something this deliverable introduced; both are now registered in the coupling
inventory §B and disclosed in the code.

### D2 — Settings-path reads delegate

**Done, and clean on every check.** `claude_runtime` gained `_claude_shared_settings_path` and
`_claude_project_settings_read_path`; `permission_common.get_project_settings_path` delegates to the
latter. No `.claude/settings` literal remains in `permission_common.py`, and the module docstring's
delegation claim is now true of the read path as well as the write path.

Behaviour was compared against `origin/main`'s inline body in all four cases (both files present,
local only, shared only, neither) and is identical in all four. Each of the four is pinned on both
sides: `test_permission_rendering.py::TestProjectSettingsReadPath` and
`test_permission_common.py::TestProjectSettingsReadPreference`, the second driven through the
module's own function so a reverted delegation is caught there rather than only in the runtime's
tests. Both classes additionally pin the read-versus-write-opposites invariant. (Verification round
2 found the local-only case missing from both — the report had claimed four where three were
pinned; it is pinned now.)

### D3 — Credential deny rules render in the runtime

**Done.** `_cred_ensure_denied.py` builds no rule text and receives none. It resolves the active
target's runtime through the router's own registration block
(`platform_runtime._make_runtime`) and calls
`permission fix --operation protect-path --permissions {credentials dir}`. The runtime renders the
deny grammar, writes it, and returns counts only (`paths_protected`, `rules_total`,
`changes_applied`); `test_no_rendered_rule_crosses_back_to_the_caller` asserts the raw TOON contains
neither `Read(` nor `Bash(`.

*Semantic identity:* the retired `_build_deny_rules()` was reconstructed from `origin/main` and
diffed against the live renderer — byte-identical, 19 rules, same order, same
`Bash(python3 -c *{distinctive segment}*)` vector.

*The `no-op` degrade* was exercised end to end, not just at the runtime method: `run_ensure_denied`
against a project whose `marshal.json` names `opencode` returns rc 0, prints `status: no-op` with
the reason and alternative, creates no settings file, and still re-asserts the credentials
directory's `0700` mode — the primary boundary holds on a target with no permission backend.

**Deliberate differences from the retired code, each stated rather than absorbed** — named rather
than counted, since the list grew once already:

- **De-duplication**, at two levels: within a path, and (since round 3) across the paths one call
  names. For a directory outside `$HOME` the tilde and absolute spellings are the same string, so
  the old builder drafted 19 rules of which 9 were duplicates and reported `rules_existing: 9` for
  rules that never existed.
- **What lands changes for one input class, and only one.** For a directory *under* `$HOME` the
  written set is byte-identical, and for an unrelated directory *outside* it the written set is the
  old one de-duplicated — same rules. For a **sibling of `$HOME`** the two differ: the retired
  `startswith` test treated `/home/user2/creds` as inside `/home/user` and emitted nine nonsensical
  `~2/creds` spellings, which the `relative_to` test does not. Nine rules that used to be written no
  longer are. They matched nothing, so this is a repair — but it is a change in what lands, and an
  earlier draft of this section claimed there was none. Found by verification round 3, which
  executed both builders against all three input classes rather than reading them.
- **`protect-path` writes only when a rule was actually added**, unlike its sibling `permission fix`
  branches. The retired caller behaved this way, and an idempotent re-run that re-serializes an
  operator's settings file is a visible change for no effect. Pinned by
  `test_a_no_change_rerun_does_not_rewrite_the_file` — which re-spells the settings compactly before
  the second call, because comparing the bytes of a file the runtime itself just wrote can never
  detect a rewrite. The asymmetry with the sibling branches is documented in `contract.md`.
- **An unregistered `runtime.target` is now an error rather than a silent Claude write.**
  `_cred_ensure_denied` resolves the runtime through `platform_runtime._make_runtime`, which returns
  `None` for a target outside the runtime registry; the command then reports `status: error` and
  writes nothing. The retired code never consulted `runtime.target` at all and wrote Claude rules
  regardless. Strictly safer, and the intended consequence of routing — but it is a fourth
  difference, and it diverges from `marketplace_paths._invoke_layout_op`, which *falls back to the
  default runtime* for an unregistered target. A layout lookup has no error channel and this command
  does, which is why the two differ; the divergence is recorded rather than harmonised, because
  harmonising it would change `_invoke_layout_op`, plan `010`'s file.
- **The subcommand's `total_deny_rules` output key is gone**, replaced by `protection_rules_total`.
  Different name and different denominator: the old key was the length of the whole `deny` list,
  the new one counts this protection's own rules. `grep` finds no consumer of the old key anywhere
  in the tree, and `rules_added` / `rules_existing` are numerically unchanged for a credentials
  directory under `$HOME`. Found by verification round 2, which counted three differences where this
  section had claimed two.

### D4 — Implementor scan routes through layout resolution

**Done.** `_scan_project_for_implementors` iterates `get_project_skill_roots()` via a new
`_project_skill_trees` helper that anchors each root with the shared
`marketplace_paths._resolve_skill_root`. No segment-wise `.claude` construction remains in the
function. Multiple roots are scanned in the op's priority order and the first root carrying a given
step id wins.

Every `test_project_scan_*` test in `test_extension_discovery.py` covers it, and none can pass
against the retired single-root code: discovery through a non-default two-root list,
highest-priority-root-wins on a colliding step id, a declared root absent from disk, an absolute
declared root, and a `~`-anchored one (which reaches a different resolver branch, since
`expanduser()` runs before the `is_absolute()` test).

**Disclosed, on the same terms as F30.** The rewritten docstring names `.claude/skills/` once, as an
`on Claude that is X` illustration of what the layout op resolves to — a **new** occurrence of the
literal, introduced by this diff in D4's own file. The plan's Verification bullet asked the sweep to
establish that no new literal was introduced by the fixes themselves, so it is stated rather than
left to the sweep's discretion: it is the same sanctioned explanatory shape
`marketplace_paths.get_project_skill_roots` and `_doctor_shared.py` use, and it is not a live
anchor. Verification round 3 found it unreported while its twin in `scan-marketplace-inventory.py`
was disclosed.

### D5 — Display and filter strings stop naming `.claude/`

**Partly a no-op, because half the deliverable was already closed.** See Findings F22 for the
divergence from the plan's OBSERVED claim.

- `scan-marketplace-inventory.py` — done. `runtime_mount` derives from
  `runtime_mount_prefix()`, which reads the highest-priority declared skill root; a relative root is
  shown `./`-anchored, a `~`-anchored or absolute one as-is. Four tests, including one that
  relocates the root and asserts the display string follows.
- `check-manifest-consistency.py` / `check-routing-decisions.py` — **`_BOOKKEEPING_PREFIXES` was
  already gone**, retired into `_footprint_classification.py` by earlier work. The only `.claude/`
  in either file was an explanatory comment naming the Claude target as an example; both were
  reworded to the layout-neutral phrasing `_footprint_classification.py` already uses. Behaviour
  unchanged, and the scripts' existing tests still pass.

*Done-when literal reading:* "no hardcoded `.claude/` remains in the three files" is not literally
satisfied — see F30.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** — 19 Python files: production
code in the `plan-marshall` and `pm-plugin-development` bundles across the `extension-api`,
`manage-providers`, `plan-retrospective`, `platform-runtime`, `tools-permission-doctor`,
`tools-permission-fix` and `tools-marketplace-inventory` skills, plus six test modules. The gate
therefore applies.

`./pw verify` was run from the repository root over the whole tree and read from the streamed tool
output rather than the exit code. **The figures below are re-derived at the current head**, not
carried forward: verification round 2 caught an earlier version of this section quoting a run that
predated the round-1 fix commit, which is how a gate figure goes quietly stale.

- quality-gate — `mypy … Success: no issues found in 416 source files`; `ruff … All checks passed!`;
  `SPDX-header check passed`; plugin-doctor `status: pass`, `total_issues: 0`.
- test-compile — no issues found over 935 source files (one `no-any-return` in a new test was found
  and fixed here; the narrower `quality-gate` + `module-tests` pair does **not** run this step, which
  is why the full `verify` was used).
- module-tests — **21381 passed, 14 skipped**.

`git status --porcelain` was empty before each commit; no `uv.lock` churn reached a commit, and paths
were staged explicitly rather than with `git add -A`.

**Stale-base re-verification (§ Step 8 condition 2), performed twice.** Shape used both times:
**rebased on the branch**, so the tested tree *is* the PR head and the PR's own CI verifies what
actually lands.

| # | Count before | What the base had taken | Replayed | Gate on the merged tree |
|---|---|---|---|---|
| 1 | 3 | three unrelated documentation commits | 12 commits, no conflict | clean; test-compile over **784** files |
| 2 | 1 | the module-budget campaign (#1314) — 281 test modules restructured | 13 commits, no conflict | clean; test-compile over **935** files |

`git rev-list --count HEAD..origin/main` reads **0** after the second.

**The second one is the one that could have failed, and is why the condition exists.** #1314 is a
pure move of the test corpus onto class boundaries — no file it touches is a file this branch
touches, so `mergeable_state` would have read `clean` either way, and this branch's own CI was green
against a base that no longer existed. What a textual check cannot see is a registration collision:
`conftest.load_script_module` registers under the script stem, and #1314's own record notes that
collapsing distinct registrations onto a shared one cost an earlier plan 173 order-dependent
failures. This branch's tests use that helper.

So the merged tree was checked for exactly that, beyond the whole-suite run: the six affected test
modules were run **serially in declaration order** and again **serially in reverse module order** —
1937 passed both ways. The whole-suite figure is unchanged at **21381 passed / 14 skipped**, which is
what a pure move predicts: the restructuring redistributed tests across many more files (784 → 935
type-checked sources) without gaining or losing one.

If `main` advances again before the merge gate, this is re-done rather than assumed — the count is
re-read at the gate, and a non-zero count means another rebase and another full gate run.

### Mutation sweep — the new guards were shown to fail

`./pw verify` passing says the guards agree with the code, not that they would notice a defect.
Mutations were applied one at a time, each restored from a harness-held byte snapshot in a `finally`
(never a git command, which would have rewritten the file from the index and discarded uncommitted
work). The tree was committed and `git status --porcelain` empty before each sweep, and empty again
after it.

**The sweep was run three times, and the table below is the last run.** Saying which run a table
comes from matters here, because the intermediate runs are where the information was:

1. Eleven mutations against the deliverables, at the commit that introduced them. All killed —
   but verification round 2 pointed out that a sweep run at that commit cannot have covered the
   guards the *later* fix commits added, and demonstrated that one of them would have survived.
2. Extended to fifteen and re-run at the current head. One **anchor miss** and one **survivor**
   (below).
3. Re-run after fixing the anchor and the vacuous guard. All fifteen killed.

| Mutation | Verdict |
|---|---|
| D1 cache permission points at the wrong subtree | killed |
| D1 defaults are merged but never written | killed |
| D1 apply-fixes drops the normalize-only save | killed |
| D2 read preference flipped to the write preference | killed |
| D3 the absolute-form Read deny rule is dropped | killed |
| D3 one exfiltration vector loses its tilde spelling | killed |
| D3 protect-path writes nothing | killed |
| D3 OpenCode rejects protect-path instead of declining | killed |
| D4 the implementor scan reverts to one hardcoded root | killed |
| D4 a later root overwrites the highest-priority root | killed |
| D5 runtime_mount reverts to the hardcoded Claude layout | killed |
| R1 protect-path reverts to writing unconditionally | killed |
| R1 the shared skill-root resolver is bypassed for a naive join | killed |
| R2 the settings read path stops preferring the local file | killed |
| R2 `protection_rules_total` reports the settings file total instead | killed |

No mutation survives at run 3. Run 2 is where the two findings came from:

- `protect-path writes nothing` returned an **anchor miss**, because the round-1 fix had changed the
  line the mutation targeted. An anchor that no longer matches is a failed mutation, not a passed
  one — the harness reports it as such rather than counting it killed, and the row above is from run
  3, after the anchor was corrected.
- `protection_rules_total reports the settings file total instead` **survived**. Both fixtures
  started from an empty deny list, so the protection's rule count and the settings file's total deny
  count were the same number and the confusion was invisible by construction — the fixture shared
  the implementation's scale. Both now seed an unrelated deny entry first, which is what makes the
  two denominators differ.

**The boundary guards round 3 added are not in this table.** `protect-path` at a home-directory
argument, at a repeated path, and a dry run against a partly-populated deny list are new inputs
rather than mutations of existing code; each was verified by executing the operation and reading the
result, which is what the table's rows do less directly.

## Findings

### Surface expansion beyond the plan's Expected surface

The epic README requires a run to **report** rather than silently absorb any file its work turns out
to need beyond the plan's list. The test that separates them is whether the edit was **forced by this
change** (keep, and report) or was an **adjacent fix to a pre-existing defect** (revert, and record)
— the epic's constraint bars adjacent fixes in another plan's surface, not the consequences of one's
own change.

Plans `010` and `030` are declared non-concurrent, so none of these is a live conflict.

The table is the complete set: it was re-derived from `git diff --name-only origin/main...HEAD`
against the plan's Expected surface at the moment of this claim, after verification round 2 found
three bundle files edited but unaccounted, and a lead-in count that disagreed with its own table.

| File | Owner per README | Why | Disposition |
|---|---|---|---|
| `platform-runtime/scripts/runtime_base.py` | `010` | `permission_fix`'s docstring enumerates the operation values; leaving it would state a false enumeration | kept, forced |
| `platform-runtime/scripts/platform_runtime.py` | `010` | argparse `choices` gate the CLI; without it the operation is reachable in-process only | kept, forced |
| `platform-runtime/scripts/opencode_runtime.py` | `010` | its `valid_ops` set decides `no-op` versus `invalid_operation` — D3's "degrades to `no-op` without error" fails without it | kept, forced |
| `platform-runtime/SKILL.md` | `070` | its op table enumerates the same operation values | kept, forced |
| `tools-permission-fix/SKILL.md` | `070` | its intent table enumerates them too | kept, forced |
| `manage-providers/scripts/credentials.py` | not listed | this change made its `ensure-denied` help text and module docstring inaccurate | kept, forced |
| `manage-providers/SKILL.md` | `070` | its verb table and a section heading promised deny rules on every target, which the routed call no longer implies | kept, forced |
| `manage-providers/standards/security-considerations.md` | `070` | same claim, and it additionally held a prose copy of the exfiltration-vector list D3 moved into the runtime — a second home for a list this plan exists to single-source | kept, forced |
| `marshall-steward/references/provider-setup.md` | `070` | same claim, at the wizard step that invokes the command | kept, forced |
| `tools-permission-doctor/standards/permission-architecture.md` | `070`, **and named in this plan's own Out of scope** | its "Resolution Priority" section states the read preference backwards — a defect that pre-dates this change | **kept, on an operator decision.** Reverted first, on the epic's rule; re-landed after round 3 raised the collision between that rule and the lane's "nothing false is left, wherever it lives" and the operator chose to fix it. The only row here whose disposition is an operator's rather than the run's |

**Two of these rows are truth fixes in another plan's surface, not consequences of this change** —
`permission-architecture.md` and the `tools-permission-doctor` description row in
`manage-providers/SKILL.md`. Both were held back under the epic's constraint and then landed on the
operator's explicit decision, recorded here because a scope rule overridden silently is worse than
one not applied at all.

Two epic documents outside `030`'s own plan directory were also edited, and are not surface
expansions but duties the epic assigns to the closing plan: `reference/coupling-inventory.md` (the
README requires the plan that removes a coupling to retire its rows in that same plan) and
`README.md` itself, whose baseline row asserted that the implementor scan does not route through the
layout helpers — false once D4 landed.

### The claim table's HYPOTHESIS is refuted; the schema addition, stated

> *"The existing permission-op TOON contract can carry D1/D3 without a schema change" — HYPOTHESIS.*

**Refuted for D3.** No existing operation writes the `deny` list; `permission_configure` and every
`permission_fix` branch mutate `allow`. The plan's own fallback applies — "a needed schema addition
is recorded in the report and made minimally, not silently" — so this is the record:

- **Added:** the operation **value** `protect-path` to the existing `permission fix` op. No new
  `Runtime` operation, no changed signature, no changed contract shape. The op count stays 24.
- **`--permissions` is documented as carrying the operation's semantic arguments** rather than one
  fixed kind of value: permission patterns for `add`/`remove`/`ensure`, **directory paths** for
  `protect-path`, nothing for `normalize`/`consolidate`. A path is normalized data, so principles §1
  is satisfied: the grammar is rendered inside the target.
- **Response fields added for that operation:** `paths_protected`, `rules_total`, and (dry-run)
  `proposed_count`. Counts, never rendered rules.
- `contract.md` carries the new enum, the `--permissions` clarification, and a worked TOON example
  generated from the real serializer (the doc's TOON blocks are round-trip-validated by test).

**Held for D1**, which needed no contract change at all: it does not go through the op surface.

### The plan's OBSERVED claim about `_BOOKKEEPING_PREFIXES` is stale

The claim table records `_BOOKKEEPING_PREFIXES` as OBSERVED in `check-manifest-consistency.py` and
`check-routing-decisions.py`. Re-derived at the moment of the claim, as the epic README requires:
**at `origin/main` the tuple is in neither file.** It was retired into
`_footprint_classification.py`, which quotes it only as a historical example of the defect it
replaced. What remained in the two check scripts was one explanatory comment each, naming the Claude
target as an example of a tree a build extension may route as `production`.

Reported, not silently adopted: half of D5 was already done, and this run's contribution there is a
wording change, not a coupling removal.

### The residual sweep beyond the plan's five clusters

The claim table required "anything beyond the five clusters above … is reported, not silently
adopted or skipped". The sweep over `marketplace/bundles/**` (both quote styles, segment-wise
included), discarding `platform-runtime` internals and the sanctioned multi-root resolvers, found
these. None was adopted.

**Registered open in the coupling inventory §B**, which is the epic's mechanism for not losing a
scoping exclusion:

- `extension-api/scripts/configurable_contract.py` — the same segment-wise `.claude/skills`
  construction D4 closed, one file over in the same skill. The two were never registered together,
  so this half survived.
- `tools-marketplace-inventory/scripts/_dep_index.py` — resolves its `project` scope from its own
  `CLAUDE_DIR` constant while the `plugin-cache` scope beside it routes through the layout op.
- `permission_fix.py`'s remaining permission-DSL knowledge — the executor and broad-python
  constants, the `Skill(…)`/`SlashCommand(…)` wildcard generators, and the timestamp-consolidation
  patterns. Registered by verification round 4, which found a code comment in that file already
  asserting the registration before it existed.

**Recorded against an existing row rather than a new one:** `permission_common.py` and
`permission_fix.py` are bound to `claude_runtime` by direct import rather than through the registry
(F25), and the settings mapping crosses the boundary as an argument (F4).

**Found, then withdrawn:** `marshall-steward/scripts/bootstrap_plugin.py`. The sweep registered its
per-target root detection as open work; the inventory's own "Confirmed clean" section already
sanctions exactly those symbols as Claude-specific-by-design, and the plan's claim table had told
the sweep to discard sanctioned resolvers. Registering it was the sweep's error, and round 3 caught
the document asserting both sides of one question. Named here rather than deleted, because a site
the sweep examined and *correctly* dismissed is different evidence from one it never looked at.

### Verification round 1 — dispositions

Round 1 dispatched an independent sub-agent against `plan.md`, the principles, the epic README and
the full diff. It returned thirty findings. Every one is dispositioned below; a finding is recorded
per instance, so one defect appearing three times is three rows.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | round 1 | `_claude_bundle_cache_root` docstring claimed the default-permission renderer reads it; the renderer reads the *parent*, `_claude_plugin_cache_dir` | **fixed** — both docstrings now name the parent and the segment-sharing that actually prevents drift |
| F2 | round 1 | `layout_bundle_cache_root` docstring — same false claim, second instance | **fixed** |
| F3 | round 1 | `permission_fix.py` comment claimed the script "never learns one target's permission-string format"; it still holds `EXECUTOR_PERMISSION`, `OVERLY_BROAD_PYTHON`, `Skill(...)`/`SlashCommand(...)` generation and DSL-parsing patterns | **fixed** — the claim is narrowed to the defaults, and the rest is named as registered open work |
| F4 | round 1 | `claude_runtime` section comment claimed the grammar "never crosses the boundary in either direction"; the settings **mapping** crosses as an argument, and §1 names the settings-file shape | **fixed** — the comment now states exactly what does not cross and names the mapping as real residue, not a technicality |
| F5 | round 1 | `permission_common.ensure_default_permissions` docstring said "the target's" default set; the module is bound to `claude_runtime` directly, so it is always Claude's | **fixed** — docstring and module docstring both state the binding |
| F6 | round 1 | `manage-providers/SKILL.md` verb table: "Add deny rules to the host platform's settings" — on a declining target it writes nothing | **fixed** |
| F7 | round 1 | same file, `### Add Deny Rules` heading — second instance | **fixed** — retitled to the goal, with the `no-op` behaviour stated |
| F8 | round 1 | `credentials.py` module docstring still said "deny rule management" while the `help=` one function below had been corrected | **fixed** |
| F9 | round 1 | `permission-architecture.md` sentence left mid-clause by this run's edit | **moot** — the whole edit was reverted (see F18) |
| F10 | round 1 | `test_the_two_runtimes_accept_the_same_operation_set` named a two-runtime comparison but drove only OpenCode; a Claude-side divergence left it green | **fixed** — both runtimes are now driven per operation |
| F11 | round 1 | a test docstring attributed the tilde/absolute collapse to the prefix-test counterfactual, where it is a property of the `relative_to` implementation | **fixed** |
| F12 | round 1 | the `claude_project` fixture docstring implied a test at `origin/main` wrote into the developer's settings; the prior tests mocked the save | **fixed** — it now says accurately that the *predecessors* were isolated by mocking `permission_common.save_settings`, which the routed call bypasses |
| F13 | round 1 | `_claude_shared_settings_path` docstring over-claimed "spelled once each"; the global path composes its own segments | **fixed** — narrowed to the project selectors, with the global path's different anchor noted |
| F14 | round 1 | `runtime_base.py` edited against the plan's Out of scope | **reported** — surface table above; forced, and plan `010` is non-concurrent |
| F15 | round 1 | `platform_runtime.py` edited against the same clause | **reported** — as above |
| F16 | round 1 | `opencode_runtime.py` edited, `010`'s surface | **reported** — as above; D3's `no-op` requirement fails without it |
| F17 | round 1 | `platform-runtime/SKILL.md` edited, `070`'s surface | **reported** — as above |
| F18 | round 1 | `permission-architecture.md` edited — named in this plan's own Out of scope, and fixing a *pre-existing* defect no deliverable needs | **reverted, then re-landed on an operator decision.** The revert was correct on the epic's rule. Round 3 then framed the residue as a *policy collision* rather than a review gap — condition A says "nothing false, wherever it lives", the epic says record instead — and put it to the operator, who chose to fix it. The re-landed edit drops the self-undermining rationale round 1 objected to (it justified the preference by an audit-completeness argument the selector's own single-file return contradicts) and states the two preferences as what the runtime selectors return, attributed to them, with no claim about how Claude Code itself layers the files |
| F19 | round 1 | `tools-permission-fix/SKILL.md` edited | **reported** — forced: its intent table enumerates the operation values |
| F20 | round 1 | `credentials.py` edited and not named in the brief's own list of knowingly-touched files | **reported** — now in the surface table; the same commit's F8 closes the inconsistency it left |
| F21 | round 1 | the claim table's required record of the schema addition was absent — the report was `_pending_` | **fixed** — recorded above |
| F22 | round 1 | the stale `_BOOKKEEPING_PREFIXES` premise and the divergence were unreported | **fixed** — recorded above |
| F23 | round 1 | the sixth residual cluster was registered in the inventory but not reported | **fixed** — recorded above, in § "The residual sweep beyond the plan's five clusters", alongside every other site the sweep found and what became of each |
| F24 | round 1 | `protect-path` saved unconditionally, where the retired caller saved only on a change | **fixed** — the write is now conditional, pinned by a byte-equality test on an idempotent re-run |
| F25 | round 1 | D1 does not route through the `Runtime` op surface, so principles §6's cost bar is unmet for it while D3 meets it; the asymmetry was undeclared | **declared, not fixed.** Bound: behaviour is identical to `origin/main` — verified in round 2, which read `origin/main`'s `permission_common` and confirmed it already imported the settings-path and load/save helpers from `claude_runtime` the same way, and that the rendered default set is byte-identical under every `$HOME` shape including the `resolve_home()` fallback. The runtime registry `platform_runtime._REGISTRY` holds `claude` and `opencode`; the *build* registry holds three targets, and `pr-agent` has no `Runtime` at all. Closing it needs either a new `Runtime` operation — which this plan's Out of scope forbids — or the `permission_common` restructure the inventory now registers. Stated in the D1 section, in the code, and in the inventory |
| F26 | round 1 | `_project_skill_trees` re-implemented `marketplace_paths._resolve_skill_root` inline | **fixed** — it calls the shared helper |
| F27 | round 1 | `test_no_rendered_rule_crosses_back_to_the_caller` never asserted success, so an error TOON would satisfy it | **fixed** |
| F28 | round 1 | an ensure-denied assertion held only because the sandbox directory name contains the word "credentials" | **fixed** — it now asserts specific rules built from the module's own bound `CREDENTIALS_DIR` |
| F29 | round 1 | the rewritten tests dropped the `importlib.reload`, so `_cred_ensure_denied` keeps whichever sandbox the first importing test installed | **rejected, with reason.** The binding is always to *a* sandbox, never the real tree, so no pollution is possible; the F28 fix reads the module's own bound constant, so the assertion is true of whichever sandbox is in force. Re-adding a module reload to make the identity match would reintroduce the cross-test reload the old fixture had to undo in teardown |
| F30 | round 1 | D5's Done-when ("no hardcoded `.claude/` remains in the three files") is not literally satisfied: two docstrings in `scan-marketplace-inventory.py` spell `.claude/skills`, one of them added by this diff | **rejected, with reason, and reported.** Both are `on Claude this is X` illustrations, the sanctioned phrasing already used by `marketplace_paths.get_project_skill_roots` and `_doctor_shared.py`; neither is a live anchor. The Done-when's wording is wider than the coupling it targets, and the divergence is stated here rather than met by deleting accurate explanatory prose |

**Positive collateral, recorded because it is a behaviour change nobody asked for.** The retired
`run_ensure_denied` loaded settings through `load_settings_path`, which returns a defaulted skeleton
*with* an `error` key on malformed JSON, and then wrote that skeleton back — silently destroying a
malformed settings file. The routed path fails closed with `invalid_settings` and writes nothing.

### Verification round 2 — dispositions

Round 2's primary surface was the text round 1 wrote, which is the round's whole point: by then the
youngest and least-reviewed prose in the branch is the prose written to explain the previous round's
fixes. It returned fifteen findings.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R2-01 | round 2 | `test_a_no_change_rerun_does_not_rewrite_the_file` — the guard round 1 added for F24 — **passes against the defect it names.** The runtime writes `json.dumps(..., indent=2)`, so the bytes of a file the runtime itself just wrote are identical on a rewrite; round 2 demonstrated it by reverting the guard and running the test's own fixture | **fixed.** The test now re-spells the settings compactly before the second call, so any write is visible; the mutation sweep confirms it now fails against that revert. The test's docstring and the two report claims that cited it as a byte-equality pin are corrected |
| R2-02 | round 2 | `marshall-steward/references/provider-setup.md` § "Step 13k: Add deny rules" — the claim round 1 corrected in `manage-providers/SKILL.md`, surviving one directory over | **fixed** — retitled to the goal, with the `no-op` degrade stated |
| R2-03 | round 2 | `manage-providers/standards/security-considerations.md` — same claim, and a prose copy of the exfiltration-vector list D3 moved into the runtime | **fixed** — the standard now names the goal and no vectors; the list has one home |
| R2-04 | round 2 | the coupling-inventory row added by round 1 asserted "the OpenCode path never reaches these scripts"; neither skill declares a `targets:` filter and an unscoped component is emitted to every target, so it does reach them | **fixed** — the row now states the reachability correctly and names remedy candidates |
| R2-05 | round 2 | the Build gate section said "six bundles"; it is two bundles across seven skills | **fixed** — re-derived from the diff |
| R2-06 | round 2 | the surface table said "Six files qualify" above seven rows, and omitted three bundle files edited by the round-1 and round-2 fix commits | **fixed** — the count lead-in is gone, the three files are rows, and the two epic documents are accounted separately |
| R2-07 | round 2 | D2 claimed four pinned read cases; the local-only case was pinned by neither class | **fixed** — added on both sides |
| R2-08 | round 2 | the build-gate and mutation-sweep figures described a tree one commit older than the head under review, without saying so | **fixed** — both re-run at the current head, and both sections now say the figures are re-derived rather than carried forward |
| R2-09 | round 2 | "Two deliberate differences from the retired code" is three — the dropped `total_deny_rules` output key was undisclosed | **fixed** — three, named rather than counted |
| R2-10 | round 2 | `protection_rules_total` was an added return key with no guard | **fixed** — and the first guard written for it was **vacuous**, which the re-run sweep caught: both fixtures started from an empty deny list, so the protection's count and the file's total deny count were the same number. Both now seed an unrelated entry |
| R2-11 | round 2 | `layout_bundle_cache_root`'s docstring claimed the cache layout is "spelled once"; the steward's bootstrap detector and the executor generator each compose it | **fixed** |
| R2-12 | round 2 | `test_project_scan_resolves_an_absolute_declared_root` claimed to cover the `~`-anchored case, which it did not exercise | **fixed** — the `~` case has its own test, since it reaches a different resolver branch (`expanduser()` runs before `is_absolute()`) |
| R2-13 | round 2 | "only `claude` and `opencode` are registered" did not name which registry, and contradicts principles §6's "the registry already holds three" | **fixed** — the runtime registry is named, and the build registry's third target is noted as having no `Runtime` |
| R2-14 | round 2 | `manage-providers/SKILL.md` describes `tools-permission-doctor` as a "Deny rule manipulation reference"; the doctor is read-only | **reported, then fixed on the same operator decision as F18.** The row now describes the doctor as a read-only audit. Round 3's observation that the F18 precedent fitted this case imperfectly — F18 reverted an edit to a file this change otherwise does not touch, whereas this sentence sits in a file the change edits twice — is what made it worth escalating rather than settling |
| R2-15 | round 2 | `contract.md` documented `protect-path` but not the conditional-write asymmetry it introduced | **fixed** — the contract states the asymmetry and why |

### Verification round 3 — dispositions

Round 3 returned ten findings. **None changed a deliverable's behaviour and none changed a test's
verdict** — but two of them found real defects in the shipped code that only a boundary probe could
reach, and one found a disposition row of mine that was simply false.

Its closing advice is adopted and recorded here because it is the round's most useful output: close
a disposition by **re-derivation**, not by assertion — re-grep the corrected phrase across the whole
file and the whole tree before writing "fixed". That is the inventory's own
[§ Closing a row](../reference/coupling-inventory.md#closing-a-row) rule applied to the run report,
and it would have caught three of this round's findings for free. Every row below was closed that
way.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R3-01 | round 3 | the coupling inventory asserted **both sides** of the same question: round 1 registered `bootstrap_plugin.py`'s per-target root detection as open §B work, while the document's own "Confirmed clean" section — unchanged from `origin/main` — sanctions exactly those symbols as Claude-specific-by-design | **fixed** — the §B row is withdrawn. The sanction is the older and better-considered statement, and the plan's claim table had instructed the sweep to discard sanctioned resolvers; registering one as a new find was the sweep's error, not the document's |
| R3-02 | round 3 | **my R2-03 disposition was false.** Round 2 changed one line of `security-considerations.md`; forty lines below, § "Deny Rule Coverage" still carried all 19 rules verbatim in the Claude DSL, under a lead-in claiming they are single-sourced from `CREDENTIALS_DIR` | **fixed** — the pattern block is gone and the section states the coverage as intent, pointing at the runtime for the set. Re-derived: `grep -n "Read(\|Bash(\|single-sourced"` over the file returns nothing |
| R3-03 | round 3 | the mutation-sweep narrative said the sweep ran twice while its own bullet described an anchor miss that a later run must have fixed | **fixed** — three runs, each named, and the table is attributed to the last |
| R3-04 | round 3 | "Four tests cover it" in D4 is five; the commit that re-derived the report's other figures missed this one | **fixed** — the tests are named by their shared prefix rather than counted, which cannot go stale the next time one is added |
| R3-05 | round 3 | this diff added a **new** `.claude/skills` illustrative literal in D4's own file, while D4's section claimed "clean on every check" and the identical case in D5's file was disclosed | **fixed** — disclosed in D4 on the same terms as F30 |
| R3-06 | round 3 | the R2-11 fix replaced one false claim with another: it said the executor generator's cache-segment composition is "registered open", where the inventory sanctions that embedded resolver as **clean** | **fixed** — the docstring now says sanctioned, which is what the inventory says |
| R3-07 | round 3 | "Nothing that lands in a settings file changes" is false for a **sibling of `$HOME`**: the retired `startswith` test emitted nine `~2/creds` spellings the `relative_to` test does not | **fixed** — the D3 section now states the three input classes and what differs in each. Round 3 established this by executing both builders, not by reading them |
| R3-08 | round 3 | a fourth behavioural difference was undisclosed: an unregistered `runtime.target` now errors instead of silently writing Claude rules, and the policy diverges from `_invoke_layout_op`'s fallback | **fixed** — disclosed, with why the two differ and why harmonising them is out of scope |
| R3-09 | round 3 | `proposed_count` was the R2-10 coincidence one field over — the only dry-run test started from an empty deny list, so `proposed_count` and `rules_total` were the same number and a confusion between them was invisible | **fixed** — a dry run against a partly-populated deny list separates them |
| R3-10 | round 3 | two boundary inputs reachable from the CLI that `tools-permission-fix/SKILL.md` now advertises: protecting **the home directory itself** rendered `Bash(python3 -c *.*)` — a deny rule matching very nearly every inline script — and naming **one directory twice** reported `rules_total: 38` while writing 19, re-creating one level up the over-count the per-path de-duplication exists to remove | **fixed, both.** `_tilde_form` renders home as bare `~`, so the distinctive segment falls back to the absolute path instead of `.`; `protect-path` de-duplicates across the paths one call names. Guarded by four new tests, including one that a collapse of two genuinely distinct paths would fail. The path-containing-`)` case round 3 also noted is a pre-existing escaping class it did not raise, and this run does not either |

### Verification round 4 — dispositions

Round 4 was commissioned to test round 3's diagnosis: that the recurring failure lives in the **fix
step**, so each round finds exactly one instance of "the previous round's fix didn't fully land".

**It recurred, for the third round running** — and one layer deeper than before. Nine of round 3's
ten closures held under independent re-derivation; the tenth landed in the artifact and not in the
sentence *about* the artifact. Worse, the same shape was then found in a claim written by **round
1** that rounds 2 and 3 had both walked past.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R4-01 | round 4 | R3-01 withdrew the `bootstrap_plugin.py` row from the inventory, but the report section asserting that registration was not updated: it still read "three live sites … all three are registered in the coupling inventory §B", and F23's row inherited the over-count | **fixed** — the section is restructured by *what became of each site* rather than by a count, and names the withdrawn one explicitly. A site the sweep examined and correctly dismissed is different evidence from one it never looked at, so it is named rather than deleted |
| R4-02 | round 4 | a **shipped code comment** in `permission_fix.py` — written by round 1's F3 fix — claimed its residual DSL knowledge was "registered open in the multiplattform epic's coupling inventory". No row named it: the one row mentioning that file registers a different coupling entirely | **fixed by registering it.** The claim named real open work, so the honest close is the row, not a retraction: §B now carries a row naming `EXECUTOR_PERMISSION`, `OVERLY_BROAD_PYTHON`, the `Skill(…)`/`SlashCommand(…)` generators and the timestamp patterns, as the same grammar-in-a-general-script class `workflow-permission-web` already holds. The comment now points at that row |
| R4-03 | round 4 | `contract.md` documented `protect-path`'s response as `paths_protected` and `rules_total`, omitting `proposed_count` — and its only dry-run example shows `proposed_additions`, which this operation never returns. The plan required the schema addition be made "not silently" | **fixed** — the op-schema document names `proposed_count`, and says why this operation substitutes a count for the additions list |
| R4-04 | round 4 | the `tools-permission-doctor` row this run rewrote asserts the skill "never writes itself"; its `scripts/permission_common.py` exposes `save_settings` and now `ensure_default_permissions` | **fixed twice.** The first attempt replaced the false absolute with "its `detect-*` subcommands inspect what the protection wrote" — also false, and the closure pass caught it: `permission_doctor.py` contains no occurrence of `deny` at all, and all three `detect-*` subcommands read only `permissions.allow`. The row now says what the doctor does audit, and states plainly that it does **not** read the deny rules `ensure-denied` writes — which is the fact a reader of this skill actually needs |
| R4-05 | round 4 | the newly-corrected § "Resolution Priority" framed its bullets as "the preferences the `tools-permission-*` selectors apply", under which the pre-existing "Global settings always apply as baseline" bullet is false — no selector applies a global baseline | **fixed** — global scope is described as a separate scope addressed by `--scope global`, outside either project preference |

**Round 4's closure checklist, re-derived rather than asserted.** Its recommendation was that a
fifth *general* round would not terminate — each round's primary surface is the prose the previous
round wrote — and that what closes the loop is a targeted pass over an enumerable population. That
checklist was run:

1. The residual-sweep section carries no count and no registration claim for `bootstrap_plugin.py`;
   F23's row matches. Re-derived by grep for the retired phrasings: no hits.
2. Every "registered open" / "sanctioned" claim this diff adds under `marketplace/` — five of them —
   was checked against the **Coupling column of the row it points at**, not merely the row's
   existence. All five now hold: the layout docstring's two sanctioned sites are both named in the
   Confirmed-clean paragraph; the `permission_common` module docstring and
   `ensure_default_permissions` both point at the direct-import row, which covers that binding; the
   `claude_runtime` section comment points at the same row's settings-mapping half; and
   `permission_fix.py`'s comment points at the row R4-02 added, which names each symbol it cites.
3. `proposed_count` appears in `contract.md`'s `protect-path` documentation.

**What round 4 confirmed clean**, listed because an empty finding set is otherwise indistinguishable
from a check that examined nothing: the home-directory guard is strongly non-vacuous — reverting
`_tilde_form` fails all four of its assertions, positives included, so it is not carried by its
negatives; the three deny-rule input classes were re-verified **by executing both the retired and
the current builder** (byte-identical under `$HOME`; de-duplicated outside it; exactly nine `~2/`
rules dropped for a sibling of `$HOME`); the `no-op` degrade end to end for `opencode`, the error
path for an unregistered target, and the Claude default for an absent `marshal.json`; 21395 collected
== 21381 + 14; the surface table's ten rows complete; and the disposition tables contiguous across
F1–F30, R2-01–R2-15, R3-01–R3-10.

**Bounded observations round 4 raised and did not treat as findings**, recorded so they are not
lost: `protect-path` does not normalize its path argument, so `"$HOME/"` yields a double-slash rule,
`"./creds"` yields rules that describe more ground than they cover, and `"/"` yields
`Bash(python3 -c */*)`. The retired builder used the raw string identically, and the credentials
caller passes one absolute path, so this is a pre-existing shape reachable only by CLI misuse.
`_tilde_form` is path-lexical, so a symlink into the home directory renders absolute.

### When the loop stopped, and on whose answer

**Budget.** The lane's default is five rounds. Four general rounds ran; at the fourth, the verifier
argued that a fifth *general* round would not terminate — each round's primary surface is the prose
the previous round wrote, so it keeps yielding roughly one new instance indefinitely — and
recommended a **targeted closure pass over an enumerable population** instead. The operator, who was
reachable throughout, had already granted up to five further rounds. The grant was therefore spent
on **one** pass, scoped as round 4 advised rather than as a fifth of the same thing. That is
recorded because it is a discretionary use of an extension: the remaining rounds were declined on a
verifier's reasoning, not exhausted.

**The exit is `verifier-clear`, and the answer is the closure verifier's, not this run's.** Asked
directly whether any defect remained that a reader should know about and the report did not
disclose, it answered **yes** — two prose statements — and said explicitly that once those landed
and were re-checked mechanically it saw *"no basis for another round: every other assertion in the
round-4 commit and in round 4's checklist was re-derived and holds."* Both were fixed, and both were
re-derived after fixing: the inventory row's cross-reference no longer states a direction, and
`permission_doctor.py`'s zero occurrences of `deny` is the evidence the corrected SKILL.md row now
states rather than contradicts.

**The evidence the answer rests on is stronger than another read.** Across the five passes: both the
retired and the current deny-rule builders were **executed** against all three input classes and
diffed; the `no-op` degrade, the unregistered-target error path and the absent-`marshal.json`
default were **run** end to end; every settings-path case was **run** against `origin/main`'s
retired body; and an 18-mutation sweep was run four times, the last with no survivor. The
home-directory guard was mutation-tested specifically and fails all four of its assertions against
the reverted implementation.

**Were the late rounds narrower, or merely fewer?** Narrower, measurably. Round 1's thirty were
spread across the shipped change; round 3 returned ten of which **none** changed a test's verdict;
the closure pass returned two, both single-clause prose, neither behavioural. But narrower is not
the same as exhausted — see the residue.

**Survivors left open, each characterised.**

| Survivor | Kind | Bound |
|---|---|---|
| **F25** — D1 does not route through the `Runtime` op surface; `permission_common` imports `claude_runtime` directly, so the default set is Claude's whatever `runtime.target` says | (b) bounded | Behaviour is identical to `origin/main`, verified by reading its `permission_common`, which imported the same helpers the same way. The runtime registry holds `claude` and `opencode`; the build registry's third target has no `Runtime` at all. Closing it needs a new `Runtime` operation — which this plan's Out of scope forbids — or the `permission_common` restructure now registered in the inventory. Re-put to the verifier in the stopping pass and re-confirmed |
| **F4-residue** — the Claude-shaped settings mapping crosses into `ensure_default_permissions` as an argument, which principles §1 forbids | (b) bounded | Pre-existing and verified so: `origin/main`'s `save_settings` already passed the same mapping into `claude_runtime._save_settings`. This adds one more site of an existing crossing, not a new kind. Closing it means restructuring every `permission_fix` subcommand. Re-put to the verifier in the stopping pass and re-confirmed |
| **`protect-path` does not normalize its path argument** — `"$HOME/"` yields a double-slash rule, `"./creds"` an unanchored one, `"/"` yields `Bash(python3 -c */*)` | (b) bounded | All three **run**, not reasoned about. The retired builder used the raw string identically, so this is a pre-existing shape; the only shipped caller passes one absolute path, so it is reachable solely by CLI misuse. `_tilde_form` is path-lexical, so a symlink into home renders absolute |

**What residue to assume remains.** The deliverables should be read as still carrying defects of the
kind the last passes found: **false or imprecise sentences**, in prose written to explain a fix.
That class did not decay across five passes — every round found at least one, including the closure
pass, and twice the defect was inside a sentence a previous round had just rewritten. It is not
claimed to be exhausted. What *is* claimed, and was tested by execution rather than reading, is that
no behavioural defect is open: the last change to executing code was round 3's, and the two passes
since found none.

### Post-loop: a meta-project leak the verification passes never looked for

Raised by the operator after the loop closed, and worth recording because five verification passes
missed it — none of them was asked whether shipped bundle source may reference the meta-project's
own planning documents.

**The question asked** was whether this run violated the documentation standard *"Current state only
— do not describe transitional information"* by writing history into prose. Swept: **it did not.**
No added line under `marketplace/**` carries `used to`, `no longer`, `previously`, `formerly`,
`retired`, `deprecated`, `legacy`, `this plan`, or `since plan`. The history in this run lives in
`doc/plans/**` — this report and the coupling inventory — where `CLAUDE.md` places it: a run report
is a dated **record**, and the standard governs documentation rather than records.

**What the sweep did find** is a different defect, and a real one: **five references from shipped
bundle source into `doc/plans/multiplattform/reference/coupling-inventory.md`** —
in `claude_runtime.py`, `_claude_runtime_impl.py`, `permission_common.py` (twice) and
`permission_fix.py`. Bundles ship to consumer projects, and no consumer project has that file. Each
was a pointer added to make a claim checkable; the effect was to make four scripts depend on a
document only this repository holds — the meta-project-leak class this repo keeps a dedicated audit
recipe for, and one no plugin-doctor rule catches.

All five are gone. What each pointer was carrying is kept where it was load-bearing and made
self-contained instead: the layout docstring now says *why* the other two cache-segment spellings are
deliberate (one runs before the plugin is resolvable, the other is generated to run standalone)
rather than citing a document that sanctions them. Re-derived: `coupling inventory`, `multiplattform`
and `doc/plans` return nothing across every `marketplace/**` file this run touched. The couplings
themselves stay registered in the inventory, which is where a registry belongs.

## Reviewer participation

_Recorded at the merge gate, from the comment bodies on all three surfaces._

**Expected population, derived from configuration** — the `author_login` of each registry doc under
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/`, read at the moment of this
claim rather than transcribed from anywhere: `coderabbitai` (`coderabbit.md`, `honors_skip_label:
true`), `cuioss-review-bot` (`pr-agent.md`, `honors_skip_label: true`), `sourcery-ai`
(`sourcery.md`, `honors_skip_label: false`). M = 3.

**Label decision (§ Step 7's table), taken at creation and disclosed to the operator first.** The
changed-path set carries R1 (`*.py`), R2 (`marketplace/**`) and R3 (`doc/plans/**`) paths, so **row
1** fires: **no `skip-bot-review` label**, arm `reviewable`. Every reviewer is invited.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| … | … | … | … |

## Cost

- **Tokens:** not available to the agent in this session — no harness surface exposes a running
  total, and a figure derived by any other means would be a guess.
- **Wall-clock:** _recorded at the merge gate._
- **Population:** whatever is recorded here counts **this single interactive Claude Code cloud
  session**, orchestrator and every dispatched verification sub-agent together, as the harness bills
  it. ⛔ That is **not** comparable to a plan-marshall `metrics.toon` total, which counts a dispatch
  tree under plan-marshall's own per-task billing boundary — a boundary this lane does not have. The
  two figures answer different questions and must not be put side by side.

**What the run cost in verification effort, which is the figure that matters here.** Five
verification passes ran: four general rounds and one targeted closure pass. They returned 30, 15,
10, 5 and 2 findings — 62 in total, of which **two changed code behaviour** (the conditional write,
and round 3's two boundary defects counted as one behavioural change each) and the rest were
statements, guards, scope declaration, and this report. The mutation sweep ran four times, ending at
18 mutations with none surviving.

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
