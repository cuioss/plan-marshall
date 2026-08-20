# Run report — 030-claude-literal-residuals (run 01)

**Date (UTC):** 2026-08-20    **Branch:** `claude/claude-literal-residuals-tcyauu`    **PR:** _pending_    **Outcome:** _in progress_

> **Verification loop exit:** _pending_

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

Commits are named by subject rather than SHA throughout this report. The branch is expected to be
rebased onto `main` before the PR (to pick up a test-restructuring PR the operator named), and a
rebase replaces every replayed commit's object id — a quoted SHA would cite a commit on no branch
under review.

### D1 — Default permissions render in the runtime

**Done.** `permission_fix.py` no longer declares `DEFAULT_PERMISSIONS` or `add_default_permissions`.
`cmd_apply_fixes` states the goal through `permission_common.ensure_default_permissions`, which
delegates to `claude_runtime.ensure_default_permissions`: the runtime renders the rules from
`_default_permission_rules()`, merges them, sorts the allow list, performs the write, and returns
`{'defaults_added': [semantic ids], 'defaults_added_count': int, 'applied': bool}`.

*Done-when:* no `.claude/` literal remains in `permission_fix.py`, and no rendered `Read(...)` value
is received — the ids are `plan-dir-edit`, `plan-dir-write`, `bundle-cache-read`. The written set is
pinned byte-identically against literals by
`test_permission_fix.py::test_written_default_set_is_unchanged_by_the_relocation` and by the
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
local only, shared only, neither) and is identical in all four. Pinned on both sides:
`test_permission_rendering.py::TestProjectSettingsReadPath` (four cases plus the
read-versus-write-opposites invariant) and
`test_permission_common.py::TestProjectSettingsReadPreference` (the same, driven through the
module's own function so a reverted delegation is caught here rather than in the runtime's tests).

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

**Two deliberate differences from the retired code, both stated rather than absorbed:**

- The renderer **de-duplicates**. For a directory outside `$HOME` the tilde and absolute spellings
  are the same string, so the old builder drafted 19 rules of which 9 were duplicates and reported
  `rules_existing: 9` for rules that never existed. Nothing that lands in a settings file changes —
  the old append loop skipped duplicates too — only the count a caller is told.
- `protect-path` **writes only when a rule was actually added**, unlike its sibling `permission fix`
  branches. The retired caller behaved this way, and an idempotent re-run that re-serializes an
  operator's settings file is a visible change for no effect. Pinned by
  `test_a_no_change_rerun_does_not_rewrite_the_file`, which asserts byte equality rather than mtime.

### D4 — Implementor scan routes through layout resolution

**Done, and clean on every check.** `_scan_project_for_implementors` iterates
`get_project_skill_roots()` via a new `_project_skill_trees` helper that anchors each root with the
shared `marketplace_paths._resolve_skill_root`. No segment-wise `.claude` construction remains in
the function. Multiple roots are scanned in the op's priority order and the first root carrying a
given step id wins.

Four tests cover it, and none can pass against the retired single-root code: discovery through a
non-default two-root list, highest-priority-root-wins on a colliding step id, a declared root absent
from disk, and an absolute declared root.

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

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty**: the change touches Python
production code in six bundles plus six test modules. The gate therefore applies.

`./pw verify` was run from the repository root over the whole tree and read from the streamed tool
output rather than the exit code:

- quality-gate — `mypy … Success: no issues found in 416 source files`; `ruff … All checks passed!`;
  `SPDX-header check passed`; plugin-doctor `status: pass`, `total_issues: 0`.
- test-compile — `Found 0 errors` over 784 source files (one `no-any-return` in a new test was found
  and fixed here; the narrower `quality-gate` + `module-tests` pair does **not** run this step, which
  is why the full `verify` was used).
- module-tests — **21372 passed, 14 skipped**.

`git status --porcelain` was empty before each commit; no `uv.lock` churn reached a commit, and paths
were staged explicitly rather than with `git add -A`.

**Stale-base re-verification (§ Step 8 condition 2):** _pending — recorded at the merge gate._

### Mutation sweep — the new guards were shown to fail

`./pw verify` passing says the guards agree with the code, not that they would notice a defect.
Eleven mutations were applied one at a time, each restored from a harness-held byte snapshot in a
`finally` (never a git command, which would have rewritten the file from the index). The tree was
committed and `git status --porcelain` empty before the sweep, and empty again after it.

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

No mutation survived.

## Findings

### Surface expansion beyond the plan's Expected surface

The epic README requires a run to **report** rather than silently absorb any file its work turns out
to need beyond the plan's list. Six files qualify. The test that separates them is whether the edit
was **forced by this change** (keep, and report) or was an **adjacent fix to a pre-existing defect**
(revert, and record) — the epic's constraint bars adjacent fixes in another plan's surface, not the
consequences of one's own change.

Plans `010` and `030` are declared non-concurrent, so none of these is a live conflict.

| File | Owner per README | Why | Disposition |
|---|---|---|---|
| `platform-runtime/scripts/runtime_base.py` | `010` | `permission_fix`'s docstring enumerates the operation values; leaving it would state a false enumeration | kept, forced |
| `platform-runtime/scripts/platform_runtime.py` | `010` | argparse `choices` gate the CLI; without it the operation is reachable in-process only | kept, forced |
| `platform-runtime/scripts/opencode_runtime.py` | `010` | its `valid_ops` set decides `no-op` versus `invalid_operation` — D3's "degrades to `no-op` without error" fails without it | kept, forced |
| `platform-runtime/SKILL.md` | `070` | its op table enumerates the same operation values | kept, forced |
| `tools-permission-fix/SKILL.md` | `070` | its intent table enumerates them too | kept, forced |
| `manage-providers/scripts/credentials.py` | not listed | this change made its `ensure-denied` help text and module docstring inaccurate | kept, forced |
| `tools-permission-doctor/standards/permission-architecture.md` | `070`, **and named in this plan's own Out of scope** | corrects a defect that pre-dates this change | **reverted** — recorded below instead |

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

### The residual sweep found three clusters beyond the plan's five

The claim table required "anything beyond the five clusters above … is reported, not silently
adopted or skipped". The sweep over `marketplace/bundles/**` (both quote styles, segment-wise
included), discarding `platform-runtime` internals and the sanctioned multi-root resolvers, found
three live sites outside the five clusters. None was adopted; all three are registered in the
coupling inventory §B with no plan, which is the epic's mechanism for not losing a scoping
exclusion:

- `extension-api/scripts/configurable_contract.py` — the same segment-wise `.claude/skills`
  construction D4 closed, one file over in the same skill. The two were never registered together,
  so this half survived.
- `marshall-steward/scripts/bootstrap_plugin.py` — branches on the target name and composes each
  target's roots inline. Registered with the caveat that the bootstrap runs before the plugin is
  resolvable, so the remedy needs establishing rather than assuming.
- `tools-marketplace-inventory/scripts/_dep_index.py` — resolves its `project` scope from its own
  `CLAUDE_DIR` constant while the `plugin-cache` scope beside it routes through the layout op.

A fourth was recorded against an existing row rather than a new one: `permission_common.py` and
`permission_fix.py` are bound to `claude_runtime` by direct import rather than through the registry
(F25), and the settings mapping crosses the boundary as an argument (F4).

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
| F18 | round 1 | `permission-architecture.md` edited — named in this plan's own Out of scope, and fixing a *pre-existing* defect no deliverable needs | **reverted.** The pre-existing defect (its "Resolution Priority" states the READ preference backwards) is recorded against the standards row in the coupling inventory instead, which is what the epic's constraint asks for. The round also found the rationale added in that edit self-undermining, which is a second reason not to keep it |
| F19 | round 1 | `tools-permission-fix/SKILL.md` edited | **reported** — forced: its intent table enumerates the operation values |
| F20 | round 1 | `credentials.py` edited and not named in the brief's own list of knowingly-touched files | **reported** — now in the surface table; the same commit's F8 closes the inconsistency it left |
| F21 | round 1 | the claim table's required record of the schema addition was absent — the report was `_pending_` | **fixed** — recorded above |
| F22 | round 1 | the stale `_BOOKKEEPING_PREFIXES` premise and the divergence were unreported | **fixed** — recorded above |
| F23 | round 1 | the sixth residual cluster was registered in the inventory but not reported | **fixed** — recorded above, with the other two |
| F24 | round 1 | `protect-path` saved unconditionally, where the retired caller saved only on a change | **fixed** — the write is now conditional, pinned by a byte-equality test on an idempotent re-run |
| F25 | round 1 | D1 does not route through the `Runtime` op surface, so principles §6's cost bar is unmet for it while D3 meets it; the asymmetry was undeclared | **declared, not fixed.** Bound: behaviour is identical to `origin/main` (the module was already Claude-bound) and only `claude` and `opencode` are registered. Closing it needs either a new `Runtime` operation — which this plan's Out of scope forbids — or the `permission_common` restructure the inventory now registers. Stated in the D1 section, in the code, and in the inventory |
| F26 | round 1 | `_project_skill_trees` re-implemented `marketplace_paths._resolve_skill_root` inline | **fixed** — it calls the shared helper |
| F27 | round 1 | `test_no_rendered_rule_crosses_back_to_the_caller` never asserted success, so an error TOON would satisfy it | **fixed** |
| F28 | round 1 | an ensure-denied assertion held only because the sandbox directory name contains the word "credentials" | **fixed** — it now asserts specific rules built from the module's own bound `CREDENTIALS_DIR` |
| F29 | round 1 | the rewritten tests dropped the `importlib.reload`, so `_cred_ensure_denied` keeps whichever sandbox the first importing test installed | **rejected, with reason.** The binding is always to *a* sandbox, never the real tree, so no pollution is possible; the F28 fix reads the module's own bound constant, so the assertion is true of whichever sandbox is in force. Re-adding a module reload to make the identity match would reintroduce the cross-test reload the old fixture had to undo in teardown |
| F30 | round 1 | D5's Done-when ("no hardcoded `.claude/` remains in the three files") is not literally satisfied: two docstrings in `scan-marketplace-inventory.py` spell `.claude/skills`, one of them added by this diff | **rejected, with reason, and reported.** Both are `on Claude this is X` illustrations, the sanctioned phrasing already used by `marketplace_paths.get_project_skill_roots` and `_doctor_shared.py`; neither is a live anchor. The Done-when's wording is wider than the coupling it targets, and the divergence is stated here rather than met by deleting accurate explanatory prose |

**Positive collateral, recorded because it is a behaviour change nobody asked for.** The retired
`run_ensure_denied` loaded settings through `load_settings_path`, which returns a defaulted skeleton
*with* an `error` key on malformed JSON, and then wrote that skeleton back — silently destroying a
malformed settings file. The routed path fails closed with `invalid_settings` and writes nothing.

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
